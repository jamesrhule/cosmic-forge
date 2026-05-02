/**
 * Animated string-breaking trace.
 *
 * Surfaces the per-frame string_tension as a moving baseline that
 * "breaks" (drops) when the value crosses a vacuum-quark threshold.
 * For now we render the τ-trace + a marker at the most recent frame;
 * full motion via `motion` lands when the visualizer's animation
 * primitive ships.
 */

import type { HepFrame } from "../types";

interface Props {
  frames: HepFrame[];
  currentTau?: number;
  width?: number;
  height?: number;
}

export function StringBreakingAnim({
  frames, currentTau, width = 320, height = 180,
}: Props) {
  if (!frames || frames.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No string-tension trace.
      </div>
    );
  }
  const taus = frames.map((f) => f.tau);
  const ts = frames.map((f) => f.string_tension);
  const minT = Math.min(...taus);
  const maxT = Math.max(...taus);
  const maxV = Math.max(0.5, ...ts);
  const pad = 24;
  const w = width - pad * 2;
  const h = height - pad * 2;
  const path = frames.map((f, i) => {
    const x = pad + ((f.tau - minT) / Math.max(1e-9, maxT - minT)) * w;
    const y = pad + h - (f.string_tension / maxV) * h;
    return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
  const cur = currentTau ?? frames[frames.length - 1].tau;
  const cx = pad + ((cur - minT) / Math.max(1e-9, maxT - minT)) * w;
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        String tension σ(τ) — peak {maxV.toFixed(3)}
      </div>
      <svg width={width} height={height} role="img" aria-label="String breaking">
        <path d={path} fill="none" stroke="hsl(28 90% 55%)" strokeWidth={1.6} />
        <line x1={cx} y1={pad} x2={cx} y2={pad + h} stroke="hsl(220 70% 50%)" strokeDasharray="4 2" />
      </svg>
    </div>
  );
}

export default StringBreakingAnim;
