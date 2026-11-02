/**
 * QCompass — Visualizer service.
 *
 * Decodes msgpack frames when `liveBackend` is on; consumes JSON
 * fixtures otherwise.
 *
 * @example
 *   const tl = await getVisualization("chemistry.molecular", "h2-sto3g");
 */
import { decode } from "@msgpack/msgpack";
import { FEATURES } from "@/config/features";
import { loadFixture } from "@/lib/fixtures";
import { getDomain } from "@/lib/domains/registry";
import type { DomainId, VisualizationFrame, VisualizationTimeline } from "@/lib/domains/types";
import { apiFetch, isQcompassBackendConfigured } from "./http";
import { isBackendConfigured as isVizBackendConfigured } from "@/lib/apiClient";
import { getDomainTimeline } from "@/services/manifest";
import { isDomainName, normalizeDomainTimeline } from "@/lib/visualizer/domainFrames";
import type { DomainTimelineResponse, VisualizationDomain } from "@/types/manifest";
import { API_BASE_URL } from "@/config/features";

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
  if (FEATURES.liveBackend && isQcompassBackendConfigured()) {
    try {
      return await apiFetch<VisualizationTimeline>(
        `/api/qcompass/domains/${encodeURIComponent(domain)}/runs/${encodeURIComponent(id)}/visualization`,
      );
    } catch {
      /* fall through */
    }
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

/** @endpoint WS /ws/qcompass/domains/{domain}/runs/{id}/visualization */
export async function* streamVisualization(
  domain: DomainId,
  id: string,
): AsyncIterable<VisualizationFrame> {
  if (FEATURES.liveBackend && isQcompassBackendConfigured() && typeof WebSocket !== "undefined") {
    const url = `${API_BASE_URL.replace(/^http/, "ws")}/ws/qcompass/domains/${encodeURIComponent(
      domain,
    )}/runs/${encodeURIComponent(id)}/visualization`;
    const socket = new WebSocket(url);
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

  // Fixture fallback — replay the static timeline.
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
  if (isVizBackendConfigured()) {
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
