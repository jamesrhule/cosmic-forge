import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface AnomalyChartProps {
  width: number;
  height: number;
  data: Record<string, number>[];
  cutoff: number;
  hasPartner: boolean;
}

export default function AnomalyChart({
  width,
  height,
  data,
  cutoff,
  hasPartner,
}: AnomalyChartProps) {
  return (
    <ComposedChart
      width={width}
      height={height}
      data={data}
      margin={{ left: 8, right: 16, top: 4, bottom: 12 }}
    >
      <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
      <XAxis
        dataKey="k"
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
          value: "k",
          position: "insideBottom",
          offset: -4,
          fontSize: 11,
          fill: "var(--color-muted-foreground)",
        }}
      />
      <YAxis
        yAxisId="left"
        tick={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          fill: "var(--color-muted-foreground)",
        }}
      />
      <YAxis
        yAxisId="right"
        orientation="right"
        tick={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
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
        labelFormatter={(label) => `k = ${Number(label).toExponential(2)}`}
      />
      <ReferenceLine
        x={cutoff}
        yAxisId="left"
        stroke="var(--color-destructive)"
        strokeDasharray="3 2"
        ifOverflow="extendDomain"
        label={{
          value: "cutoff",
          position: "top",
          fontSize: 10,
          fill: "var(--color-destructive)",
        }}
      />
      <Bar
        yAxisId="left"
        dataKey="integrandA"
        name="integrand (A)"
        fill="var(--color-accent-indigo)"
        fillOpacity={0.7}
        isAnimationActive={false}
      />
      {hasPartner ? (
        <Bar
          yAxisId="left"
          dataKey="integrandB"
          name="integrand (B)"
          fill="var(--color-chart-4)"
          fillOpacity={0.5}
          isAnimationActive={false}
        />
      ) : null}
      <Line
        yAxisId="right"
        type="monotone"
        dataKey="runningA"
        name="∫ (A)"
        stroke="var(--color-chart-3)"
        strokeWidth={1.6}
        dot={false}
        isAnimationActive={false}
      />
      {hasPartner ? (
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="runningB"
          name="∫ (B)"
          stroke="var(--color-chart-5)"
          strokeWidth={1.6}
          strokeDasharray="3 3"
          dot={false}
          isAnimationActive={false}
        />
      ) : null}
    </ComposedChart>
  );
}
