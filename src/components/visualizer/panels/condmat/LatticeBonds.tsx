/**
 * Lattice + bond-strength panel.
 *
 * Each site is a circle; bonds are drawn as the colour-graded
 * line between adjacent sites. Pure SVG so it stays fast for
 * lattices up to a few hundred sites; larger grids should
 * upgrade-path to @react-three/fiber instancing.
 */

import type { CondmatFrame } from "../types";

interface Props {
  frame: CondmatFrame | undefined;
  width?: number;
  height?: number;
}

export function LatticeBonds({ frame, width = 320, height = 320 }: Props) {
  const sites = frame?.lattice_sites ?? [];
  const bonds = frame?.bond_strengths ?? [];
  if (sites.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No lattice data.
      </div>
    );
  }
  const xs = sites.map((s) => s[0]);
  const ys = sites.map((s) => s[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const pad = 24;
  const sx = (x: number) => pad + ((x - minX) / Math.max(1, maxX - minX)) * (width - 2 * pad);
  const sy = (y: number) => pad + ((y - minY) / Math.max(1, maxY - minY)) * (height - 2 * pad);

  // Pair bonds with adjacent lattice sites (i, i+1) for the simple case.
  const bondLines = bonds.slice(0, sites.length - 1).map((w, i) => {
    const a = sites[i];
    const b = sites[Math.min(sites.length - 1, i + 1)];
    return { a, b, w };
  });
  const maxBond = Math.max(0.1, ...bonds.map(Math.abs));

  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        {sites.length} sites · {bonds.length} bonds
      </div>
      <svg width={width} height={height} role="img" aria-label="Lattice bonds">
        {bondLines.map((b, i) => (
          <line
            key={i}
            x1={sx(b.a[0])}
            y1={sy(b.a[1])}
            x2={sx(b.b[0])}
            y2={sy(b.b[1])}
            stroke="hsl(var(--primary, 220 70% 50%))"
            strokeOpacity={Math.min(1, Math.abs(b.w) / maxBond)}
            strokeWidth={1 + (Math.abs(b.w) / maxBond) * 3}
          />
        ))}
        {sites.map(([x, y], i) => (
          <circle
            key={i}
            cx={sx(x)}
            cy={sy(y)}
            r={3}
            fill="hsl(var(--foreground, 220 10% 20%))"
          />
        ))}
      </svg>
    </div>
  );
}

export default LatticeBonds;
