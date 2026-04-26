import { useMemo } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import type { AmoFrame } from "@/types/manifest";

export interface BlockadeCorrelationsProps {
  frame: AmoFrame | null;
}

export function BlockadeCorrelations({ frame }: BlockadeCorrelationsProps) {
  const points = useMemo(() => {
    const pairs = frame?.correlations?.pairs ?? [];
    const g2 = frame?.correlations?.g2 ?? [];
    return pairs.map((p, i) => ({
      pair: `${p[0]}-${p[1]}`,
      x: i,
      g2: g2[i] ?? 0,
    }));
  }, [frame]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        Blockade correlations g²(r)
      </div>
      <div className="min-h-0 flex-1 p-2">
        {points.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
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
                domain={[0, 1.2]}
                label={{ value: "g²", angle: -90, position: "insideLeft", fontSize: 10 }}
              />
              <Tooltip
                cursor={{ stroke: "currentColor", strokeOpacity: 0.2 }}
                contentStyle={{
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  borderRadius: 6,
                }}
              />
              <Scatter data={points} fill="hsl(var(--primary))" />
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
