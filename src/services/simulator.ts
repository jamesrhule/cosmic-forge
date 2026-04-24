import { FEATURES } from "@/config/features";
import { loadFixture, loadJsonlFixture } from "@/lib/fixtures";
import { supabase } from "@/integrations/supabase/client";
import {
  persistRunRow,
  persistRunResult,
  persistAuditReport,
  setRunStatus,
} from "@/lib/persistence";
import { trackError } from "@/lib/telemetry";
import {
  ServiceError,
  type AuditReport,
  type BenchmarkIndex,
  type RunConfig,
  type RunEvent,
  type RunResult,
  type RunStatus,
  type ScanResult,
} from "@/types/domain";

/**
 * List the canonical benchmark catalog.
 *
 * Backend: GET /api/benchmarks
 */
export async function getBenchmarks(): Promise<BenchmarkIndex> {
  void FEATURES.liveBackend;
  return loadFixture<BenchmarkIndex>("benchmarks.json");
}

const RUN_FIXTURES: Record<string, string> = {
  "kawai-kim-natural": "runs/kawai-kim-natural.json",
  "starobinsky-standard": "runs/starobinsky-standard.json",
  "gb-off-control": "runs/gb-off-control.json",
  "failing-run": "runs/failing-run.json",
};

const FIXTURE_IDS = Object.keys(RUN_FIXTURES);

/** Fetch a fixture by run id, throws NOT_FOUND when missing. */
async function loadRunFixture(id: string): Promise<RunResult> {
  const path = RUN_FIXTURES[id];
  if (!path) {
    throw new ServiceError("NOT_FOUND", `No fixture for run id ${id}`);
  }
  return loadFixture<RunResult>(path);
}

/**
 * Best-effort backfill: when we serve a fixture for a known id and the
 * caller is signed in, push the fixture into Postgres so future reads are
 * hot. Anonymous callers can still read because RLS lets them see public
 * rows — they just can't create them.
 */
async function backfillFixture(id: string, fixture: RunResult): Promise<void> {
  if (!FEATURES.persistRuns) return;
  try {
    const { data } = await supabase.auth.getUser();
    if (!data.user) return;

    // Reconstruct a config-shaped object from the fixture for the row;
    // the fixtures embed `config` at the top level.
    const config = (fixture as unknown as { config?: RunConfig }).config;
    if (!config) return;

    const status = (fixture as unknown as { status?: RunStatus }).status ?? "completed";
    const r = await persistRunRow({
      id,
      config,
      status,
      visibility: "public",
      label: id,
    });
    if (!r.ok) return;
    await persistRunResult(id, fixture);
    if (fixture.audit) {
      await persistAuditReport(id, fixture.audit);
    }
  } catch (err) {
    // Backfill must never throw — it's opportunistic.
    trackError("service_error", {
      scope: "backfill_failed",
      runId: id,
      message: err instanceof Error ? err.message : String(err),
    });
  }
}

/**
 * Fetch a single completed (or failed) run by id.
 *
 * Reads from Postgres first; falls back to bundled fixtures for the
 * canonical demo runs.
 *
 * Backend: GET /api/runs/{id}
 */
