/**
 * One typed function per compute-API route (P4-02).
 *
 * Every return type is read from the OpenAPI document through `./api.ts`,
 * so a backend change that breaks a caller fails `tsc` once the generated
 * types are refreshed (and CI fails while they are stale). The functions
 * are pure HTTP: whether the app calls them or reads fixtures is decided by
 * the app (`src/config/features.ts`, `VITE_API_URL`), never by the SDK.
 */

import type { QcompassClient, SseEvent } from "./client";
import type { JsonRequest, JsonResponse } from "./api";
import type {
  CreateScanRequest,
  QcompassManifest,
  QcompassRunStreamEvent,
  SubmitRunRequest,
} from "./types";

const enc = encodeURIComponent;

function query(params: Record<string, string | number | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined) q.set(k, String(v));
  const s = q.toString();
  return s ? `?${s}` : "";
}

// ── Ops ─────────────────────────────────────────────────────────────

export function getHealth(client: QcompassClient): Promise<JsonResponse<"/healthz", "get">> {
  return client.getJson("/healthz");
}

export function getReadiness(client: QcompassClient): Promise<JsonResponse<"/readyz", "get">> {
  return client.getJson("/readyz");
}

// ── UCGLE-F1 (legacy /api/runs mirror of the workbench services) ───

export function getBenchmarks(
  client: QcompassClient,
): Promise<JsonResponse<"/api/benchmarks", "get">> {
  return client.getJson("/api/benchmarks");
}

export function getUcgleRun(
  client: QcompassClient,
  runId: string,
): Promise<JsonResponse<"/api/runs/{run_id}", "get">> {
  return client.getJson(`/api/runs/${enc(runId)}`);
}

export function getUcgleAudit(
  client: QcompassClient,
  runId: string,
): Promise<JsonResponse<"/api/runs/{run_id}/audit", "get">> {
  return client.getJson(`/api/runs/${enc(runId)}/audit`);
}

export function streamUcgleRun(
  client: QcompassClient,
  runId: string,
  signal?: AbortSignal,
): AsyncGenerator<SseEvent> {
  return client.sse(`/api/runs/${enc(runId)}/stream`, { signal });
}

// ── Agent chat and models ───────────────────────────────────────────

export function chat(
  client: QcompassClient,
  body: JsonRequest<"/v1/chat", "post">,
  signal?: AbortSignal,
): AsyncGenerator<SseEvent> {
  return client.sse("/v1/chat", { method: "POST", body, signal });
}

export function listModels(client: QcompassClient): Promise<JsonResponse<"/api/models", "get">> {
  return client.getJson("/api/models");
}

export function getModelStatus(
  client: QcompassClient,
  modelId: string,
): Promise<JsonResponse<"/api/models/{mid}/status", "get">> {
  return client.getJson(`/api/models/${enc(modelId)}/status`);
}

export function installModel(
  client: QcompassClient,
  modelId: string,
  signal?: AbortSignal,
): AsyncGenerator<SseEvent> {
  return client.sse(`/api/models/${enc(modelId)}/install`, { method: "POST", signal });
}

export function uninstallModel(
  client: QcompassClient,
  modelId: string,
): Promise<JsonResponse<"/api/models/{mid}", "delete">> {
  return client.deleteJson(`/api/models/${enc(modelId)}`);
}

// ── Domains ─────────────────────────────────────────────────────────

export function listDomains(
  client: QcompassClient,
): Promise<JsonResponse<"/api/qcompass/domains", "get">> {
  return client.getJson("/api/qcompass/domains");
}

export function getDomainSchema(
  client: QcompassClient,
  domain: string,
): Promise<JsonResponse<"/api/qcompass/domains/{domain}/schema", "get">> {
  return client.getJson(`/api/qcompass/domains/${enc(domain)}/schema`);
}

// ── Runs ────────────────────────────────────────────────────────────

/**
 * Enqueue a run (202). Accepts `{manifest, runId?}`, a bare manifest, or a
 * bare `problem` object (the API wraps it in a classical manifest).
 */
export function submitRun<T = Record<string, unknown>>(
  client: QcompassClient,
  domain: string,
  body: SubmitRunRequest<T> | QcompassManifest<T> | Record<string, unknown>,
): Promise<JsonResponse<"/api/qcompass/domains/{domain}/runs", "post">> {
  return client.postJson(`/api/qcompass/domains/${enc(domain)}/runs`, body);
}

export function listRuns(
  client: QcompassClient,
  domain: string,
  opts: { limit?: number; offset?: number } = {},
): Promise<JsonResponse<"/api/qcompass/domains/{domain}/runs", "get">> {
  return client.getJson(`/api/qcompass/domains/${enc(domain)}/runs${query(opts)}`);
}

