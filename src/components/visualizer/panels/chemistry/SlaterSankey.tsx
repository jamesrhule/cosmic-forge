import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  Cell,
} from "recharts";
import type { ChemistryFrame } from "@/types/manifest";

export interface SlaterSankeyProps {
  frame: ChemistryFrame | null;
}

/**
 * Slater-determinant weight breakdown. Sankey-style flow rendering is
 * deferred to the optional `d3-sankey` dynamic-import path; the
 * baseline view is a horizontal weighted-bar chart so the panel
 * works without the optional dep.
 */
export function SlaterSankey({ frame }: SlaterSankeyProps) {
  const data = useMemo(() => {
    return (frame?.slater_determinants ?? []).map((d) => ({
      label: d.label,
      weight: Number(d.weight.toFixed(4)),
      occupations: d.occupations.join(""),
    }));
  }, [frame]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        Slater determinants (weight)
      </div>
      <div className="min-h-0 flex-1 p-2">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 8, right: 24, bottom: 8, left: 60 }}
            >
              <XAxis
                type="number"
                domain={[0, 1]}
                stroke="currentColor"
                fontSize={10}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="label"
                stroke="currentColor"
                fontSize={11}
                tickLine={false}
                width={56}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  borderRadius: 6,
                }}
                formatter={(v: number, _n, item) => [
                  `${v} (${(item.payload as { occupations: string }).occupations})`,
                  "weight",
                ]}
              />
              <Bar dataKey="weight" radius={[0, 4, 4, 0]}>
                {data.map((d, i) => (
                  <Cell
                    key={d.label}
                    fill={i === 0 ? "hsl(var(--primary))" : "hsl(var(--muted-foreground))"}
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
