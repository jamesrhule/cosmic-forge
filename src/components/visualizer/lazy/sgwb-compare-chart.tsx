import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface SgwbCompareChartProps {
  width: number;
  height: number;
  data: Array<Record<string, number>>;
  spectra: { id: string; label: string }[];
  bands: Array<{ low: number; high: number; label: string }>;
  colors: string[];
}

export default function SgwbCompareChart({
  width,
  height,
  data,
  spectra,
  bands,
  colors,
}: SgwbCompareChartProps) {
  return (
    <LineChart
      width={width}
      height={height}
      data={data}
      margin={{ left: 8, right: 16, top: 8, bottom: 12 }}
    >
      <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
      <XAxis
        dataKey="f"
        scale="log"
        domain={["auto", "auto"]}
        type="number"
        tickFormatter={(v: number) => `10^${Math.round(Math.log10(v))}`}
        tick={{ fontSize: 11, fontFamily: "var(--font-mono)" }}
        label={{
          value: "f [Hz]",
          position: "insideBottom",
          offset: -4,
          fontSize: 11,
        }}
      />
      <YAxis
        scale="log"
        domain={[1e-22, 1e-8]}
        type="number"
        tickFormatter={(v: number) => `10^${Math.round(Math.log10(v))}`}
        tick={{ fontSize: 11, fontFamily: "var(--font-mono)" }}
        label={{
          value: "ΩGW",
          angle: -90,
          position: "insideLeft",
          fontSize: 11,
        }}
      />
      {bands.map((b) => (
        <ReferenceArea
          key={b.label}
          y1={b.low}
          y2={b.high}
          fill="var(--color-accent-indigo)"
          fillOpacity={0.08}
          ifOverflow="extendDomain"
        />
      ))}
      <Tooltip
        contentStyle={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          background: "var(--color-popover)",
          border: "1px solid var(--color-border)",
        }}
        formatter={(value) => Number(value).toExponential(2)}
        labelFormatter={(label) => `f = ${Number(label).toExponential(2)} Hz`}
      />
      <Legend wrapperStyle={{ fontSize: 11 }} />
      {spectra.map((s, i) => (
        <Line
          key={s.id}
          type="monotone"
          dataKey={s.id}
          name={s.label}
          dot={false}
          stroke={colors[i % colors.length]}
          strokeWidth={1.6}
          isAnimationActive={false}
        />
      ))}
    </LineChart>
  );
}