export function getRun(
  client: QcompassClient,
  domain: string,
  runId: string,
): Promise<JsonResponse<"/api/qcompass/domains/{domain}/runs/{run_id}", "get">> {
  return client.getJson(`/api/qcompass/domains/${enc(domain)}/runs/${enc(runId)}`);
}

/** Server-sent run events: `history`, then the worker's `status`/`progress`/…, then `end`. */
export function streamRun(
  client: QcompassClient,
  domain: string,
  runId: string,
  signal?: AbortSignal,
): AsyncGenerator<QcompassRunStreamEvent> {
  return client.sse(`/api/qcompass/domains/${enc(domain)}/runs/${enc(runId)}/stream`, {
    signal,
  }) as AsyncGenerator<QcompassRunStreamEvent>;
}

// ── Visualization ──────────────────────────────────────────────────

export function getVisualization(
  client: QcompassClient,
  domain: string,
  runId: string,
  maxFrames: number = 256,
): Promise<JsonResponse<"/api/qcompass/domains/{domain}/runs/{run_id}/visualization", "get">> {
  return client.getJson(
    `/api/qcompass/domains/${enc(domain)}/runs/${enc(runId)}/visualization${query({ max_frames: maxFrames })}`,
  );
}

export function openVisualizationStream(
  client: QcompassClient,
  domain: string,
  runId: string,
): WebSocket {
  return client.openWebSocket(
    `/ws/qcompass/domains/${enc(domain)}/runs/${enc(runId)}/visualization`,
  );
}

// ── Scans (`/api/qcompass/scans`; `/api/scans` is the API's alias) ─

export function listScans(
  client: QcompassClient,
  opts: { domain?: string; limit?: number } = {},
): Promise<JsonResponse<"/api/qcompass/scans", "get">> {
  return client.getJson(`/api/qcompass/scans${query(opts)}`);
}

export function getScan(
  client: QcompassClient,
  scanId: string,
): Promise<JsonResponse<"/api/qcompass/scans/{scan_id}", "get">> {
  return client.getJson(`/api/qcompass/scans/${enc(scanId)}`);
}

export function createScan(
  client: QcompassClient,
  body: CreateScanRequest,
): Promise<JsonResponse<"/api/qcompass/scans", "post">> {
  return client.postJson("/api/qcompass/scans", body);
}

export function deleteScan(
  client: QcompassClient,
  scanId: string,
): Promise<JsonResponse<"/api/qcompass/scans/{scan_id}", "delete">> {
  return client.deleteJson(`/api/qcompass/scans/${enc(scanId)}`);
}

// ── Tenancy, verdict, literature ────────────────────────────────────

export function listTenants(
  client: QcompassClient,
): Promise<JsonResponse<"/api/qcompass/tenants", "get">> {
  return client.getJson("/api/qcompass/tenants");
}

export function getVerdict(
  client: QcompassClient,
  verdictId: string,
): Promise<JsonResponse<"/api/verdict/{verdict_id}", "get">> {
  return client.getJson(`/api/verdict/${enc(verdictId)}`);
}

export function getLatestVerdict(
  client: QcompassClient,
): Promise<JsonResponse<"/api/qcompass/verdict", "get">> {
  return client.getJson("/api/qcompass/verdict");
}

export function getLatticeQcdReferences(
  client: QcompassClient,
): Promise<JsonResponse<"/api/qcompass/literature/lattice-qcd", "get">> {
  return client.getJson("/api/qcompass/literature/lattice-qcd");
}

export function getNuclearReferences(
  client: QcompassClient,
): Promise<JsonResponse<"/api/qcompass/literature/nuclear", "get">> {
  return client.getJson("/api/qcompass/literature/nuclear");
}

// ── Domain-keyed convenience namespaces ───────────────────────────

function domainService(client: QcompassClient, domain: string) {
  return {
    schema: () => getDomainSchema(client, domain),
    submit: (manifest: QcompassManifest) => submitRun(client, domain, manifest),
    list: () => listRuns(client, domain),
    get: (runId: string) => getRun(client, domain, runId),
    stream: (runId: string) => streamRun(client, domain, runId),
    visualization: (runId: string, maxFrames?: number) =>
      getVisualization(client, domain, runId, maxFrames),
    openWs: (runId: string) => openVisualizationStream(client, domain, runId),
  };
}

export const chemistryService = (client: QcompassClient) => domainService(client, "chemistry");
export const cosmologyService = (client: QcompassClient) => domainService(client, "cosmology");
export const hepService = (client: QcompassClient) => domainService(client, "hep");
export const nuclearService = (client: QcompassClient) => domainService(client, "nuclear");
