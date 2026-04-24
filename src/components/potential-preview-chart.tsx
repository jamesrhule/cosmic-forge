import { Suspense, lazy } from "react";
import type { PotentialKind } from "@/types/domain";
import { samplePotential } from "@/lib/potentialEvaluator";
import { ResponsiveChart } from "@/components/charts/responsive-chart";
import { PanelSkeleton } from "@/components/visualizer/panel-skeleton";

const PotentialPreviewChartInner = lazy(
  () => import("@/components/visualizer/lazy/potential-preview-chart-inner"),
);

export interface PotentialPreviewChartProps {
  kind: PotentialKind;
  params: Record<string, number>;
  height?: number;
}

export function PotentialPreviewChart({ kind, params, height = 200 }: PotentialPreviewChartProps) {
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
    <ResponsiveChart height={height} label="vψ">
      {({ width, height: h }) => (
        <Suspense fallback={<PanelSkeleton label="Loading chart…" />}>
          <PotentialPreviewChartInner width={width} height={h} data={samples} />
        </Suspense>
      )}
    </ResponsiveChart>
  );
}
