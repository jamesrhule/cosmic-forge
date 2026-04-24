import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import type { SgwbSnapshot } from "@/types/visualizer";

export interface SgwbChartProps {
  width: number;
  height: number;
  data: Record<string, number>[];
  snapADash?: string;
  snapBDash?: string;
  hasPartner: boolean;
}

export default function SgwbChart({
  width,
  height,
  data,
  snapADash,
  snapBDash,
  hasPartner,
}: SgwbChartProps) {
  return (
    <LineChart
      width={width}
      height={height}
      data={data}
      margin={{ left: 8, right: 16, top: 4, bottom: 12 }}
    >
      <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
      <XAxis
        dataKey="f"
        type="number"
        scale="log"
        domain={["auto", "auto"]}
        tickFormatter={(v: number) => `10^${Math.round(Math.log10(v))}`}
        tick={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          fill: "var(--color-muted-foreground)",
        }}
        label={{
          value: "f [Hz]",
          position: "insideBottom",
          offset: -4,
          fontSize: 11,
          fill: "var(--color-muted-foreground)",
        }}
      />
      <YAxis
        type="number"
        scale="log"
        domain={["auto", "auto"]}
        tickFormatter={(v: number) => `10^${Math.round(Math.log10(v))}`}
        tick={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          fill: "var(--color-muted-foreground)",
        }}
        label={{
          value: "ΩGW",
          angle: -90,
          position: "insideLeft",
          fontSize: 11,
          fill: "var(--color-muted-foreground)",
        }}
      />
      <Tooltip
        contentStyle={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          background: "var(--color-popover)",
          border: "1px solid var(--color-border)",
          color: "var(--color-popover-foreground)",
        }}
        formatter={(v) => Number(v).toExponential(2)}
        labelFormatter={(label) => `f = ${Number(label).toExponential(2)} Hz`}
      />
      <Line
        type="monotone"
        dataKey="omegaA"
        name="ΩGW (A)"
        stroke="var(--color-accent-indigo)"
        strokeDasharray={snapADash}
        strokeWidth={1.6}
        dot={false}
        isAnimationActive={false}
      />
      {hasPartner ? (
        <Line
          type="monotone"
          dataKey="omegaB"
          name="ΩGW (B)"
          stroke="var(--color-chart-4)"
          strokeDasharray={snapBDash}
          strokeWidth={1.6}
          dot={false}
          isAnimationActive={false}
        />
      ) : null}
    </LineChart>
  );
}

export function chiralityDash(snap: SgwbSnapshot): string | undefined {
  if (snap.chirality.length === 0) return undefined;
  let acc = 0;
  for (const c of snap.chirality) acc += c;
  const mean = acc / snap.chirality.length;
  if (Math.abs(mean) < 0.05) return undefined;
  return mean > 0 ? "6 2" : "2 4";
}
