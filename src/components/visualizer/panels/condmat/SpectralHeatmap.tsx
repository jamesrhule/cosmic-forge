/**
 * Spectral function A(k, ω) heatmap (condensed matter).
 *
 * Merged panel (P0-02): router-branch rect grid (k rows × ω columns)
 * plus the agent-branch size caption. Axes are labelled as indices when
 * the source gave no physical k / ω values.
 */
import { useMemo } from "react";
import type { CondmatFrame } from "../types";
import { PanelShell } from "../PanelShell";

export interface SpectralHeatmapProps {
  frame: CondmatFrame | null;
}

export function SpectralHeatmap({ frame }: SpectralHeatmapProps) {
  const data = frame?.spectral_function_Akw ?? null;

  const grid = useMemo(() => {
    if (!data) return null;
    const nk = data.Akw.length;
    const no = data.Akw[0]?.length ?? 0;
    if (nk === 0 || no === 0) return null;
    let max = 0;
    for (const row of data.Akw) for (const v of row) if (v > max) max = v;
    return { nk, no, Akw: data.Akw, max: Math.max(max, 1e-6) };
  }, [data]);

  const range = (xs: number[]) =>
    xs.length > 0 ? `[${Math.min(...xs).toFixed(2)}, ${Math.max(...xs).toFixed(2)}]` : "—";

  return (
    <PanelShell
      title="Spectral function A(k, ω)"
      empty={!grid}
      caption={
        grid && data ? (
          data.axes === "index" ? (
            <>
              {grid.nk} k × {grid.no} ω (index axes)
            </>
          ) : (
            <>
              k ∈ {range(data.k)} · ω ∈ {range(data.omega)}
            </>
          )
        ) : null
      }
    >
      {grid ? (
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
              return (
                <rect
                  key={`${ki}-${oi}`}
                  x={oi}
                  y={ki}
                  width={1}
                  height={1}
                  fill={`hsl(${(0.6 - 0.6 * t) * 360}, 70%, ${20 + 60 * t}%)`}
                />
              );
            }),
          )}
        </svg>
      ) : null}
    </PanelShell>
  );
}

export default SpectralHeatmap;
