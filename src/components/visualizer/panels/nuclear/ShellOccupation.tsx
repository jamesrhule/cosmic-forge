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
import type { NuclearFrame } from "@/types/manifest";

export interface ShellOccupationProps {
  frame: NuclearFrame | null;
}

export function ShellOccupation({ frame }: ShellOccupationProps) {
  const data = useMemo(() => {
    return (frame?.shell_occupation ?? []).map((s) => ({
      shell: s.shell,
      n: Number(s.n.toFixed(3)),
      energy: s.energy_MeV,
    }));
  }, [frame]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        Shell occupation (n)
      </div>
      <div className="min-h-0 flex-1 p-2">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 16, bottom: 16, left: 32 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
              <XAxis dataKey="shell" stroke="currentColor" fontSize={10} tickLine={false} />
              <YAxis stroke="currentColor" fontSize={10} tickLine={false} />
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  borderRadius: 6,
                }}
                formatter={(v: number, _n, item) => [
                  `${v} (E ${(item.payload as { energy: number }).energy.toFixed(2)} MeV)`,
                  "n",
                ]}
              />
              <Bar dataKey="n" radius={[4, 4, 0, 0]}>
                {data.map((d) => (
                  <Cell
                    key={d.shell}
                    fill={d.energy < -4 ? "hsl(var(--primary))" : "hsl(var(--muted-foreground))"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
