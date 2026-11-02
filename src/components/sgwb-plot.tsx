import { Suspense, lazy } from "react";
import type { SgwbSpectrum } from "@/types/domain";
import { ResponsiveChart } from "@/components/charts/responsive-chart";
import { PanelSkeleton } from "@/components/visualizer/panel-skeleton";

const SgwbCompareChart = lazy(() => import("@/components/visualizer/lazy/sgwb-compare-chart"));

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
  // R6: M6's frequencies are a placeholder conversion while the API says so.
  const placeholder = spectra.find((s) => s.data.f_Hz_is_placeholder === true);
  const merged: Array<Record<string, number>> = [];
  if (spectra.length > 0) {
    const length = spectra[0].data.f_Hz.length;
    for (let i = 0; i < length; i++) {
      const row: Record<string, number> = { f: spectra[0].data.f_Hz[i] };
      for (const s of spectra) {
        const v = s.data.Omega_gw[i];
        row[s.id] = Math.max(v, 1e-25);
      }
      merged.push(row);
    }
  }

  const chart = (
    <ResponsiveChart height={height} label="sgwb">
      {({ width, height: h }) => (
        <Suspense fallback={<PanelSkeleton label="Loading chart…" />}>
          <SgwbCompareChart
            width={width}
            height={h}
            data={merged}
            spectra={spectra.map((s) => ({ id: s.id, label: s.label }))}
            bands={bands}
            colors={COLORS}
            placeholderFrequencies={placeholder !== undefined}
          />
        </Suspense>
      )}
    </ResponsiveChart>
  );
  if (!placeholder) return chart;
  return (
    <div>
      {chart}
      <p
        data-testid="sgwb-placeholder-note"
        className="mt-1 text-[11px] leading-snug text-muted-foreground"
      >
        Frequency axis: placeholder frequencies, not physical Hz.
        {placeholder.data.note ? ` ${placeholder.data.note}` : ""}
      </p>
    </div>
  );
}
