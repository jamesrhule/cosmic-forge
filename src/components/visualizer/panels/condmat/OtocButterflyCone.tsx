import { useMemo } from "react";
import type { CondmatFrame } from "@/types/manifest";

export interface OtocButterflyConeProps {
  frame: CondmatFrame | null;
}

/**
 * OTOC butterfly heatmap: time × distance, shaded by intensity.
 * Renders to a canvas via direct ImageData writes — keeps the panel
 * self-contained without a charting dep, and the cone-of-influence
 * shape emerges naturally from the underlying intensity data.
 */
export function OtocButterflyCone({ frame }: OtocButterflyConeProps) {
  const otoc = frame?.otoc_butterfly ?? null;

  const grid = useMemo(() => {
    if (!otoc) return null;
    const t = otoc.times.length;
    const d = otoc.distances.length;
    if (t === 0 || d === 0) return null;
    let max = 0;
    for (const row of otoc.intensity) {
      for (const v of row) if (v > max) max = v;
    }
    return { t, d, intensity: otoc.intensity, max: Math.max(max, 1e-6) };
  }, [otoc]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        OTOC butterfly cone
      </div>
      <div className="min-h-0 flex-1 p-2">
        {!grid ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
          <OtocCanvas grid={grid} />
        )}
      </div>
    </div>
  );
}

function OtocCanvas({
  grid,
}: {
  grid: { t: number; d: number; intensity: number[][]; max: number };
}) {
  return (
    <div className="grid h-full w-full">
      <svg
        viewBox={`0 0 ${grid.d} ${grid.t}`}
        preserveAspectRatio="none"
        className="h-full w-full"
        role="img"
        aria-label="OTOC butterfly intensity"
      >
        {grid.intensity.map((row, ti) =>
          row.map((v, di) => {
            const t = v / grid.max;
            const hue = 0.05 + 0.7 * (1 - t); // bright red high → blue low
            const lightness = 0.2 + 0.6 * t;
            return (
              <rect
                key={`${ti}-${di}`}
                x={di}
                y={ti}
                width={1}
                height={1}
                fill={`hsl(${hue * 360}, 80%, ${lightness * 100}%)`}
              />
            );
          }),
        )}
      </svg>
    </div>
  );
}
