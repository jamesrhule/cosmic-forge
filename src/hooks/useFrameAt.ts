import type { BakedVisualizationTimeline, VisualizationFrame } from "@/types/visualizer";

/**
 * Pick a frame from a timeline by integer index or by τ.
 *
 * - `pick: number | { tau: number }`
 * - Out-of-range indices are clamped to `[0, frames.length - 1]`.
 * - When picking by τ we do a linear search (frames are typically
 *   small; binary search adds complexity for ~200-frame fixtures).
 */
export function pickFrame(
  timeline: BakedVisualizationTimeline,
  pick: number | { tau: number },
): { index: number; frame: VisualizationFrame } {
  const frames = timeline.frames;
  if (frames.length === 0) {
    throw new Error("Timeline has no frames");
  }

  if (typeof pick === "number") {
    const i = clamp(Math.round(pick), 0, frames.length - 1);
    return { index: i, frame: frames[i] };
  }

  const targetTau = pick.tau;
  let bestIdx = 0;
  let bestDist = Infinity;
  for (let i = 0; i < frames.length; i++) {
    const d = Math.abs(frames[i].tau - targetTau);
    if (d < bestDist) {
      bestDist = d;
      bestIdx = i;
    }
  }
  return { index: bestIdx, frame: frames[bestIdx] };
}

/**
 * Resolve "the same phase" in a partner timeline. Used by Sync-by-phase
 * comparison mode. Falls back to proportional index mapping when the
 * partner timeline doesn't have the requested phase boundary.
 */
export function mapFrameByPhase(
  source: BakedVisualizationTimeline,
  target: BakedVisualizationTimeline,
  sourceIndex: number,
): number {
  const sFrame = source.frames[clamp(sourceIndex, 0, source.frames.length - 1)];
  const phase = sFrame?.phase;
  const sBoundary = source.meta.phaseBoundaries[phase];
  const tBoundary = target.meta.phaseBoundaries[phase];

  if (!sBoundary || !tBoundary) {
    // Proportional fallback so the playheads at least stay in sync.
    const ratio = sourceIndex / Math.max(1, source.frames.length - 1);
    return Math.round(ratio * (target.frames.length - 1));
  }

  const [sStart, sEnd] = sBoundary;
  const [tStart, tEnd] = tBoundary;
  const sLen = Math.max(1, sEnd - sStart);
  const tLen = Math.max(0, tEnd - tStart);
  const local = clamp((sourceIndex - sStart) / sLen, 0, 1);
  return Math.round(tStart + local * tLen);
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}
