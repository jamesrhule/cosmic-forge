/**
 * QCompass — Multi-domain run service.
 *
 * Mirrors `src/services/simulator.ts` but generic over `DomainId`.
 * With `VITE_API_URL` set, every call goes to the compute API through the
 * generated SDK (P4-02) and errors propagate; otherwise fixtures are read.
 *
 * @example
 *   const runs = await listRuns("hep.lattice");
 *   const run = await getRun("hep.lattice", "schwinger-1plus1d");
 */
import * as sdk from "@qcompass/frontend-sdk";
import { loadFixture } from "@/lib/fixtures";
import { api, apiStream, usesApi } from "@/lib/sdk";
import { getDomain } from "@/lib/domains/registry";
import type { DomainId, DomainRunResult, RunEvent, RunSummary } from "@/lib/domains/types";

const DOMAIN_FIXTURE_INDEX: Record<DomainId, string[]> = {
  "cosmology.ucglef1": [],
  "chemistry.molecular": ["h2-sto3g", "lih-631g", "n2-ccpvdz", "femoco-toy"],
  "condmat.lattice": ["hubbard-4x4", "heisenberg-1d", "otoc-butterfly"],
  "amo.rydberg": ["rydberg-mis", "rydberg-quench", "blockade-ground"],
  "hep.lattice": ["schwinger-1plus1d", "zN-lattice", "su2-toy"],
  "nuclear.structure": ["ovbb-1plus1d", "ncsm-4he", "sterile-osc"],
  "gravity.syk": ["syk-sparse", "jt-gravity", "learned-syk"],
  "statmech.sampling": ["qae-toy", "quantum-metropolis", "tfd-prep"],
};

function fixturePath(domain: DomainId, id: string): string {
  const plugin = getDomain(domain);
  const prefix = plugin?.fixturePathPrefix ?? `${domain}/`;
  return `${prefix}runs/${id}.json`;
}

/** The API's DomainRunResult as the app's type (same wire contract, P4-01). */
function fromWire(run: sdk.DomainRunResult): DomainRunResult {
  return run as unknown as DomainRunResult;
}

/** @endpoint GET /api/qcompass/domains/{domain}/runs */
export async function listRuns(domain: DomainId): Promise<RunSummary[]> {
  if (usesApi()) {
    const rows = await api((c) => sdk.listRuns(c, domain));
    return rows as unknown as RunSummary[];
  }
  const ids = DOMAIN_FIXTURE_INDEX[domain] ?? [];
  const summaries = await Promise.all(
    ids.map(async (id): Promise<RunSummary | null> => {
      try {
        const r = await loadFixture<DomainRunResult>(fixturePath(domain, id));
        const summary: RunSummary = {
          id: r.id,
          label: r.label,
          status: r.status,
          domain: r.domain,
          created_at: r.created_at,
        };
        if (r.synthetic === true) summary.synthetic = true;
        if (typeof r.payload?.summary === "string") {
          summary.summary = r.payload.summary as string;
        }
        return summary;
      } catch {
        return null;
      }
    }),
  );
  return summaries.filter((s): s is RunSummary => s !== null);
}

/** @endpoint GET /api/qcompass/domains/{domain}/runs/{id} */
export async function getRun(domain: DomainId, id: string): Promise<DomainRunResult> {
  if (usesApi()) {
    return fromWire(await api((c) => sdk.getRun(c, domain, id)));
  }
  return loadFixture<DomainRunResult>(fixturePath(domain, id));
}

/**
 * Enqueue a run. Live: the API validates the envelope and returns 202 with
 * the run id; refusals (plan limits, budgets, invalid manifests) propagate
 * as ServiceError. Fixtures: the domain's first fixture run id.
 *
 * `manifest` is the domain's `Manifest.problem` (or a full manifest).
 *
 * @endpoint POST /api/qcompass/domains/{domain}/runs
 */
export async function startRun(
  domain: DomainId,
  manifest: Record<string, unknown>,
): Promise<{ runId: string }> {
  if (usesApi()) {
    const res = await api((c) => sdk.submitRun(c, domain, manifest));
    return { runId: res.runId };
  }
  const ids = DOMAIN_FIXTURE_INDEX[domain] ?? [];
  return { runId: ids[0] ?? "demo" };
}

const TERMINAL = new Set(["completed", "failed", "canceled", "cancelled"]);

/**
 * Stream a run's lifecycle as `queued → running(progress) → result | error`.
 *
 * Live: the API's SSE stream, whose events the worker writes as the run
 * progresses (P3-02); on a terminal status the stored run is fetched and
 * yielded as the result. Fixtures: a synthetic queued → running → result
 * trio over the bundled fixture so UI affordances can be exercised offline.
 *
 * @endpoint SSE GET /api/qcompass/domains/{domain}/runs/{id}/stream
 */
export async function* streamRun(
  domain: DomainId,
  id: string,
  signal?: AbortSignal,
): AsyncIterable<RunEvent> {
  if (usesApi()) {
    yield* streamLive(domain, id, signal);
    return;
  }
  yield { type: "queued", runId: id };
  for (const p of [0.25, 0.5, 0.75, 1.0]) {
    await new Promise((r) => setTimeout(r, 50));
    yield { type: "running", runId: id, progress: p };
  }
  try {
    const payload = await getRun(domain, id);
    yield { type: "result", runId: id, payload };
  } catch (err) {
    yield {
      type: "error",
      runId: id,
      message: err instanceof Error ? err.message : String(err),
    };
  }
}

async function* streamLive(
  domain: DomainId,
  id: string,
  signal?: AbortSignal,
): AsyncIterable<RunEvent> {
  let progress = 0;
  let terminal: string | null = null;
  for await (const ev of apiStream((c) => sdk.streamRun(c, domain, id, signal))) {
    const data = (ev.data ?? {}) as Record<string, unknown>;
    if (ev.event === "history") {
      yield { type: "queued", runId: id };
    } else if (ev.event === "status") {
      const status = String(data.status ?? "");
      if (status === "running") yield { type: "running", runId: id, progress };
      if (TERMINAL.has(status)) terminal = status;
    } else if (ev.event === "progress") {
      if (typeof data.fraction === "number") progress = data.fraction;
      yield { type: "running", runId: id, progress };
    } else if (ev.event === "log") {
      const level = data.level === "warn" || data.level === "error" ? data.level : "info";
      yield { type: "log", runId: id, level, message: String(data.text ?? data.message ?? "") };
    }
    if (terminal || ev.event === "end") break;
  }
  const run = await getRun(domain, id);
  if (run.status === "completed") {
    yield { type: "result", runId: id, payload: run };
  } else {
    const detail = run.payload?.error ?? run.payload?.status_detail ?? run.status;
    yield { type: "error", runId: id, message: `Run ${id} ${run.status}: ${String(detail)}` };
  }
}