export async function getRun(id: string): Promise<RunResult> {
  if (FEATURES.persistRuns) {
    try {
      const { data, error } = await supabase
        .from("run_results")
        .select("payload")
        .eq("run_id", id)
        .maybeSingle();
      if (!error && data?.payload) {
        return data.payload as unknown as RunResult;
      }
    } catch (err) {
      trackError("service_error", {
        scope: "get_run_db_failed",
        runId: id,
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }

  const fixture = await loadRunFixture(id);
  // Fire-and-forget backfill so the next read is hot.
  void backfillFixture(id, fixture);
  return fixture;
}

/**
 * List every available run (catalog + own).
 *
 * Backend: GET /api/runs
 */
export async function listRuns(): Promise<RunResult[]> {
  const dbRuns: RunResult[] = [];
  const seen = new Set<string>();

  if (FEATURES.persistRuns) {
    try {
      const { data, error } = await supabase
        .from("runs")
        .select("id, run_results(payload)")
        .order("created_at", { ascending: false })
        .limit(50);
      if (!error && data) {
        for (const row of data) {
          const payload = (row as unknown as { run_results?: { payload?: RunResult } | { payload?: RunResult }[] })
            .run_results;
          const result = Array.isArray(payload) ? payload[0]?.payload : payload?.payload;
          if (result) {
            dbRuns.push(result);
            seen.add(row.id as string);
          }
        }
      }
    } catch (err) {
      trackError("service_error", {
        scope: "list_runs_db_failed",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }

  // Merge with fixtures — fixtures fill any slot the DB doesn't know about
  // yet so the public catalog never appears empty during cold start.
  const fixtureFills = await Promise.all(
    FIXTURE_IDS.filter((id) => !seen.has(id)).map(async (id) => {
      const fx = await loadRunFixture(id);
      void backfillFixture(id, fx);
      return fx;
    }),
  );

  return [...dbRuns, ...fixtureFills];
}

/**
 * Enqueue a new simulation run from a `RunConfig`. Returns the new
 * runId immediately; the caller subscribes to `streamRun` for progress.
 *
 * - Authenticated users get a real persisted row with a fresh id.
 * - Anonymous callers get the legacy fixture id so the demo flow on `/`
 *   still works without auth.
 *
 * Backend: POST /api/runs   body: RunConfig   -> { runId }
 */
export async function startRun(config: RunConfig): Promise<{ runId: string }> {
  if (FEATURES.persistRuns) {
    try {
      const { data: auth } = await supabase.auth.getUser();
      if (auth.user) {
        const id =
          typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID()
            : `run-${Date.now()}`;
        const r = await persistRunRow({
          id,
          config,
          status: "queued",
          visibility: "public",
        });
        if (r.ok) {
          return { runId: id };
        }
      }
    } catch (err) {
      trackError("service_error", {
        scope: "start_run_persist_failed",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }

  // Anonymous fallback — fixture-driven demo path.
  return { runId: "kawai-kim-natural" };
}

/**
 * Stream a run's lifecycle events. Currently fixture-driven; on terminal
 * events we update the persisted row's status (best-effort).
 *
 * Backend: SSE GET /api/runs/{runId}/stream
 */
export async function* streamRun(runId: string): AsyncIterable<RunEvent> {
  void FEATURES.liveBackend;
  const startedAt = new Date().toISOString();
  void setRunStatus(runId, "running", { startedAt }).catch(() => {});

  let lastResult: RunResult | null = null;
  for await (const evt of loadJsonlFixture<RunEvent>("events/run-kawai-kim.jsonl", 200)) {
    if (evt.type === "result") {
      lastResult = evt.payload;
    }
    yield evt;
  }

  const completedAt = new Date().toISOString();
  void setRunStatus(runId, "completed", { startedAt, completedAt }).catch(() => {});
  if (lastResult) {
    void persistRunResult(runId, lastResult).catch(() => {});
    if (lastResult.audit) {
      void persistAuditReport(runId, lastResult.audit).catch(() => {});
    }
  }
}

/**
 * Fetch a run's audit report (S1–S15 verdicts).
 *
 * Backend: GET /api/runs/{runId}/audit
 */
export async function getAuditReport(runId: string): Promise<AuditReport> {
  const run = await getRun(runId);
  return run.audit;
}

/**
 * Fetch a parameter scan grid.
 *
 * Backend: GET /api/scans/{scanId}
 */
export async function getScan(scanId: string): Promise<ScanResult> {
  void FEATURES.liveBackend;
  void scanId;
  return loadFixture<ScanResult>("scans/xi-theta-64x64.json");
}
