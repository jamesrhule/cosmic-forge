/**
 * Atom-array layout panel.
 *
 * Renders the (x, y) projection of the 3D positions plus a circle
 * showing each atom's Rydberg blockade radius. Pure SVG — upgrade
 * to @react-three/fiber when the workflow needs the third axis.
 */

import type { AmoFrame } from "../types";

interface Props {
  frame: AmoFrame | undefined;
  width?: number;
  height?: number;
}

export function AtomArray3D({ frame, width = 320, height = 240 }: Props) {
  const positions = frame?.atom_positions ?? [];
  const blockade = frame?.blockade_radii ?? [];
  if (positions.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No atom positions.
      </div>
    );
  }
  const xs = positions.map((p) => p[0]);
  const ys = positions.map((p) => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const pad = 24;
  const sx = (x: number) =>
    pad + ((x - minX) / Math.max(1e-6, maxX - minX)) * (width - 2 * pad);
  const sy = (y: number) =>
    pad + ((y - minY) / Math.max(1e-6, maxY - minY)) * (height - 2 * pad);
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        {positions.length} atoms (μm) — Rydberg blockade overlay
      </div>
      <svg width={width} height={height} role="img" aria-label="Atom array">
        {positions.map(([x, y], i) => (
          <g key={i}>
            <circle
              cx={sx(x)}
              cy={sy(y)}
              r={Math.max(8, (blockade[i] ?? 4) * 2)}
              fill="hsl(220 70% 50%)"
              fillOpacity={0.12}
              stroke="hsl(220 70% 50%)"
              strokeOpacity={0.5}
            />
            <circle cx={sx(x)} cy={sy(y)} r={3} fill="hsl(220 70% 30%)" />
          </g>
        ))}
      </svg>
    </div>
  );
}

export default AtomArray3D;
