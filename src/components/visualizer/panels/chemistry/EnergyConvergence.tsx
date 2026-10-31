/**
 * Energy convergence per SCF / VQE iteration (chemistry).
 *
 * Merged panel (P0-02): router-branch recharts line chart plus the
 * agent-branch iteration count / ΔE caption.
 */
import { useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import type { ChemistryFrame } from "../types";
import { PanelShell, TOOLTIP_STYLE } from "../PanelShell";

export interface EnergyConvergenceProps {
  frame: ChemistryFrame | null;
}

export function EnergyConvergence({ frame }: EnergyConvergenceProps) {
  const series = useMemo(() => frame?.energy_convergence ?? [], [frame]);
  const data = useMemo(() => series.map((e, i) => ({ iter: i, energy: e })), [series]);
  const delta = series.length > 1 ? series[series.length - 1] - series[0] : null;

  return (
    <PanelShell
      title="SCF energy convergence"
      empty={data.length === 0}
      caption={
        <>
          {series.length} iteration{series.length === 1 ? "" : "s"}
          {delta !== null ? ` · ΔE_final = ${delta.toExponential(2)} Ha` : ""}
        </>
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 16, right: 16, bottom: 16, left: 32 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
          <XAxis
            dataKey="iter"
            stroke="currentColor"
            fontSize={11}
            tickLine={false}
            label={{ value: "iteration", position: "insideBottom", offset: -2, fontSize: 10 }}
          />
          <YAxis
            stroke="currentColor"
            fontSize={11}
            tickLine={false}
            domain={["auto", "auto"]}
            label={{ value: "E (Hartree)", angle: -90, position: "insideLeft", fontSize: 10 }}
          />
          <Tooltip cursor={{ stroke: "currentColor", strokeOpacity: 0.2 }} contentStyle={TOOLTIP_STYLE} />
          <Line type="monotone" dataKey="energy" stroke="hsl(var(--primary))" dot={data.length === 1} />
        </LineChart>
      </ResponsiveContainer>
    </PanelShell>
  );
}

export default EnergyConvergence;
