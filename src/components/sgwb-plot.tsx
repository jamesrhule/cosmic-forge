import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
  ReferenceArea,
} from "recharts";
import type { SgwbSpectrum } from "@/types/domain";

export interface SGWBPlotProps {
  spectra: { id: string; label: string; data: SgwbSpectrum }[];
  bands?: Array<{ low: number; high: number; label: string }>;
  height?: number;
}

const COLORS = [
  "var(--color-accent-indigo)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
];

export function SGWBPlot({ spectra, bands = [], height = 280 }: SGWBPlotProps) {
  // merge into a single series array indexed by frequency
  const merged: Array<Record<string, number>> = [];
  if (spectra.length > 0) {
    const length = spectra[0].data.f_Hz.length;
    for (let i = 0; i < length; i++) {
      const row: Record<string, number> = { f: spectra[0].data.f_Hz[i] };
      for (const s of spectra) {
        const v = s.data.Omega_gw[i];
        // log-clamp to keep log scale happy
        row[s.id] = Math.max(v, 1e-25);
      }
      merged.push(row);
    }
  }

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <LineChart data={merged} margin={{ left: 8, right: 16, top: 8, bottom: 12 }}>
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
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={1.6}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
