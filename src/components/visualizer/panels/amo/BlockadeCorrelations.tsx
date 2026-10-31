/**
 * Blockade correlations (AMO).
 *
 * Merged panel (P0-02): the router-branch g²(r) pair scatter when the
 * frame lists pair correlations, and the agent-branch ⟨σᶻᵢσᶻⱼ⟩ matrix
 * heatmap when it carries the matrix. They are different observables
 * and are never converted into one another.
 */
import { useMemo } from "react";
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import type { AmoFrame } from "../types";
import { PanelShell, TOOLTIP_STYLE } from "../PanelShell";

export interface BlockadeCorrelationsProps {
  frame: AmoFrame | null;
}

export function BlockadeCorrelations({ frame }: BlockadeCorrelationsProps) {
  const points = useMemo(() => {
    const pairs = frame?.correlations?.pairs ?? [];
    const g2 = frame?.correlations?.g2 ?? [];
    return pairs.flatMap((p, i) => (g2[i] === undefined ? [] : [{ pair: `${p[0]}-${p[1]}`, x: i, g2: g2[i] }]));
  }, [frame]);
  const zz = useMemo(() => frame?.zz_correlations ?? [], [frame]);
  const zzMax = useMemo(() => Math.max(0.01, ...zz.flat().map(Math.abs)), [zz]);

  const hasG2 = points.length > 0;
  const hasZZ = zz.length > 0;

  return (
    <PanelShell
      title={hasG2 ? "Blockade correlations g²(r)" : "Blockade correlations ⟨σᶻᵢ σᶻⱼ⟩"}
      empty={!hasG2 && !hasZZ}
      caption={
        <>
          {hasG2 ? `${points.length} pairs` : null}
          {hasG2 && hasZZ ? " · " : null}
          {hasZZ ? `${zz.length}×${zz.length} ⟨σᶻσᶻ⟩, max |·| = ${zzMax.toFixed(3)}` : null}
        </>
      }
    >
      <div className={hasG2 && hasZZ ? "grid h-full grid-cols-2 gap-2" : "h-full"}>
        {hasG2 ? (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 8, right: 16, bottom: 16, left: 32 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
              <XAxis
                type="number"
                dataKey="x"
                stroke="currentColor"
                fontSize={10}
                tickLine={false}
                label={{ value: "pair index", position: "insideBottom", offset: -2, fontSize: 10 }}
              />
              <YAxis
                type="number"
                dataKey="g2"
                stroke="currentColor"
                fontSize={10}
                tickLine={false}
                domain={[0, "auto"]}
                label={{ value: "g²", angle: -90, position: "insideLeft", fontSize: 10 }}
              />
              <Tooltip cursor={{ stroke: "currentColor", strokeOpacity: 0.2 }} contentStyle={TOOLTIP_STYLE} />
              <Scatter data={points} fill="hsl(var(--primary))" />
            </ScatterChart>
          </ResponsiveContainer>
        ) : null}
        {hasZZ ? (
          <svg
            viewBox={`0 0 ${zz.length} ${zz.length}`}
            preserveAspectRatio="xMidYMid meet"
            className="h-full w-full"
            role="img"
            aria-label="Blockade correlations"
          >
            {zz.map((row, i) =>
              row.map((v, j) => (
                <rect
                  key={`${i}-${j}`}
                  x={j}
                  y={i}
                  width={0.95}
                  height={0.95}
                  fill={v >= 0 ? "hsl(280 80% 55%)" : "hsl(190 80% 45%)"}
                  fillOpacity={Math.min(1, Math.abs(v) / zzMax)}
                />
              )),
            )}
          </svg>
        ) : null}
      </div>
    </PanelShell>
  );
}

export default BlockadeCorrelations;
