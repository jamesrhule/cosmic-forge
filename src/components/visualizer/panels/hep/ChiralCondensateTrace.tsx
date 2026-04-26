import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import type { DomainTimelineResponse, HepFrame } from "@/types/manifest";

export interface ChiralCondensateTraceProps {
  timeline: DomainTimelineResponse;
}

export function ChiralCondensateTrace({ timeline }: ChiralCondensateTraceProps) {
  const data = useMemo(() => {
    const frames = timeline.frames as HepFrame[];
    return frames.map((f) => ({
      tau: Number(f.tau.toFixed(2)),
      condensate: f.chiral_condensate,
    }));
  }, [timeline]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        Chiral condensate ⟨ψ̄ψ⟩(τ)
      </div>
      <div className="min-h-0 flex-1 p-2">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 16, right: 16, bottom: 16, left: 32 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
              <XAxis
                dataKey="tau"
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
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  borderRadius: 6,
                }}
              />
              <Line
                type="monotone"
                dataKey="condensate"
                stroke="hsl(var(--primary))"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
