/**
 * Chiral-condensate τ-trace across all frames.
 *
 * Unlike the per-frame panels, this one consumes the whole timeline
 * to plot ⟨ψ̄ψ⟩(τ).
 */

import type { HepFrame } from "../types";

interface Props {
  frames: HepFrame[];
  width?: number;
  height?: number;
}

export function ChiralCondensateTrace({
  frames, width = 320, height = 200,
}: Props) {
  if (!frames || frames.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No chiral-condensate trace.
      </div>
    );
  }
  const taus = frames.map((f) => f.tau);
  const vals = frames.map((f) => f.chiral_condensate);
  const minT = Math.min(...taus);
  const maxT = Math.max(...taus);
  const minV = Math.min(0, ...vals);
  const maxV = Math.max(0.01, ...vals);
  const pad = 28;
  const w = width - pad * 2;
  const h = height - pad * 2;
  const points = frames.map((f, i) => {
    const x = pad + ((f.tau - minT) / Math.max(1e-9, maxT - minT)) * w;
    const y = pad + h - ((f.chiral_condensate - minV) / Math.max(1e-9, maxV - minV)) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        ⟨ψ̄ψ⟩(τ) — {frames.length} frames, range [{minV.toFixed(3)}, {maxV.toFixed(3)}]
      </div>
      <svg width={width} height={height} role="img" aria-label="Chiral condensate trace">
        <polyline
          points={points}
          fill="none"
          stroke="hsl(140 65% 45%)"
          strokeWidth={1.5}
        />
        <text x={pad} y={pad - 4} fontSize={10} fill="currentColor">⟨ψ̄ψ⟩</text>
        <text x={width - pad} y={height - 4} fontSize={10} textAnchor="end" fill="currentColor">τ</text>
      </svg>
    </div>
  );
}

export default ChiralCondensateTrace;
