/**
 * Per-shell occupation bars.
 */

import type { NuclearFrame } from "../types";

interface Props {
  frame: NuclearFrame | undefined;
  width?: number;
  height?: number;
}

export function ShellOccupation({ frame, width = 320, height = 220 }: Props) {
  const occ = frame?.shell_occupation ?? [];
  if (occ.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No shell-occupation data.
      </div>
    );
  }
  const max = Math.max(0.1, ...occ);
  const barW = Math.max(8, Math.floor((width - 32) / occ.length));
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        Shell occupation — {occ.length} levels, max ⟨n⟩ = {max.toFixed(2)}
      </div>
      <svg width={width} height={height} role="img" aria-label="Shell occupation">
        <g transform="translate(16,16)">
          {occ.map((n, i) => {
            const h = ((height - 48) * n) / max;
            return (
              <g key={i} transform={`translate(${i * barW},${(height - 48) - h})`}>
                <rect
                  width={barW - 2}
                  height={h}
                  fill="hsl(200 60% 50%)"
                  fillOpacity={0.75}
                />
                <text
                  x={(barW - 2) / 2}
                  y={h + 14}
                  fontSize={10}
                  textAnchor="middle"
                  fill="currentColor"
                >
                  {i}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}

export default ShellOccupation;
