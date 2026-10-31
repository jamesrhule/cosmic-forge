/**
 * Per-domain + scan service wrappers (PROMPT 8 v2 §C).
 *
 * Each function maps 1:1 to a backend route under
 * /api/qcompass/* or /api/scans/*. They are pure HTTP helpers —
 * fixture-vs-live decisions are made by the calling React layer
 * via FEATURES.liveBackend.
 */

import { QcompassClient } from "./client";
import type {
  CreateScanRequest,
  DomainsResponse,
  ProvenanceSidecar,
  QcompassManifest,
  ScanEnvelope,
  SubmitRunRequest,
  SubmitRunResponse,
  VisualizationTimeline,
} from "./types";

// ── Domains ─────────────────────────────────────────────────────────

export function listDomains(client: QcompassClient): Promise<DomainsResponse> {
  return client.getJson<DomainsResponse>("/api/qcompass/domains");
}

export function getDomainSchema(
  client: QcompassClient, domain: string,
): Promise<Record<string, unknown>> {
  return client.getJson(`/api/qcompass/domains/${domain}/schema`);
}

// ── Runs ────────────────────────────────────────────────────────────

export function submitRun<T = Record<string, unknown>>(
  client: QcompassClient, domain: string,
  body: SubmitRunRequest<T> | QcompassManifest<T>,
): Promise<SubmitRunResponse> {
  const payload =
    "manifest" in body ? body : { manifest: body };
  return client.postJson(`/api/qcompass/domains/${domain}/runs`, payload);
}

export function getRun(
  client: QcompassClient, domain: string, runId: string,
): Promise<ProvenanceSidecar> {
  return client.getJson(
    `/api/qcompass/domains/${domain}/runs/${runId}`,
  );
}

export async function* streamRun(
  client: QcompassClient, domain: string, runId: string,
): AsyncIterable<{ event?: string; [key: string]: unknown }> {
  yield* client.sse(
    `/api/qcompass/domains/${domain}/runs/${runId}/stream`,
  );
}

// ── Visualization ──────────────────────────────────────────────────

export function getVisualization(
  client: QcompassClient,
  domain: string,
  runId: string,
  maxFrames: number = 256,
): Promise<VisualizationTimeline> {
  return client.getJson(
    `/api/qcompass/domains/${domain}/runs/${runId}/visualization?max_frames=${maxFrames}`,
  );
}

export function openVisualizationStream(
  client: QcompassClient, domain: string, runId: string,
): WebSocket {
  return client.openWebSocket(
    `/ws/qcompass/domains/${domain}/runs/${runId}/visualization`,
  );
}

// ── Scans ──────────────────────────────────────────────────────────

export function listScans(
  client: QcompassClient,
  opts: { domain?: string; limit?: number } = {},
): Promise<{ scans: ScanEnvelope[] }> {
  const params = new URLSearchParams();
  if (opts.domain) params.set("domain", opts.domain);
  if (opts.limit) params.set("limit", String(opts.limit));
  const query = params.toString();
  return client.getJson(`/api/scans${query ? `?${query}` : ""}`);
}

export function getScan(
  client: QcompassClient, scanId: string,
): Promise<ScanEnvelope> {
  return client.getJson(`/api/scans/${scanId}`);
}

export function createScan(
  client: QcompassClient, body: CreateScanRequest,
): Promise<ScanEnvelope> {
  return client.postJson("/api/scans", body);
}

export function deleteScan(
  client: QcompassClient, scanId: string,
): Promise<{ ok: true }> {
  return client.deleteJson(`/api/scans/${scanId}`);
}

// ── Domain-keyed convenience namespaces ───────────────────────────

export function chemistryService(client: QcompassClient) {
  return {
    schema: () => getDomainSchema(client, "chemistry"),
    submit: (manifest: QcompassManifest) =>
      submitRun(client, "chemistry", manifest),
    get: (runId: string) => getRun(client, "chemistry", runId),
    stream: (runId: string) => streamRun(client, "chemistry", runId),
    visualization: (runId: string, maxFrames?: number) =>
      getVisualization(client, "chemistry", runId, maxFrames),
    openWs: (runId: string) =>
      openVisualizationStream(client, "chemistry", runId),
  };
}

export function cosmologyService(client: QcompassClient) {
  return {
    schema: () => getDomainSchema(client, "cosmology"),
    submit: (manifest: QcompassManifest) =>
      submitRun(client, "cosmology", manifest),
    get: (runId: string) => getRun(client, "cosmology", runId),
    stream: (runId: string) => streamRun(client, "cosmology", runId),
    visualization: (runId: string, maxFrames?: number) =>
      getVisualization(client, "cosmology", runId, maxFrames),
    openWs: (runId: string) =>
      openVisualizationStream(client, "cosmology", runId),
  };
}

export function hepService(client: QcompassClient) {
  return {
    schema: () => getDomainSchema(client, "hep"),
    submit: (manifest: QcompassManifest) =>
      submitRun(client, "hep", manifest),
    get: (runId: string) => getRun(client, "hep", runId),
    stream: (runId: string) => streamRun(client, "hep", runId),
    visualization: (runId: string, maxFrames?: number) =>
      getVisualization(client, "hep", runId, maxFrames),
    openWs: (runId: string) =>
      openVisualizationStream(client, "hep", runId),
  };
}

export function nuclearService(client: QcompassClient) {
  return {
    schema: () => getDomainSchema(client, "nuclear"),
    submit: (manifest: QcompassManifest) =>
      submitRun(client, "nuclear", manifest),
    get: (runId: string) => getRun(client, "nuclear", runId),
    stream: (runId: string) => streamRun(client, "nuclear", runId),
    visualization: (runId: string, maxFrames?: number) =>
      getVisualization(client, "nuclear", runId, maxFrames),
    openWs: (runId: string) =>
      openVisualizationStream(client, "nuclear", runId),
  };
}
