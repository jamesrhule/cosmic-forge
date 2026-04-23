import { FEATURES } from "@/config/features";
import { loadFixture, loadJsonlFixture } from "@/lib/fixtures";
import {
  ServiceError,
  type AuditReport,
  type BenchmarkIndex,
  type RunConfig,
  type RunEvent,
  type RunResult,
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

/**
 * Fetch a single completed (or failed) run by id.
 *
 * Backend: GET /api/runs/{id}
 */
export async function getRun(id: string): Promise<RunResult> {
  void FEATURES.liveBackend;
  const path = RUN_FIXTURES[id];
  if (!path) {
    throw new ServiceError("NOT_FOUND", `No fixture for run id ${id}`);
  }
  return loadFixture<RunResult>(path);
}

/**
 * List every available run id (handy for the runs sidebar).
 *
 * Backend: GET /api/runs
 */
export async function listRuns(): Promise<RunResult[]> {
  void FEATURES.liveBackend;
  const ids = Object.keys(RUN_FIXTURES);
  return Promise.all(ids.map(getRun));
}

/**
 * Enqueue a new simulation run from a `RunConfig`. Returns the new
 * runId immediately; the caller subscribes to `streamRun` for progress.
 *
 * Backend: POST /api/runs   body: RunConfig   -> { runId }
 */
export async function startRun(
  config: RunConfig,
): Promise<{ runId: string }> {
  void FEATURES.liveBackend;
  void config;
  // Always pretend the new run is the Kawai-Kim baseline so the fixtures
  // line up with `streamRun` and `getRun`.
  return { runId: "kawai-kim-natural" };
}

/**
 * Stream a run's lifecycle events (status, logs, progress, metrics, result).
 *
 * Backend: SSE GET /api/runs/{runId}/stream  (or  WebSocket /ws/runs/{runId})
 */
export async function* streamRun(runId: string): AsyncIterable<RunEvent> {
  void FEATURES.liveBackend;
  void runId;
  yield* loadJsonlFixture<RunEvent>("events/run-kawai-kim.jsonl", 200);
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
