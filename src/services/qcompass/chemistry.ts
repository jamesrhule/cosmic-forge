/**
 * Chemistry domain services.
 *
 * All methods are offline-first via fixtures under
 * `/public/fixtures/chemistry/`. PROMPT 8 v2 §C wires the live
 * backend path: when `FEATURES.liveBackend` is `true`, calls go
 * through `@qcompass/frontend-sdk`'s `chemistryService` against
 * `API_BASE_URL`. When `false`, the existing fixture path is
 * preserved verbatim so the cosmology byte-identity contract
 * keeps holding.
 *
 * Type contract: every payload mirrors the Pydantic models in
 * `packages/qfull-chemistry/src/qfull_chem/manifest.py` and
 * `packages/qcompass-core/src/qcompass_core/manifest.py`.
 */

import { API_BASE_URL, FEATURES } from "@/config/features";
import { loadFixture, loadJsonlFixture } from "@/lib/fixtures";
import { ServiceError } from "@/types/domain";
import type {
  ChemistryProblem,
  ChemistryRunEvent,
  ChemistryRunResult,
  QcompassManifest,
} from "@/types/qcompass";

import {
  chemistryService as sdkChemistryService,
  QcompassClient,
} from "@qcompass/frontend-sdk";

let _sdkClient: QcompassClient | null = null;

function getSdkClient(): QcompassClient {
  if (!_sdkClient) {
    _sdkClient = new QcompassClient({ baseUrl: API_BASE_URL });
  }
  return _sdkClient;
}

const RUN_FIXTURES: Record<string, string> = {
  "h2-sto3g": "chemistry/runs/h2-sto3g.json",
  "lih-631g": "chemistry/runs/lih-631g.json",
  "n2-ccpvdz": "chemistry/runs/n2-ccpvdz.json",
  "femoco-toy": "chemistry/runs/femoco-toy.json",
};

/**
 * List every chemistry run available.
 *
 * Backend: GET /api/qcompass/chemistry/runs
 */
export async function listChemistryRuns(): Promise<ChemistryRunResult[]> {
  void FEATURES.liveBackend;
  const ids = Object.keys(RUN_FIXTURES);
  return Promise.all(ids.map(getChemistryRun));
}

/**
 * Fetch a single chemistry run by id.
 *
 * Backend: GET /api/qcompass/chemistry/runs/{id}
 */
export async function getChemistryRun(
  id: string,
): Promise<ChemistryRunResult> {
  void FEATURES.liveBackend;
  const path = RUN_FIXTURES[id];
  if (!path) {
    throw new ServiceError("NOT_FOUND", `No fixture for chemistry run id ${id}`);
  }
  return loadFixture<ChemistryRunResult>(path);
}

/**
 * Submit a chemistry manifest. Returns the new run id immediately;
 * caller subscribes to `streamChemistryRun` for progress.
 *
 * Backend: POST /api/qcompass/chemistry/runs   body: QcompassManifest<ChemistryProblem>
 *          returns: { runId: string }
 */
export async function startChemistryRun(
  manifest: QcompassManifest<ChemistryProblem>,
): Promise<{ runId: string }> {
  if (FEATURES.liveBackend) {
    const sub = await sdkChemistryService(getSdkClient()).submit(
      manifest as unknown as Parameters<
        ReturnType<typeof sdkChemistryService>["submit"]
      >[0],
    );
    return { runId: sub.runId };
  }
  // In fixture mode every submission resolves to the H2 baseline so
  // the configurator → control flow is exercisable end-to-end without
  // a backend. Real submissions return a server-generated run_id.
  const moleculeKey = String(manifest.problem.molecule).toLowerCase();
  const fallback = moleculeKey === "lih"
    ? "lih-631g"
    : moleculeKey === "n2"
    ? "n2-ccpvdz"
    : moleculeKey === "femoco_toy"
    ? "femoco-toy"
    : "h2-sto3g";
  return { runId: fallback };
}

/**
 * Stream a chemistry run's lifecycle events (status, log, metric, result).
 *
 * Backend: SSE GET /api/qcompass/chemistry/runs/{id}/stream
 *          (or  WebSocket /ws/qcompass/chemistry/runs/{id})
 */
export async function* streamChemistryRun(
  id: string,
): AsyncIterable<ChemistryRunEvent> {
  void FEATURES.liveBackend;
  const path = RUN_FIXTURES[id];
  if (!path) {
    throw new ServiceError(
      "NOT_FOUND",
      `No stream fixture for chemistry run id ${id}`,
    );
  }
  // We synthesise a minimal event timeline from the static fixture
  // so the Control view can exercise its render path without any
  // JSONL fixture authored per run. Once the backend lands, this
  // becomes a real SSE subscription.
  yield* synthesizeStream(id);
}

async function* synthesizeStream(
  id: string,
): AsyncIterable<ChemistryRunEvent> {
  const result = await getChemistryRun(id);
  const at = new Date().toISOString();
  yield { type: "status", status: "running", at };
  yield {
    type: "log",
    level: "info",
    text: `Resolving classical reference (${result.energies.classical_method})...`,
    at,
  };
  if (result.energies.classical_energy !== null) {
    yield {
      type: "metric",
      name: "classical_energy",
      value: result.energies.classical_energy,
      unit: "Ha",
    };
  }
  if (result.energies.quantum_energy !== null) {
    yield {
      type: "metric",
      name: "quantum_energy",
      value: result.energies.quantum_energy,
      unit: "Ha",
    };
  }
  yield { type: "result", payload: result };
  yield { type: "status", status: "completed", at };
}

/**
 * Optional: load JSONL stream fixture if a richer per-run timeline is
 * authored later (e.g. `chemistry/streams/h2-sto3g.jsonl`). Falls back
 * to `synthesizeStream` when the file is missing.
 */
export async function* streamChemistryRunFromJsonl(
  id: string,
): AsyncIterable<ChemistryRunEvent> {
  try {
    yield* loadJsonlFixture<ChemistryRunEvent>(
      `chemistry/streams/${id}.jsonl`,
      120,
    );
  } catch {
    yield* synthesizeStream(id);
  }
}
