import { FEATURES } from "@/config/features";
import { loadFixture, loadJsonlFixture } from "@/lib/fixtures";
import { ServiceError } from "@/types/domain";
import { bakeTimelineBuffers } from "@/lib/visualizerBake";
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

/**
 * Fetch a pre-rendered visualization timeline for a completed run.
 *
 * Backend: GET /api/runs/{runId}/visualization
 *   → 200 { VisualizationTimeline }
 *   → 404 if run not found
 *   → 409 if the run completed before the visualizer integration shipped
 *
 * Returns a `BakedVisualizationTimeline` with GPU-ready Float32Array
 * buffers attached as a non-enumerable `baked` property — see
 * `src/lib/visualizerBake.ts`.
 */
export async function getVisualization(
  runId: string,
): Promise<BakedVisualizationTimeline> {
  void FEATURES.liveVisualization;
  const path = VISUALIZATION_FIXTURES[runId];
  if (!path) {
    throw new ServiceError(
      "NOT_FOUND",
      `No visualization fixture for run ${runId}.`,
    );
  }
  const timeline = await loadFixture<VisualizationTimeline>(path);
  guardSize(timeline);
  return bake(timeline);
}

/**
 * Re-render a visualization at a different resolution / frame count.
 * For running jobs use `streamVisualization` instead.
 *
 * Backend: POST /api/runs/{runId}/visualization/render
 *   body: { resolution, framesCount? }
 *   → 202 { VisualizationTimeline }   (server may downsample frames)
 */
export async function renderVisualization(
  runId: string,
  opts: RenderOptions,
): Promise<BakedVisualizationTimeline> {
  void FEATURES.liveVisualization;
  void opts;
  // Fixture mode: the resolution tier is purely advisory; we serve the
  // canonical fixture and let the consumer downsample frames in the UI.
  return getVisualization(runId);
}

/**
 * Stream visualization frames from a still-running job. One frame per
 * simulator checkpoint (recommended ~30 frames per cosmological e-fold
 * by Claude Code).
 *
 * Backend: WebSocket /ws/runs/{runId}/visualization-live
 *   → message per frame: VisualizationFrame
 *   → close on completion
 *
 * Fixture mode: yields frames from a pre-recorded JSONL file with a
 * 50ms delay between frames.
 */
export async function* streamVisualization(
  runId: string,
): AsyncIterable<VisualizationFrame> {
  void FEATURES.liveVisualization;
  void runId;
  yield* loadJsonlFixture<VisualizationFrame>(
    "visualizations/streams/kawai-kim-live.jsonl",
    50,
  );
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
  // Cheap upper bound — JSON serialisation overhead means the in-memory
  // footprint is smaller, so this errs on the side of letting things load.
  let approxBytes: number;
  try {
    approxBytes = JSON.stringify(timeline).length;
  } catch {
    return; // pathological cycles — let downstream complain
  }
  if (approxBytes > MAX_TIMELINE_BYTES) {
    throw new ServiceError(
      "OVERSIZED",
      `Visualization timeline for run ${timeline.runId} is ${(
        approxBytes /
        1024 /
        1024
      ).toFixed(1)} MB which exceeds the 200 MB browser ceiling. ` +
        "Download the Jupyter Book artifact instead.",
    );
  }
}

function bake(timeline: VisualizationTimeline): BakedVisualizationTimeline {
  const baked = bakeTimelineBuffers(timeline);
  // Non-enumerable so React's structural sharing doesn't iterate the
  // (potentially huge) typed arrays during devtools inspection.
  Object.defineProperty(timeline, "baked", {
    value: baked,
    enumerable: false,
    writable: false,
    configurable: false,
  });
  return timeline as BakedVisualizationTimeline;
}
