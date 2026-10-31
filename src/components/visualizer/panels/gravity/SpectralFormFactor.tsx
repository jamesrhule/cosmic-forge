/**
 * Spectral form factor g(t) trace for gravity (SYK / JT) frames.
 */

import type { GravityFrame } from "../types";

interface Props {
  frame: GravityFrame | undefined;
  width?: number;
  height?: number;
}

export function SpectralFormFactor({ frame, width = 320, height = 200 }: Props) {
  const sff = frame?.spectral_form_factor ?? [];
  if (sff.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No SFF data.
      </div>
    );
  }
  const maxV = Math.max(0.1, ...sff);
  const pad = 24;
  const w = width - pad * 2;
  const h = height - pad * 2;
  const points = sff.map((v, i) => {
    const x = pad + (i / Math.max(1, sff.length - 1)) * w;
    const y = pad + h - (v / maxV) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        Spectral form factor g(t) — {sff.length} samples
      </div>
      <svg width={width} height={height} role="img" aria-label="SFF trace">
        <polyline
          points={points}
          fill="none"
          stroke="hsl(280 70% 55%)"
          strokeWidth={1.5}
        />
      </svg>
    </div>
  );
}

export default SpectralFormFactor;
