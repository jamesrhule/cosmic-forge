/**
 * Gauge plaquettes (HEP).
 *
 * Merged panel (P0-02): router-branch z-projected cell grid, shaded by
 * plaquette flux when provided, otherwise by the plaquette action
 * density (the flat wire shape's S_p), plus the agent-branch caption.
 */
import { useMemo } from "react";
import type { HepFrame } from "../types";
import { PanelShell } from "../PanelShell";

export interface GaugePlaquettesProps {
  frame: HepFrame | null;
}

export function GaugePlaquettes({ frame }: GaugePlaquettesProps) {
  const projected = useMemo(() => {
    const ps = frame?.plaquettes ?? [];
    if (ps.length === 0) return null;
    const useFlux = ps.every((p) => p.flux !== null);
    const quantity = useFlux ? "flux" : "action density S_p";
    const cells = new Map<string, { sum: number; count: number }>();
    for (const p of ps) {
      const v = useFlux ? p.flux : p.energy;
      if (v === null) continue;
      const key = `${p.cell[0]},${p.cell[1]}`;
      const c = cells.get(key) ?? { sum: 0, count: 0 };
      c.sum += v;
      c.count += 1;
      cells.set(key, c);
    }
    if (cells.size === 0) return null;
    const rows = [...cells].map(([key, c]) => {
      const [x, y] = key.split(",").map(Number);
      return { x, y, v: c.sum / Math.max(1, c.count) };
    });
    const maxAbs = Math.max(1e-9, ...rows.map((r) => Math.abs(r.v)));
    const xs = rows.map((r) => r.x);
    const ys = rows.map((r) => r.y);
    return {
      rows,
      quantity,
      count: ps.length,
      maxAbs,
      xMin: Math.min(...xs),
      yMin: Math.min(...ys),
      w: Math.max(...xs) - Math.min(...xs) + 1,
      h: Math.max(...ys) - Math.min(...ys) + 1,
    };
  }, [frame]);

  return (
    <PanelShell
      title="Gauge plaquettes (z-projected)"
      empty={!projected}
      caption={projected ? <>{projected.count} plaquettes · {projected.quantity} · max |·| = {projected.maxAbs.toFixed(3)}</> : null}
    >
      {projected ? (
        <svg
          viewBox={`${projected.xMin} ${projected.yMin} ${projected.w} ${Math.max(projected.h, projected.w / 8)}`}
          preserveAspectRatio="xMidYMid meet"
          className="h-full w-full"
          role="img"
          aria-label="Gauge plaquette grid"
        >
          {projected.rows.map((r) => {
            const t = r.v / projected.maxAbs; // -1..1
            const hue = t > 0 ? 0 : 0.66; // red positive, blue negative
            return (
              <rect
                key={`${r.x},${r.y}`}
                x={r.x}
                y={r.y}
                width={0.95}
                height={0.95}
                fill={`hsl(${hue * 360}, 75%, ${(0.4 + 0.4 * Math.abs(t)) * 100}%)`}
              />
            );
          })}
        </svg>
      ) : null}
    </PanelShell>
  );
}

export default GaugePlaquettes;
