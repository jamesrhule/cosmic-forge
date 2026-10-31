/**
 * Spectral function A(k, ω) heatmap.
 */

import type { CondmatFrame } from "../types";

interface Props {
  frame: CondmatFrame | undefined;
  width?: number;
  height?: number;
}

export function SpectralHeatmap({ frame, width = 320, height = 240 }: Props) {
  const grid = frame?.spectral ?? [];
  if (grid.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No spectral data.
      </div>
    );
  }
  const K = grid.length;
  const W = grid[0]?.length ?? 0;
  const cellW = (width - 16) / Math.max(1, K);
  const cellH = (height - 16) / Math.max(1, W);
  const flat = grid.flat();
  const max = Math.max(0.01, ...flat);
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        A(k, ω) — {K} k × {W} ω
      </div>
      <svg width={width} height={height} role="img" aria-label="Spectral heatmap">
        {grid.map((row, k) =>
          row.map((v, w) => (
            <rect
              key={`${k}-${w}`}
              x={8 + k * cellW}
              y={8 + (W - 1 - w) * cellH}
              width={cellW}
              height={cellH}
              fill="hsl(280 80% 55%)"
              fillOpacity={Math.min(1, v / max)}
            />
          ))
        )}
      </svg>
    </div>
  );
}

export default SpectralHeatmap;
