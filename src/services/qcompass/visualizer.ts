/**
 * QCompass — Visualizer service.
 *
 * With `VITE_API_URL` set, reads the compute API through the generated SDK
 * (P4-02) and decodes msgpack frames from its WebSocket; consumes JSON
 * fixtures otherwise.
 *
 * @example
 *   const tl = await getVisualization("chemistry.molecular", "h2-sto3g");
 */
import { decode } from "@msgpack/msgpack";
import * as sdk from "@qcompass/frontend-sdk";
import { loadFixture } from "@/lib/fixtures";
import { api, sdkClient, usesApi } from "@/lib/sdk";
import { getDomain } from "@/lib/domains/registry";
import type { DomainId, VisualizationFrame, VisualizationTimeline } from "@/lib/domains/types";
import { getDomainTimeline } from "@/services/manifest";
import { isDomainName, normalizeDomainTimeline } from "@/lib/visualizer/domainFrames";
import type { DomainTimelineResponse, VisualizationDomain } from "@/types/manifest";

function timelineFixturePath(domain: DomainId, id: string): string {
  const plugin = getDomain(domain);
  const prefix = plugin?.fixturePathPrefix ?? `${domain}/`;
  return `${prefix}runs/${id}.json`;
}

/** @endpoint GET /api/qcompass/domains/{domain}/runs/{id}/visualization */
export async function getVisualization(
  domain: DomainId,
  id: string,
): Promise<VisualizationTimeline> {
  if (usesApi()) {
    // The API's VisualizationResponse; real-run timelines replace its
    // synthetic bake in P4-04.
    return timelineFromApi(domain, id, await api((c) => sdk.getVisualization(c, domain, id)));
  }
  // The run fixture itself carries an embedded `timeline` for now; back
  // it out into the standalone shape consumers expect.
  const run = await loadFixture<{
    payload?: { timeline?: VisualizationTimeline };
    domain: DomainId;
  }>(timelineFixturePath(domain, id));
  const tl = run.payload?.timeline;
  if (tl) return tl;

  // Synthesise a minimal frame timeline from whatever payload exists.
  const frames: VisualizationFrame[] = Array.from({ length: 8 }, (_, i) => ({
    tau: i / 7,
    data: { progress: i / 7 },
  }));
  const plugin = getDomain(domain);
  return {
    runId: id,
    domain: run.domain,
    frames,
    active_terms: [],
    tau_range: [0, 1],
    panelGroupId: plugin?.visualizerPanelGroupId ?? domain.split(".")[0],
  };
}

/**
 * The API's `VisualizationResponse` (`{run_id, domain, schema_version,
 * n_frames, frames, synthetic, source}`) as the timeline shape the views read
 * (c5: the cosmology card read `tau_range`/`active_terms`, which the API does
 * not send, and crashed). Everything shown comes from the response: τ range
 * and active terms are read off the frames (`null` / `[]` when they carry
 * none), and the B2 `synthetic`/`source` label is kept (R7).
 */
export function timelineFromApi(
  domain: DomainId,
  id: string,
  r: sdk.VisualizationTimeline,
): VisualizationTimeline {
  const frames = (Array.isArray(r.frames) ? r.frames : []) as unknown as VisualizationFrame[];
  const taus: number[] = [];
  const terms = new Set<string>();
  for (const f of frames as unknown as Array<Record<string, unknown>>) {
    if (typeof f.tau === "number" && Number.isFinite(f.tau)) taus.push(f.tau);
    if (Array.isArray(f.active_terms)) {
      for (const t of f.active_terms) if (typeof t === "string") terms.add(t);
    }
  }
  const plugin = getDomain(domain);
  return {
    runId: typeof r.run_id === "string" ? r.run_id : id,
    domain,
    frames,
    active_terms: [...terms],
    tau_range: taus.length > 0 ? [Math.min(...taus), Math.max(...taus)] : null,
    panelGroupId: plugin?.visualizerPanelGroupId ?? domain.split(".")[0],
    synthetic: r.synthetic === true,
    ...(typeof r.source === "string" ? { source: r.source } : {}),
  };
}

/** @endpoint WS /ws/qcompass/domains/{domain}/runs/{id}/visualization */
export async function* streamVisualization(
  domain: DomainId,
  id: string,
): AsyncIterable<VisualizationFrame> {
  if (usesApi() && typeof WebSocket !== "undefined") {
    const socket = sdk.openVisualizationStream(sdkClient(), domain, id);
    socket.binaryType = "arraybuffer";
    const queue: VisualizationFrame[] = [];
    let resolveNext: ((v: void) => void) | null = null;
    let closed = false;
    socket.onmessage = (ev: MessageEvent<ArrayBuffer>) => {
      try {
        const frame = decode(new Uint8Array(ev.data)) as VisualizationFrame;
        queue.push(frame);
        resolveNext?.();
        resolveNext = null;
      } catch {
        /* skip malformed frame */
      }
    };
    socket.onclose = () => {
      closed = true;
      resolveNext?.();
    };
    try {
      while (!closed) {
        if (queue.length === 0) {
          await new Promise<void>((r) => (resolveNext = r));
        }
        while (queue.length > 0) {
          const f = queue.shift();
          if (f) yield f;
        }
      }
    } finally {
      socket.close();
    }
    return;
  }

  // Fixture mode — replay the static timeline.
  const tl = await getVisualization(domain, id);
  for (const frame of tl.frames) {
    await new Promise((r) => setTimeout(r, 30));
    yield frame;
  }
}

// ─── Domain visualizer (panel timelines) ─────────────────────────────

/**
 * Per-domain panel timeline for `/domains/$domain/visualizer/$id`.
 *
 * - Backend configured: the `cosmic_forge_viz` API via
 *   `getDomainTimeline` (normalised there).
 * - No backend: the bundled `public/fixtures/visualizations/<id>.json`
 *   through the shared `loadFixture`, normalised by the same function
 *   and labelled `metadata.synthetic = true` (R7). A missing fixture, or
 *   one for another domain, yields an empty timeline — never a
 *   synthesised one.
 */
export async function getDomainVisualization(
  domain: DomainId,
  id: string,
): Promise<DomainTimelineResponse | null> {
  const vizDomain = visualizerDomainOf(domain);
  if (!vizDomain) return null;
  if (usesApi()) {
    return getDomainTimeline(vizDomain, id);
  }
  const empty: DomainTimelineResponse = {
    manifest: {
      run_id: id,
      domain: vizDomain,
      frame_count: 0,
      formula_variant: null,
      bake_uri: null,
      metadata: { synthetic: true, source: "frontend-fallback" },
    },
    frames: [],
  };
  let raw: unknown;
  try {
    raw = await loadFixture<unknown>(`visualizations/${id}.json`);
  } catch {
    return empty;
  }
  const rawDomain = (raw as { domain?: unknown } | null)?.domain;
  if (rawDomain !== vizDomain) return empty;
  const tl = normalizeDomainTimeline(raw, { run_id: id, domain: vizDomain, synthetic: true });
  tl.manifest.metadata.source = "bundled-fixture";
  return tl;
}

/** Map a registry DomainId to its visualizer panel group (`chemistry.molecular` → `chemistry`). */
export function visualizerDomainOf(domain: DomainId): VisualizationDomain | null {
  const group = getDomain(domain)?.visualizerPanelGroupId ?? domain.split(".")[0];
  return isDomainName(group) ? group : null;
}
