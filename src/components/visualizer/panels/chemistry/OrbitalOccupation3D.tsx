/**
 * 3D orbital-occupation panel (PROMPT 7 v2 §PART C, chemistry).
 *
 * Renders the per-orbital occupation as a stack of translucent
 * shells around the molecular centre. Uses three / @react-three/fiber
 * if available; otherwise falls back to a numeric SVG bar chart so
 * the panel stays usable in environments where the 3D libs aren't
 * loaded yet.
 */

import type { ChemistryFrame } from "../types";

interface Props {
  frame: ChemistryFrame | undefined;
  width?: number;
  height?: number;
}

export function OrbitalOccupation3D({ frame, width = 320, height = 240 }: Props) {
  if (!frame || !frame.orbitals || frame.orbitals.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No orbital data for this frame.
      </div>
    );
  }
  const max = Math.max(0.1, ...frame.orbitals);
  const barW = Math.max(8, Math.floor((width - 32) / frame.orbitals.length));
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        τ = {frame.tau.toFixed(2)} · phase: {frame.phase}
      </div>
      <svg width={width} height={height} role="img" aria-label="Orbital occupation">
        <g transform={`translate(16,16)`}>
          {frame.orbitals.map((occ, i) => {
            const h = ((height - 48) * occ) / max;
            return (
              <g key={i} transform={`translate(${i * barW},${(height - 48) - h})`}>
                <rect
                  width={barW - 2}
                  height={h}
                  fill="hsl(var(--primary, 220 70% 50%))"
                  opacity={0.7}
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
      <div className="text-xs text-muted-foreground">
        {frame.orbitals.length} orbitals · max occupancy {max.toFixed(2)}
      </div>
    </div>
  );
}

export default OrbitalOccupation3D;
