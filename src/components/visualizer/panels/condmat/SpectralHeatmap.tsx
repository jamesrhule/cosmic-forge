import { useMemo } from "react";
import type { CondmatFrame } from "@/types/manifest";

export interface SpectralHeatmapProps {
  frame: CondmatFrame | null;
}

/**
 * Spectral function A(k, ω) heatmap. Falls back to an SVG rect grid;
 * the optional `@visx/heatmap` path can replace the inner grid via a
 * dynamic import without changing the public props.
 */
export function SpectralHeatmap({ frame }: SpectralHeatmapProps) {
  const data = frame?.spectral_function_Akw ?? null;

  const grid = useMemo(() => {
    if (!data) return null;
    const nk = data.k.length;
    const no = data.omega.length;
    if (nk === 0 || no === 0) return null;
    let max = 0;
    for (const row of data.Akw) for (const v of row) if (v > max) max = v;
    return { nk, no, Akw: data.Akw, max: Math.max(max, 1e-6) };
  }, [data]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        Spectral function A(k, ω)
      </div>
      <div className="min-h-0 flex-1 p-2">
        {!grid ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
          <svg
            viewBox={`0 0 ${grid.no} ${grid.nk}`}
            preserveAspectRatio="none"
            className="h-full w-full"
            role="img"
            aria-label="A(k, ω) heatmap"
          >
            {grid.Akw.map((row, ki) =>
              row.map((v, oi) => {
                const t = v / grid.max;
                const hue = 0.6 - 0.6 * t;
                return (
                  <rect
                    key={`${ki}-${oi}`}
                    x={oi}
                    y={ki}
                    width={1}
                    height={1}
                    fill={`hsl(${hue * 360}, 70%, ${20 + 60 * t}%)`}
                  />
                );
              }),
            )}
          </svg>
        )}
      </div>
    </div>
  );
}
