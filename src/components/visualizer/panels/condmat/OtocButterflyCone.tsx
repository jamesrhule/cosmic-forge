/**
 * OTOC butterfly cone (condensed matter).
 *
 * Reconciles the agent-branch `OtocButterfly` and the router-branch
 * `OtocButterflyCone` (P0-02): one time × distance heatmap shaded by
 * |C(t, x)|, with the agent caption. Axes are labelled as indices when
 * the source gave no physical axis values.
 */
import { useMemo } from "react";
import type { CondmatFrame } from "../types";
import { PanelShell } from "../PanelShell";

export interface OtocButterflyConeProps {
  frame: CondmatFrame | null;
}

export function OtocButterflyCone({ frame }: OtocButterflyConeProps) {
  const otoc = frame?.otoc_butterfly ?? null;

  const grid = useMemo(() => {
    if (!otoc) return null;
    const t = otoc.intensity.length;
    const d = otoc.intensity[0]?.length ?? 0;
    if (t === 0 || d === 0) return null;
    let max = 0;
    for (const row of otoc.intensity) for (const v of row) max = Math.max(max, Math.abs(v));
    return { t, d, intensity: otoc.intensity, max: Math.max(max, 1e-6) };
  }, [otoc]);

  const axisNote = otoc?.axes === "index" ? " (index axes)" : "";

  return (
    <PanelShell
      title="OTOC butterfly cone"
      empty={!grid}
      caption={
        grid ? (
          <>
            {grid.t} t × {grid.d} x{axisNote} · max |C(t,x)| = {grid.max.toFixed(3)}
          </>
        ) : null
      }
    >
      {grid ? (
        <svg
          viewBox={`0 0 ${grid.d} ${grid.t}`}
          preserveAspectRatio="none"
          className="h-full w-full"
          role="img"
          aria-label="OTOC butterfly intensity"
        >
          {grid.intensity.map((row, ti) =>
            row.map((v, di) => {
              const t = Math.abs(v) / grid.max;
              const hue = 0.05 + 0.7 * (1 - t); // bright red high → blue low
              return (
                <rect
                  key={`${ti}-${di}`}
                  x={di}
                  y={ti}
                  width={1}
                  height={1}
                  fill={`hsl(${hue * 360}, 80%, ${(0.2 + 0.6 * t) * 100}%)`}
                />
              );
            }),
          )}
        </svg>
      ) : null}
    </PanelShell>
  );
}

export default OtocButterflyCone;
