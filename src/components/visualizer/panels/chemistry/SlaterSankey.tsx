/**
 * Slater-flow Sankey diagram (orbital ↔ orbital weight matrix).
 *
 * Renders each non-trivial entry of the slater matrix as a chord.
 * Stays SVG-only so the panel works without visx imports loaded;
 * upgrade-path swaps in @visx/sankey when ≥1k chords land.
 */

import type { ChemistryFrame } from "../types";

interface Props {
  frame: ChemistryFrame | undefined;
  width?: number;
  height?: number;
  threshold?: number;
}

export function SlaterSankey({
  frame, width = 320, height = 240, threshold = 0.05,
}: Props) {
  const matrix = frame?.slater ?? [];
  if (matrix.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No Slater weights for this frame.
      </div>
    );
  }
  const n = matrix.length;
  const pad = 32;
  const colW = (width - pad * 2) / 2;
  const rowStep = (height - pad * 2) / Math.max(1, n - 1);
  const flows: Array<{ i: number; j: number; w: number }> = [];
  matrix.forEach((row, i) => {
    row.forEach((w, j) => {
      if (Math.abs(w) >= threshold) flows.push({ i, j, w });
    });
  });
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        Slater flow ({flows.length} edges over threshold {threshold})
      </div>
      <svg width={width} height={height} role="img" aria-label="Slater flow Sankey">
        {Array.from({ length: n }).map((_, i) => (
          <g key={`l-${i}`}>
            <text x={pad} y={pad + i * rowStep + 4} fontSize={10} textAnchor="end" fill="currentColor">
              {i}
            </text>
            <text x={pad + colW * 2 + 4} y={pad + i * rowStep + 4} fontSize={10} fill="currentColor">
              {i}
            </text>
          </g>
        ))}
        {flows.map((f, idx) => (
          <line
            key={idx}
            x1={pad + 2}
            y1={pad + f.i * rowStep}
            x2={pad + colW * 2 - 2}
            y2={pad + f.j * rowStep}
            stroke="hsl(var(--primary, 220 70% 50%))"
            strokeOpacity={Math.min(1, Math.abs(f.w) * 5)}
            strokeWidth={1 + Math.abs(f.w) * 4}
          />
        ))}
      </svg>
    </div>
  );
}

export default SlaterSankey;
