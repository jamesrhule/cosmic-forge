import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface PhaseBand {
  label: string;
  tauStart: number;
  tauEnd: number;
  fill: string;
}

interface SeriesPoint {
  tau: number;
  frame: number;
  bPlusA?: number;
  bMinusA?: number;
  xiHA?: number;
  bPlusB?: number;
  bMinusB?: number;
  xiHB?: number;
}

export interface GBWindowChartProps {
  width: number;
  height: number;
  data: SeriesPoint[];
  phaseBands: PhaseBand[];
  currentTau: number;
  hasPartner: boolean;
  onSeek: (frame: number) => void;
}

export default function GBWindowChart({
  width,
  height,
  data,
  phaseBands,
  currentTau,
  hasPartner,
  onSeek,
}: GBWindowChartProps) {
  return (
    <LineChart
      width={width}
      height={height}
      data={data}
      margin={{ left: 8, right: 16, top: 8, bottom: 12 }}
      onClick={(state) => {
        const payload = (
          state as unknown as {
            activePayload?: Array<{ payload?: { frame?: number } }>;
          }
        )?.activePayload?.[0]?.payload;
        const f = payload?.frame;
        if (typeof f === "number") onSeek(f);
      }}
    >
      <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
      <XAxis
        dataKey="tau"
        type="number"
        domain={["dataMin", "dataMax"]}
        tick={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          fill: "var(--color-muted-foreground)",
        }}
        label={{
          value: "τ (e-folds)",
          position: "insideBottom",
          offset: -4,
          fontSize: 11,
          fill: "var(--color-muted-foreground)",
        }}
      />
      <YAxis
        tick={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          fill: "var(--color-muted-foreground)",
        }}
      />
      {phaseBands.map((band) => (
        <ReferenceArea
          key={band.label}
          x1={band.tauStart}
          x2={band.tauEnd}
          fill={band.fill}
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
          color: "var(--color-popover-foreground)",
        }}
        formatter={(v) => Number(v).toExponential(2)}
        labelFormatter={(label) => `τ = ${Number(label).toFixed(2)}`}
      />
      <ReferenceLine
        x={currentTau}
        stroke="var(--color-accent-indigo)"
        strokeWidth={1.5}
        ifOverflow="extendDomain"
      />
      <Line
        type="monotone"
        dataKey="bPlusA"
        name="B₊ (A)"
        stroke="var(--color-accent-indigo)"
        strokeWidth={1.6}
        dot={false}
        isAnimationActive={false}
      />
      <Line
        type="monotone"
        dataKey="bMinusA"
        name="B₋ (A)"
        stroke="var(--color-chart-4)"
        strokeWidth={1.6}
        dot={false}
        isAnimationActive={false}
      />
      <Line
        type="monotone"
        dataKey="xiHA"
        name="ξ·H (A)"
        stroke="var(--color-chart-3)"
        strokeWidth={1.2}
        strokeDasharray="4 2"
        dot={false}
        isAnimationActive={false}
      />
      {hasPartner ? (
        <>
          <Line
            type="monotone"
            dataKey="bPlusB"
            name="B₊ (B)"
            stroke="var(--color-accent-indigo)"
            strokeOpacity={0.5}
            strokeWidth={1.4}
            strokeDasharray="2 2"
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="bMinusB"
            name="B₋ (B)"
            stroke="var(--color-chart-4)"
            strokeOpacity={0.5}
            strokeWidth={1.4}
            strokeDasharray="2 2"
            dot={false}
            isAnimationActive={false}
          />
        </>
      ) : null}
    </LineChart>
  );
}
