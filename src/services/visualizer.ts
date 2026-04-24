import { FEATURES } from "@/config/features";
import { loadFixture, loadJsonlFixture } from "@/lib/fixtures";
import { VisualizationTimelineShape } from "@/lib/fixtureSchemas";
import { ServiceError } from "@/types/domain";
import { bakeTimelineBuffers } from "@/lib/visualizerBake";
import { supabase } from "@/integrations/supabase/client";
import {
  loadTimelineFromStorage,
  persistVisualizationTimeline,
} from "@/lib/persistence";
import { trackError } from "@/lib/telemetry";
import type {
  BakedVisualizationTimeline,
  RenderOptions,
  VisualizationFrame,
  VisualizationTimeline,
} from "@/types/visualizer";

/**
 * Each shipped run gets one timeline fixture. The mapping is intentionally
 * separate from `RUN_FIXTURES` in `simulator.ts` because not every run
 * ships a visualization (e.g. the failing-run fixture has none).
 */
const VISUALIZATION_FIXTURES: Record<string, string> = {
  "kawai-kim-natural": "visualizations/kawai-kim-natural.json",
  "starobinsky-standard": "visualizations/starobinsky-standard.json",
  "gb-off-control": "visualizations/gb-off-control.json",
  "f2-nieh-yan-demo": "visualizations/f2-nieh-yan-demo.json",
  "f3-large-N-demo": "visualizations/f3-large-N-demo.json",
  "f5-resonance-demo": "visualizations/f5-resonance-demo.json",
  "f7-stacked-demo": "visualizations/f7-stacked-demo.json",
};

/**
 * Static, hand-maintained summary of each shipped fixture. Used by the
 * `/visualizer` index card grid so the loader doesn't have to fetch and
 * parse every timeline JSON just to render a one-line subtitle.
 *
 * Keep this in lockstep with `VISUALIZATION_FIXTURES`. If the numbers
 * drift the index just shows a slightly stale summary — never throws.
 */
export interface VisualizationSummary {
  runId: string;
  frameCount: number;
  kModes: number;
}

const VISUALIZATION_SUMMARIES: Record<string, Omit<VisualizationSummary, "runId">> = {
  "kawai-kim-natural": { frameCount: 240, kModes: 24 },
  "starobinsky-standard": { frameCount: 240, kModes: 24 },
  "gb-off-control": { frameCount: 240, kModes: 24 },
  "f2-nieh-yan-demo": { frameCount: 240, kModes: 24 },
  "f3-large-N-demo": { frameCount: 240, kModes: 24 },
  "f5-resonance-demo": { frameCount: 240, kModes: 24 },
  "f7-stacked-demo": { frameCount: 240, kModes: 24 },
};

/**
 * Static stream-fixture line counts used by `getStreamFrameCount` so the
 * progress indicator's denominator doesn't require a full HTTP GET of
 * the JSONL just to count newlines.
 */
const STREAM_FRAME_COUNTS: Record<string, number> = {
  "kawai-kim-natural": 60,
};

/**
 * Hard memory ceiling — refuse to load timelines that would balloon the
 * browser heap. Approximated as `JSON.stringify(timeline).length` after
 * fetch (a cheap upper bound). The user is directed to the downloadable
 * Jupyter Book in the empty-state.
 */
const MAX_TIMELINE_BYTES = 200 * 1024 * 1024;

const TIMELINE_TTL_DAYS = 30;

/**
 * Fetch a pre-rendered visualization timeline for a completed run.
 *
 * Resolution order:
 *   1. Storage signed URL (`viz_timelines` row + `viz-timelines` bucket)
 *   2. Bundled fixture (canonical demo runs only)
 *   3. NOT_FOUND
 *
 * On a fixture hit we fire-and-forget a backfill to Storage (signed-in
 * authors only — RLS silently rejects anonymous writes) so the next read
 * is hot. Returns a `BakedVisualizationTimeline` with GPU-ready
 * Float32Array buffers attached as a non-enumerable `baked` property —
 * see `src/lib/visualizerBake.ts`.
 */
export async function getVisualization(runId: string): Promise<BakedVisualizationTimeline> {
  void FEATURES.liveVisualization;

  // 1. Storage first.
  if (FEATURES.persistRuns) {
    const stored = await loadTimelineFromStorage(runId);
    if (stored) {
      guardSize(stored);
      return safeBake(stored);
    }
  }

  // 2. Bundled fixture fallback.
  const path = VISUALIZATION_FIXTURES[runId];
  if (!path) {
    throw new ServiceError(
      "NOT_FOUND",
      `No visualization timeline available for run ${runId}.`,
    );
  }
  const timeline = await loadFixture<VisualizationTimeline>(path, {
    validate: (raw) => VisualizationTimelineShape.parse(raw) as unknown as VisualizationTimeline,
  });
  guardSize(timeline);

  // 3. Best-effort backfill so the next read is hot.
  if (FEATURES.persistRuns) {
    void backfillTimeline(runId, timeline);
  }

  return safeBake(timeline);
}

async function backfillTimeline(
  runId: string,
  timeline: VisualizationTimeline,
): Promise<void> {
  try {
    const { data: auth } = await supabase.auth.getUser();
    if (!auth.user) return;
    const expiresAt = new Date(Date.now() + TIMELINE_TTL_DAYS * 24 * 60 * 60 * 1000);
    await persistVisualizationTimeline({ runId, timeline, expiresAt });
  } catch (err) {
    trackError("service_error", {
      scope: "viz_backfill_failed",
      runId,
      message: err instanceof Error ? err.message : String(err),
    });
  }
}

