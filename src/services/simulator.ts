import * as sdk from "@qcompass/frontend-sdk";
import { FEATURES } from "@/config/features";
import { loadFixture, loadJsonlFixture } from "@/lib/fixtures";
import { supabase } from "@/integrations/supabase/client";
import { api, apiStream, usesApi } from "@/lib/sdk";
import {
  persistRunRow,
  persistRunResult,
  persistAuditReport,
  setRunStatus,
} from "@/lib/persistence";
import { trackError } from "@/lib/telemetry";
import { BenchmarkIndexShape, RunResultShape, ScanResultShape } from "@/lib/fixtureSchemas";
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
 * @endpoint GET /api/benchmarks
 */
export async function getBenchmarks(): Promise<BenchmarkIndex> {
  if (usesApi()) {
    return (await api((c) => sdk.getBenchmarks(c))) as unknown as BenchmarkIndex;
  }
  return loadFixture<BenchmarkIndex>("benchmarks.json", {
    validate: (raw) => BenchmarkIndexShape.parse(raw) as unknown as BenchmarkIndex,
  });
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
  return loadFixture<RunResult>(path, {
    validate: (raw) => RunResultShape.parse(raw) as unknown as RunResult,
  });
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

const COSMOLOGY = "cosmology.ucglef1";

interface LiveRun {
  id: string;
  status: string;
  payload?: Record<string, unknown> | null;
}

/**
 * The RunResult inside a platform-route run (SF5). `qcompass.run` stores the
 * adapter's result (`payload.result.run_result`); `ucgle_f1.run` stores the
 * RunResult itself as the payload.
 */
export function cosmologyRunResult(run: LiveRun): RunResult {
  if (run.status !== "completed") {
    throw new ServiceError("NOT_FOUND", `run ${run.id} has no result yet (status ${run.status})`);
  }
  const payload = (run.payload ?? {}) as Record<string, unknown>;
  const nested = (payload.result as { run_result?: unknown } | undefined)?.run_result;
  const candidate = (nested ?? ("eta_B" in payload ? payload : null)) as RunResult | null;
  if (!candidate || typeof candidate !== "object") {
    throw new ServiceError("UPSTREAM_FAILURE", `run ${run.id} completed without a RunResult`);
  }
  return { ...candidate, id: run.id };
}

/**
 * Wait for a run to finish and return its result. With the API this follows
 * the run's stream to its terminal status first (SF5); with fixtures it is
 * `getRun` (byte-identical to before).
 */
export async function awaitRun(id: string): Promise<RunResult> {
  if (usesApi()) {
    for await (const ev of liveRunEvents(id)) {
      if (ev.type === "result") return ev.payload;
    }
  }
  return getRun(id);
}

/**
 * Fetch a single completed (or failed) run by id.
 *
 * Resolution order: Postgres (Supabase `run_results`) → then either the
 * compute API (with `VITE_API_URL`; errors propagate) or the bundled fixture.
 *
 * SF5 (R20): the live cosmology path has one shape, the platform route
 * `/api/qcompass/domains/cosmology.ucglef1/runs/{id}`, which serves both
 * workbench (`qcompass.run`) and agent (`ucgle_f1.run`) runs. A run that is
 * not completed yet is `NOT_FOUND` as a RunResult; `awaitRun` waits for it.
 *
 * @endpoint GET /api/qcompass/domains/{domain}/runs/{id}
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

  if (usesApi()) {
    const run = await api((c) => sdk.getRun(c, COSMOLOGY, id));
    return cosmologyRunResult(run as unknown as LiveRun);
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
          const payload = (
            row as unknown as { run_results?: { payload?: RunResult } | { payload?: RunResult }[] }
          ).run_results;
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

  // With the API, the catalog is what was persisted; no fixture fills (P4-02).
  if (usesApi()) return dbRuns;

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
 * - With `VITE_API_URL`, the config goes to the compute API as the
 *   `cosmology.ucglef1` manifest's problem (validated, enqueued, 202; P3-02)
 *   and the server-assigned id is returned (also mirrored to Postgres for
 *   catalog reads). Refusals (plan limits, budgets, invalid config) throw.
 * - Otherwise, an authenticated user gets a freshly-minted persisted row
 *   with a uuid, and an anonymous caller falls back to the demo fixture.
 *
 * Progress for an API run streams from `streamRun("cosmology.ucglef1", id)`
 * in `@/services/qcompass/runs`.
 *
 * @endpoint POST /api/qcompass/domains/{domain}/runs
 */
export async function startRun(config: RunConfig): Promise<{ runId: string }> {
  let liveId: string | null = null;
  if (usesApi()) {
    const res = await api((c) =>
      sdk.submitRun(c, "cosmology.ucglef1", {
        manifest: {
          domain: "cosmology",
          version: "1.0",
          problem: config,
          backend_request: { kind: "classical" },
        },
      }),
    );
    liveId = res.runId;
  }

  if (FEATURES.persistRuns) {
    try {
      const { data: auth } = await supabase.auth.getUser();
      if (auth.user) {
        const id =
          liveId ??
          (typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID()
            : `run-${Date.now()}`);
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

  if (liveId) return { runId: liveId };

  // Anonymous, no-backend fallback — fixture-driven demo path.
  return { runId: "kawai-kim-natural" };
}

/**
 * Stream a run's lifecycle events. The compute API's SSE stream with
 * `VITE_API_URL`; fixture-driven otherwise. On terminal events we update the
 * persisted row's status (best-effort).
 *
 * @endpoint SSE GET /api/qcompass/domains/{domain}/runs/{runId}/stream
 */
export async function* streamRun(runId: string): AsyncIterable<RunEvent> {
  const startedAt = new Date().toISOString();
  void setRunStatus(runId, "running", { startedAt }).catch(() => {});

  let lastResult: RunResult | null = null;

  const source: AsyncIterable<RunEvent> = usesApi()
    ? liveRunEvents(runId)
    : loadJsonlFixture<RunEvent>("events/run-kawai-kim.jsonl", 200);

  for await (const evt of source) {
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

const TERMINAL_STATUSES = new Set(["completed", "failed", "canceled"]);

/**
 * The platform route's run stream as RunEvents (SF5). Worker events from
 * either run kind become `status`/`progress`/`log`/`metric`; on a completed
 * run the stored result is fetched and yielded as the `result` event.
 */
async function* liveRunEvents(runId: string): AsyncIterable<RunEvent> {
  let terminal: string | null = null;
  for await (const ev of apiStream((c) => sdk.streamRun(c, COSMOLOGY, runId))) {
    const data = (ev.data ?? {}) as Record<string, unknown>;
    const at = typeof data.at === "string" ? data.at : new Date().toISOString();
    if (ev.event === "status") {
      const status = String(data.status ?? "");
      yield { type: "status", status: status as RunStatus, at };
      if (TERMINAL_STATUSES.has(status)) terminal = status;
    } else if (ev.event === "progress" && typeof data.fraction === "number") {
      const module = (typeof data.module === "string" ? data.module : "M7") as never;
      const detail =
        typeof data.detail === "string" ? data.detail : (data.stage as string | undefined);
      yield { type: "progress", module, fraction: data.fraction, detail };
    } else if (ev.event === "log") {
      const level = data.level === "warn" || data.level === "error" ? data.level : "info";
      const module = (typeof data.module === "string" ? data.module : "M7") as never;
      yield { type: "log", module, level, text: String(data.text ?? ""), at };
    } else if (ev.event === "metric" && typeof data.value === "number") {
      yield { type: "metric", name: String(data.name ?? ""), value: data.value };
    }
    if (terminal || ev.event === "end") break;
  }
  if (terminal === "completed") {
    yield { type: "result", payload: await getRun(runId) };
  } else if (terminal) {
    throw new ServiceError("UPSTREAM_FAILURE", `run ${runId} ${terminal}`);
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
 * @endpoint GET /api/qcompass/scans/{scanId}
 */
export async function getScan(scanId: string): Promise<ScanResult> {
  if (usesApi()) {
    // The API's ScanEnvelope; the grid shape arrives with scans as jobs (P4-07).
    return (await api((c) => sdk.getScan(c, scanId))) as unknown as ScanResult;
  }
  return loadFixture<ScanResult>("scans/xi-theta-64x64.json", {
    validate: (raw) => ScanResultShape.parse(raw) as unknown as ScanResult,
  });
}
