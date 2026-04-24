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
export async function* streamVisualization(runId: string): AsyncIterable<VisualizationFrame> {
  void FEATURES.liveVisualization;
  void runId;
  // Per-frame guard: a malformed line should be skipped (and tracked)
  // rather than tearing down the whole stream — the live consumer can
  // keep advancing on whatever frames did parse cleanly.
  try {
    for await (const frame of loadJsonlFixture<VisualizationFrame>(
      "visualizations/streams/kawai-kim-live.jsonl",
      50,
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

/** True when a fixture is registered for the given run id. */
export function hasVisualization(runId: string): boolean {
  return runId in VISUALIZATION_FIXTURES;
}

/** Stable list of run ids that ship visualizations. */
export function listVisualizationRunIds(): string[] {
  return Object.keys(VISUALIZATION_FIXTURES);
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
