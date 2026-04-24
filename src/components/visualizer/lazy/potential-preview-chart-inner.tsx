import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";

export interface PotentialPreviewChartInnerProps {
  width: number;
  height: number;
  data: { psi: number; V: number }[];
}

export default function PotentialPreviewChartInner({
  width,
  height,
  data,
}: PotentialPreviewChartInnerProps) {
  return (
    <LineChart
      width={width}
      height={height}
      data={data}
      margin={{ left: 8, right: 12, top: 8, bottom: 12 }}
    >
      <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
      <XAxis
        dataKey="psi"
        type="number"
        domain={["dataMin", "dataMax"]}
        tick={{ fontSize: 10, fontFamily: "var(--font-mono)" }}
        label={{
          value: "ψ [Mₚ]",
          position: "insideBottom",
          offset: -4,
          fontSize: 10,
        }}
      />
      <YAxis
        tick={{ fontSize: 10, fontFamily: "var(--font-mono)" }}
        tickFormatter={(v: number) => Number(v).toExponential(1)}
      />
      <Tooltip
        contentStyle={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          background: "var(--color-popover)",
          border: "1px solid var(--color-border)",
        }}
        formatter={(value) => Number(value).toExponential(2)}
        labelFormatter={(label) => `ψ = ${Number(label).toFixed(3)}`}
      />
      <Line
        type="monotone"
        dataKey="V"
        stroke="var(--color-accent-indigo)"
        strokeWidth={1.6}
        dot={false}
        isAnimationActive={false}
      />
    </LineChart>
  );
}
