/**
 * Chiral condensate ⟨ψ̄ψ⟩(τ) across the whole timeline (HEP).
 *
 * Merged panel (P0-02): router-branch recharts line chart plus the
 * agent-branch frame count / range caption and current-τ marker.
 */
import { useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, ReferenceLine } from "recharts";
import type { HepFrame } from "../types";
import { PanelShell, TOOLTIP_STYLE } from "../PanelShell";

export interface ChiralCondensateTraceProps {
  frames: HepFrame[];
  currentTau?: number;
}

export function ChiralCondensateTrace({ frames, currentTau }: ChiralCondensateTraceProps) {
  const data = useMemo(
    () => frames.map((f) => ({ tau: Number(f.tau.toFixed(2)), condensate: f.chiral_condensate })),
    [frames],
  );
  const vals = data.map((d) => d.condensate);

  return (
    <PanelShell
      title="Chiral condensate ⟨ψ̄ψ⟩(τ)"
      empty={data.length === 0}
      caption={
        vals.length > 0 ? (
          <>
            {vals.length} frames · range [{Math.min(...vals).toFixed(3)}, {Math.max(...vals).toFixed(3)}]
          </>
        ) : null
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 16, right: 16, bottom: 16, left: 32 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
          <XAxis
            dataKey="tau"
            type="number"
            domain={["dataMin", "dataMax"]}
            stroke="currentColor"
            fontSize={11}
            tickLine={false}
            label={{ value: "τ", position: "insideBottom", offset: -2, fontSize: 10 }}
          />
          <YAxis
            stroke="currentColor"
            fontSize={11}
            tickLine={false}
            label={{ value: "⟨ψ̄ψ⟩", angle: -90, position: "insideLeft", fontSize: 10 }}
          />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          {currentTau !== undefined ? (
            <ReferenceLine x={Number(currentTau.toFixed(2))} stroke="currentColor" strokeDasharray="4 2" strokeOpacity={0.5} />
          ) : null}
          <Line type="monotone" dataKey="condensate" stroke="hsl(var(--primary))" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </PanelShell>
  );
}

export default ChiralCondensateTrace;
