/**
 * Rydberg-Rydberg correlation matrix heatmap.
 */

import type { AmoFrame } from "../types";

interface Props {
  frame: AmoFrame | undefined;
  width?: number;
  height?: number;
}

export function BlockadeCorrelations({
  frame, width = 240, height = 240,
}: Props) {
  const C = frame?.correlations ?? [];
  if (C.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No correlation matrix.
      </div>
    );
  }
  const N = C.length;
  const cell = (Math.min(width, height) - 16) / Math.max(1, N);
  const max = Math.max(0.01, ...C.flat());
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        ⟨σ_z^i σ_z^j⟩ — {N}×{N}, max = {max.toFixed(3)}
      </div>
      <svg width={N * cell + 16} height={N * cell + 16} role="img" aria-label="Blockade correlations">
        {C.map((row, i) =>
          row.map((v, j) => (
            <rect
              key={`${i}-${j}`}
              x={8 + j * cell}
              y={8 + i * cell}
              width={cell - 1}
              height={cell - 1}
              fill="hsl(280 80% 55%)"
              fillOpacity={Math.min(1, v / max)}
            />
          ))
        )}
      </svg>
    </div>
  );
}

export default BlockadeCorrelations;
