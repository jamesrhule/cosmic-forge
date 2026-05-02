/**
 * QCompass — Multi-domain run service.
 *
 * Mirrors `src/services/simulator.ts` but generic over `DomainId`.
 * Reads/writes against fixtures by default; live endpoints take over
 * when `FEATURES.liveBackend` is true.
 *
 * @example
 *   const runs = await listRuns("hep.lattice");
 *   const run = await getRun("hep.lattice", "schwinger-1plus1d");
 */
import { FEATURES } from "@/config/features";
import { loadFixture } from "@/lib/fixtures";
import { getDomain } from "@/lib/domains/registry";
import type {
  DomainId,
  DomainRunResult,
  RunEvent,
  RunSummary,
} from "@/lib/domains/types";
import { apiFetch, isQcompassBackendConfigured } from "./http";

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

/** @endpoint GET /api/qcompass/domains/{domain}/runs */
export async function listRuns(domain: DomainId): Promise<RunSummary[]> {
  if (FEATURES.liveBackend && isQcompassBackendConfigured()) {
    try {
      return await apiFetch<RunSummary[]>(
        `/api/qcompass/domains/${encodeURIComponent(domain)}/runs`,
      );
    } catch {
      /* fall through */
    }
  }
  const ids = DOMAIN_FIXTURE_INDEX[domain] ?? [];
  const summaries = await Promise.all(
    ids.map(async (id) => {
      try {
        const r = await loadFixture<DomainRunResult>(fixturePath(domain, id));
        return {
          id: r.id,
          label: r.label,
          status: r.status,
          domain: r.domain,
          created_at: r.created_at,
          summary: typeof r.payload?.summary === "string" ? (r.payload.summary as string) : undefined,
        } satisfies RunSummary;
      } catch {
        return null;
      }
    }),
  );
  return summaries.filter((s): s is RunSummary => s !== null);
}

/** @endpoint GET /api/qcompass/domains/{domain}/runs/{id} */
export async function getRun(domain: DomainId, id: string): Promise<DomainRunResult> {
  if (FEATURES.liveBackend && isQcompassBackendConfigured()) {
    try {
      return await apiFetch<DomainRunResult>(
        `/api/qcompass/domains/${encodeURIComponent(domain)}/runs/${encodeURIComponent(id)}`,
      );
    } catch {
      /* fall through */
    }
  }
  return loadFixture<DomainRunResult>(fixturePath(domain, id));
}

/** @endpoint POST /api/qcompass/domains/{domain}/runs */
export async function startRun(
  domain: DomainId,
  manifest: Record<string, unknown>,
): Promise<{ runId: string }> {
  if (FEATURES.liveBackend && isQcompassBackendConfigured()) {
    try {
      return await apiFetch<{ runId: string }>(
        `/api/qcompass/domains/${encodeURIComponent(domain)}/runs`,
        { method: "POST", body: manifest },
      );
    } catch {
      /* fall through */
    }
  }
  const ids = DOMAIN_FIXTURE_INDEX[domain] ?? [];
  return { runId: ids[0] ?? "demo" };
}

/** @endpoint SSE GET /api/qcompass/domains/{domain}/runs/{id}/stream */
export async function* streamRun(
  domain: DomainId,
  id: string,
): AsyncIterable<RunEvent> {
  // Fixture-mode emits a synthetic queued → running → result trio so
  // UI affordances can be exercised offline.
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