/**
 * Re-render a visualization at a different resolution / frame count.
 * For running jobs use `streamVisualization` instead.
 */
export async function renderVisualization(
  runId: string,
  opts: RenderOptions,
): Promise<BakedVisualizationTimeline> {
  void FEATURES.liveVisualization;
  void opts;
  // Fixture mode: the resolution tier is purely advisory; we serve the
  // canonical timeline and let the consumer downsample frames in the UI.
  return getVisualization(runId);
}

/**
 * Stream visualization frames from a still-running job.
 *
 * Fixture mode: yields frames from a pre-recorded JSONL file with a
 * 50ms delay between frames. (Live WS path lands with the next backend
 * cutover step.)
 */
export async function* streamVisualization(
  runId: string,
  opts: { signal?: AbortSignal; delayMs?: number } = {},
): AsyncIterable<VisualizationFrame> {
  void FEATURES.liveVisualization;
  void runId;
  // Per-frame guard: a malformed line should be skipped (and tracked)
  // rather than tearing down the whole stream — the live consumer can
  // keep advancing on whatever frames did parse cleanly. The optional
  // `signal` lets the UI cancel mid-stream when the user toggles "Live"
  // off or navigates away from the visualizer route.
  try {
    for await (const frame of loadJsonlFixture<VisualizationFrame>(
      "visualizations/streams/kawai-kim-live.jsonl",
      opts.delayMs ?? 50,
      opts.signal,
    )) {
      yield frame;
    }
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") throw err;
    trackError("service_error", {
      scope: "viz_stream",
      runId,
      message: err instanceof Error ? err.message : String(err),
    });
    throw err instanceof ServiceError
      ? err
      : new ServiceError(
          "UPSTREAM_FAILURE",
          `Visualization stream failed: ${err instanceof Error ? err.message : String(err)}`,
        );
  }
}

/**
 * Quick metadata probe for the streaming progress indicator. Returns
 * the line count of the bundled JSONL fixture so the UI can render a
 * meaningful denominator before the first frame arrives. Returns
 * `null` if the count can't be determined cheaply (e.g. the live WS
 * backend takes over and frame totals are unknown until completion).
 *
 * Backed by `STREAM_FRAME_COUNTS` to avoid re-fetching the entire JSONL
 * on every Live-toggle. Falls back to a one-shot HTTP GET only for ids
 * not in the static map.
 */
const streamFrameCountCache = new Map<string, number | null>();

export async function getStreamFrameCount(runId: string): Promise<number | null> {
  if (runId in STREAM_FRAME_COUNTS) {
    return STREAM_FRAME_COUNTS[runId] ?? null;
  }
  if (streamFrameCountCache.has(runId)) {
    return streamFrameCountCache.get(runId) ?? null;
  }
  try {
    const res = await fetch(
      `/fixtures/visualizations/streams/${encodeURIComponent(runId)}.jsonl`,
    );
    if (!res.ok) {
      streamFrameCountCache.set(runId, null);
      return null;
    }
    const text = await res.text();
    const count = text.split("\n").filter((l) => l.trim().length > 0).length;
    streamFrameCountCache.set(runId, count);
    return count;
  } catch {
    streamFrameCountCache.set(runId, null);
    return null;
  }
}

/** True when a fixture is registered for the given run id. */
export function hasVisualization(runId: string): boolean {
  return runId in VISUALIZATION_FIXTURES;
}

/** Stable list of run ids that ship visualizations. */
export function listVisualizationRunIds(): string[] {
  return Object.keys(VISUALIZATION_FIXTURES);
}

/**
 * Loader-friendly catalog of available visualization runs with the
 * per-run summary inlined. Lets the `/visualizer` index render
 * accurate subtitles ("240 frames · 24 k-modes") without fetching
 * every timeline JSON up front.
 */
export function listVisualizationSummaries(): VisualizationSummary[] {
  return Object.keys(VISUALIZATION_FIXTURES).map((runId) => {
    const summary = VISUALIZATION_SUMMARIES[runId];
    return {
      runId,
      frameCount: summary?.frameCount ?? 0,
      kModes: summary?.kModes ?? 0,
    };
  });
}

function guardSize(timeline: VisualizationTimeline): void {
  let approxBytes: number;
  try {
    approxBytes = JSON.stringify(timeline).length;
  } catch {
    return;
  }
  if (approxBytes > MAX_TIMELINE_BYTES) {
    throw new ServiceError(
      "INVALID_INPUT",
      `Visualization timeline for run ${timeline.runId} is ${(approxBytes / 1024 / 1024).toFixed(
        1,
      )} MB which exceeds the 200 MB browser ceiling. ` +
        "Download the Jupyter Book artifact instead.",
    );
  }
}

function bake(timeline: VisualizationTimeline): BakedVisualizationTimeline {
  const baked = bakeTimelineBuffers(timeline);
  Object.defineProperty(timeline, "baked", {
    value: baked,
    enumerable: false,
    writable: false,
    configurable: false,
  });
  return timeline as BakedVisualizationTimeline;
}

/**
 * Bake wrapper that maps any pre-render crash (mismatched mode counts,
 * NaNs that survived validation, etc.) into a `ServiceError("INVALID_INPUT")`
 * so the route loader's `notifyServiceError(err, "visualization")` path
 * can show a friendly toast instead of a blank workbench.
 */
function safeBake(timeline: VisualizationTimeline): BakedVisualizationTimeline {
  try {
    return bake(timeline);
  } catch (err) {
    throw new ServiceError(
      "INVALID_INPUT",
      `Visualization timeline for ${timeline.runId} couldn't be prepared for rendering: ${
        err instanceof Error ? err.message : String(err)
      }`,
    );
  }
}
