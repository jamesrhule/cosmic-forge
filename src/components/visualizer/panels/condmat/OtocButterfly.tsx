/**
 * OTOC butterfly heatmap (out-of-time-order correlator).
 *
 * Renders the (t, site) heatmap as a grid of cells; intensity ≈
 * |OTOC|. The "butterfly cone" is visible as the diagonal that
 * separates pre-scrambling and post-scrambling regions.
 */

import type { CondmatFrame } from "../types";

interface Props {
  frame: CondmatFrame | undefined;
  width?: number;
  height?: number;
}

export function OtocButterfly({ frame, width = 320, height = 200 }: Props) {
  const grid = frame?.otoc ?? [];
  if (grid.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No OTOC data.
      </div>
    );
  }
  const T = grid.length;
  const N = grid[0]?.length ?? 0;
  const cellW = (width - 16) / Math.max(1, N);
  const cellH = (height - 16) / Math.max(1, T);
  const flat = grid.flat();
  const max = Math.max(0.01, ...flat.map(Math.abs));
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        OTOC ({T}t × {N}site), max |C(t,x)| = {max.toFixed(3)}
      </div>
      <svg width={width} height={height} role="img" aria-label="OTOC butterfly">
        {grid.map((row, t) =>
          row.map((v, i) => {
            const a = Math.min(1, Math.abs(v) / max);
            return (
              <rect
                key={`${t}-${i}`}
                x={8 + i * cellW}
                y={8 + t * cellH}
                width={cellW}
                height={cellH}
                fill="hsl(var(--primary, 220 70% 50%))"
                fillOpacity={a}
              />
            );
          })
        )}
      </svg>
    </div>
  );
}

export default OtocButterfly;
