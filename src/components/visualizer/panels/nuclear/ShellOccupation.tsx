/**
 * Shell occupation (nuclear).
 *
 * Merged panel (P0-02): router-branch labelled recharts bars plus the
 * agent-branch level count / max ⟨n⟩ caption. Bars are shaded by shell
 * energy only when every shell carries one; otherwise one colour.
 */
import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { NuclearFrame } from "../types";
import { PanelShell, TOOLTIP_STYLE, hslToHex, tooltipNumber } from "../PanelShell";

export interface ShellOccupationProps {
  frame: NuclearFrame | null;
}

interface ShellRow {
  shell: string;
  n: number;
  energy: number | null;
}

function isShellRow(v: unknown): v is ShellRow {
  return typeof v === "object" && v !== null && typeof (v as ShellRow).shell === "string";
}

export function ShellOccupation({ frame }: ShellOccupationProps) {
  const data = useMemo<ShellRow[]>(
    () =>
      (frame?.shell_occupation ?? []).map((s) => ({
        shell: s.shell,
        n: Number(s.n.toFixed(3)),
        energy: s.energy_MeV,
      })),
    [frame],
  );

  const colours = useMemo(() => {
    const es = data.map((d) => d.energy);
    if (es.length === 0 || es.some((e) => e === null)) return null;
    const known = es as number[];
    const min = Math.min(...known);
    const span = Math.max(1e-9, Math.max(...known) - min);
    // deeper-bound (lower energy) = blue, shallower = red.
    return known.map((e) => hslToHex((1 - (e - min) / span) * 0.66, 0.6, 0.5));
  }, [data]);

  const maxN = data.reduce((m, d) => Math.max(m, d.n), 0);

  return (
    <PanelShell
      title="Shell occupation (n)"
      empty={data.length === 0}
      caption={
        <>
          {data.length} levels · max ⟨n⟩ = {maxN.toFixed(2)}
          {colours ? " · colour = shell energy" : ""}
        </>
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 16, left: 32 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
          <XAxis dataKey="shell" stroke="currentColor" fontSize={10} tickLine={false} />
          <YAxis stroke="currentColor" fontSize={10} tickLine={false} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, _name, item) => [
              isShellRow(item.payload) && item.payload.energy !== null
                ? `${tooltipNumber(value)} (E ${item.payload.energy.toFixed(2)} MeV)`
                : tooltipNumber(value),
              "n",
            ]}
          />
          <Bar dataKey="n" radius={[4, 4, 0, 0]}>
            {data.map((d, i) => (
              <Cell key={d.shell} fill={colours?.[i] ?? "hsl(var(--primary))"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </PanelShell>
  );
}

export default ShellOccupation;
