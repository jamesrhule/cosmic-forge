/**
 * Per-plaquette gauge action density for the lattice-gauge frame.
 */

import type { HepFrame } from "../types";

interface Props {
  frame: HepFrame | undefined;
  width?: number;
  height?: number;
}

export function GaugePlaquettes({ frame, width = 320, height = 200 }: Props) {
  const ps = frame?.plaquettes ?? [];
  if (ps.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No plaquette data.
      </div>
    );
  }
  const cell = Math.max(8, Math.floor((width - 16) / ps.length));
  const max = Math.max(0.01, ...ps.map(Math.abs));
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        {ps.length} plaquettes · max |S_p| = {max.toFixed(3)}
      </div>
      <svg width={width} height={height} role="img" aria-label="Gauge plaquettes">
        {ps.map((s, i) => {
          const h = ((height - 32) * Math.abs(s)) / max;
          return (
            <rect
              key={i}
              x={8 + i * cell}
              y={(height - 16) - h}
              width={cell - 2}
              height={h}
              fill={s >= 0 ? "hsl(220 70% 50%)" : "hsl(0 70% 50%)"}
              fillOpacity={0.7}
            />
          );
        })}
      </svg>
    </div>
  );
}

export default GaugePlaquettes;
