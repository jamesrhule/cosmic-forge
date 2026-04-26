import { useMemo } from "react";
import type { HepFrame } from "@/types/manifest";

export interface GaugePlaquettesProps {
  frame: HepFrame | null;
}

/**
 * Project plaquettes onto z=0 and shade by flux. A simple SVG grid is
 * cheaper than R3F here and the depth dimension averages out for a
 * scalar overlay anyway.
 */
export function GaugePlaquettes({ frame }: GaugePlaquettesProps) {
  const projected = useMemo(() => {
    if (!frame || frame.plaquettes.length === 0) return null;
    const cells = new Map<string, { flux: number; count: number }>();
    let maxAbs = 0;
    for (const p of frame.plaquettes) {
      const key = `${p.cell[0]},${p.cell[1]}`;
      const existing = cells.get(key) ?? { flux: 0, count: 0 };
      existing.flux += p.flux;
      existing.count += 1;
      cells.set(key, existing);
    }
    const rows: Array<{ x: number; y: number; flux: number }> = [];
    let max = 0;
    for (const [key, v] of cells) {
      const [x, y] = key.split(",").map(Number);
      const avg = v.flux / Math.max(1, v.count);
      max = Math.max(max, Math.abs(avg));
      rows.push({ x, y, flux: avg });
    }
    maxAbs = Math.max(max, 1e-9);
    const xs = rows.map((r) => r.x);
    const ys = rows.map((r) => r.y);
    const xMin = Math.min(...xs);
    const yMin = Math.min(...ys);
    const xMax = Math.max(...xs);
    const yMax = Math.max(...ys);
    return { rows, xMin, yMin, xMax, yMax, maxAbs };
  }, [frame]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        Gauge plaquettes (z-projected flux)
      </div>
      <div className="min-h-0 flex-1 p-2">
        {!projected ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
          <svg
            viewBox={`${projected.xMin} ${projected.yMin} ${projected.xMax - projected.xMin + 1} ${
              projected.yMax - projected.yMin + 1
            }`}
            preserveAspectRatio="xMidYMid meet"
            className="h-full w-full"
            role="img"
            aria-label="Gauge plaquette flux grid"
          >
            {projected.rows.map((r) => {
              const t = r.flux / projected.maxAbs; // -1..1
              const hue = t > 0 ? 0.0 : 0.66; // red positive, blue negative
              const lightness = 0.4 + 0.4 * Math.abs(t);
              return (
                <rect
                  key={`${r.x},${r.y}`}
                  x={r.x}
                  y={r.y}
                  width={0.95}
                  height={0.95}
                  fill={`hsl(${hue * 360}, 75%, ${lightness * 100}%)`}
                />
              );
            })}
          </svg>
        )}
      </div>
    </div>
  );
}
