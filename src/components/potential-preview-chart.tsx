import {
  CartesianGrid,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PotentialKind } from "@/types/domain";
import { samplePotential } from "@/lib/potentialEvaluator";
import { ResponsiveChart } from "@/components/charts/responsive-chart";

export interface PotentialPreviewChartProps {
  kind: PotentialKind;
  params: Record<string, number>;
  height?: number;
}

export function PotentialPreviewChart({
  kind,
  params,
  height = 200,
}: PotentialPreviewChartProps) {
  const samples = samplePotential(kind, params);

  if (!samples) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-dashed bg-muted/30 px-4 py-8 text-center text-xs text-muted-foreground"
        style={{ height }}
      >
        Preview unavailable for custom potential — backend will compute V(ψ).
      </div>
    );
  }

  return (
    <ResponsiveChart height={height}>
      {({ width, height: h }) => (
        <LineChart
          width={width}
          height={h}
          data={samples}
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
      )}
    </ResponsiveChart>
  );
}
