/**
 * Slater determinants (chemistry).
 *
 * Merged panel (P0-02): the router-branch determinant-weight bar chart
 * (when the frame lists determinants) and the agent-branch orbital →
 * orbital flow chords (when the frame carries the flow matrix). Either,
 * both, or neither may be present; only provided data is drawn.
 */
import { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from "recharts";
import type { ChemistryFrame } from "../types";
import { PanelShell, TOOLTIP_STYLE, tooltipNumber } from "../PanelShell";

export interface SlaterSankeyProps {
  frame: ChemistryFrame | null;
  /** Minimum |weight| for a flow chord to be drawn. */
  threshold?: number;
}

interface WeightRow {
  label: string;
  weight: number;
  occupations: string;
}

function isWeightRow(v: unknown): v is WeightRow {
  return typeof v === "object" && v !== null && typeof (v as WeightRow).occupations === "string";
}

export function SlaterSankey({ frame, threshold = 0.05 }: SlaterSankeyProps) {
  const weights = useMemo<WeightRow[]>(
    () =>
      (frame?.slater_determinants ?? []).map((d) => ({
        label: d.label,
        weight: Number(d.weight.toFixed(4)),
        occupations: d.occupations.join(""),
      })),
    [frame],
  );
  const flow = useMemo(() => frame?.slater_flow ?? [], [frame]);
  const chords = useMemo(() => {
    const out: Array<{ i: number; j: number; w: number }> = [];
    flow.forEach((row, i) =>
      row.forEach((w, j) => {
        if (Math.abs(w) >= threshold) out.push({ i, j, w });
      }),
    );
    return out;
  }, [flow, threshold]);

  const hasWeights = weights.length > 0;
  const hasFlow = flow.length > 0;

  return (
    <PanelShell
      title={hasWeights ? "Slater determinants (weight)" : "Slater flow (orbital → orbital)"}
      empty={!hasWeights && !hasFlow}
      caption={
        <>
          {hasWeights ? `${weights.length} determinants` : null}
          {hasWeights && hasFlow ? " · " : null}
          {hasFlow ? `${chords.length} flow edges ≥ ${threshold}` : null}
        </>
      }
    >
      <div className={hasWeights && hasFlow ? "grid h-full grid-cols-2 gap-2" : "h-full"}>
        {hasWeights ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={weights} layout="vertical" margin={{ top: 8, right: 24, bottom: 8, left: 60 }}>
              <XAxis type="number" domain={[0, 1]} stroke="currentColor" fontSize={10} tickLine={false} />
              <YAxis type="category" dataKey="label" stroke="currentColor" fontSize={11} tickLine={false} width={56} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value, _name, item) => [
                  isWeightRow(item.payload)
                    ? `${tooltipNumber(value)} (${item.payload.occupations})`
                    : tooltipNumber(value),
                  "weight",
                ]}
              />
              <Bar dataKey="weight" radius={[0, 4, 4, 0]}>
                {weights.map((d, i) => (
                  <Cell key={d.label} fill={i === 0 ? "hsl(var(--primary))" : "hsl(var(--muted-foreground))"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : null}
        {hasFlow ? <FlowChords n={flow.length} chords={chords} /> : null}
      </div>
    </PanelShell>
  );
}

function FlowChords({ n, chords }: { n: number; chords: Array<{ i: number; j: number; w: number }> }) {
  const H = 100;
  const step = H / Math.max(1, n - 1);
  return (
    <svg viewBox={`-12 -6 124 ${H + 12}`} className="h-full w-full" role="img" aria-label="Slater flow Sankey">
      {Array.from({ length: n }).map((_, i) => (
        <g key={`l-${i}`} fontSize={5} fill="currentColor">
          <text x={-3} y={i * step + 2} textAnchor="end">
            {i}
          </text>
          <text x={103} y={i * step + 2}>
            {i}
          </text>
        </g>
      ))}
      {chords.map((f, idx) => (
        <line
          key={idx}
          x1={0}
          y1={f.i * step}
          x2={100}
          y2={f.j * step}
          stroke="hsl(var(--primary))"
          strokeOpacity={Math.min(1, Math.abs(f.w) * 5)}
          strokeWidth={0.4 + Math.abs(f.w) * 2}
        />
      ))}
    </svg>
  );
}

export default SlaterSankey;
