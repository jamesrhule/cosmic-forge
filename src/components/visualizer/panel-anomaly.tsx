import { Suspense, lazy, useMemo, useRef } from "react";
import { ResponsiveChart } from "@/components/charts/responsive-chart";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import { PanelContextMenu } from "@/components/visualizer/panel-context-menu";
import { PanelSkeleton } from "@/components/visualizer/panel-skeleton";
import { useVisualizerStore } from "@/store/visualizer";
import type { AnomalyIntegrandSample, BakedVisualizationTimeline } from "@/types/visualizer";

const AnomalyChart = lazy(() => import("./lazy/anomaly-chart"));

export interface AnomalyIntegrandPlotProps {
  timelineA: BakedVisualizationTimeline | null;
  timelineB?: BakedVisualizationTimeline | null;
}

/**
 * Panel 4 — anomaly integrand vs k.
 *
 * Lazy-loads the Recharts ComposedChart. Snapshot resolution stays here.
 */
export function AnomalyIntegrandPlot({ timelineA, timelineB }: AnomalyIntegrandPlotProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const frameIdx = useVisualizerStore((s) => s.currentFrameIndex);

  const sampleA = useResolvedAnomaly(timelineA, frameIdx);
  const sampleB = useResolvedAnomaly(timelineB ?? null, frameIdx);

  const data = useMemo(() => {
    if (!sampleA) return [];
    const rows: Record<string, number>[] = [];
    for (let i = 0; i < sampleA.sample.k.length; i++) {
      const row: Record<string, number> = {
        k: sampleA.sample.k[i],
        integrandA: sampleA.sample.integrand[i] ?? 0,
        runningA: sampleA.sample.running_integral[i] ?? 0,
      };
      if (sampleB && sampleB.sample.k.length === sampleA.sample.k.length) {
        row.integrandB = sampleB.sample.integrand[i] ?? 0;
        row.runningB = sampleB.sample.running_integral[i] ?? 0;
      }
      rows.push(row);
    }
    return rows;
  }, [sampleA, sampleB]);

  if (!timelineA || !sampleA) {
    return (
      <PanelContextMenu panelId="anomaly" label="Anomaly integrand" timelineA={timelineA}>
        <div className="h-full w-full">
          <EmptyPanel
            title="Anomaly integrand"
            reason={
              timelineA
                ? "No anomaly integrand attached to frames yet."
                : "Pick a run to see the anomaly integrand."
            }
          />
        </div>
      </PanelContextMenu>
    );
  }

  return (
    <PanelContextMenu
      panelId="anomaly"
      label="Anomaly integrand"
      timelineA={timelineA}
      timelineB={timelineB}
      getExportTarget={() =>
        containerRef.current?.querySelector<SVGSVGElement>("svg.recharts-surface") ?? null
      }
    >
      <div
        ref={containerRef}
        className="flex h-full w-full flex-col"
        data-testid="visualizer-anomaly"
      >
        <div className="flex items-center justify-between px-2 pt-1 text-[10px] font-mono text-muted-foreground">
          <span>integrand · running ∫</span>
          <span>frame {sampleA.frame}</span>
        </div>
        <div className="min-h-0 flex-1">
          <ResponsiveChart height="100%" label="anomaly">
            {({ width, height }) => (
              <Suspense fallback={<PanelSkeleton label="Loading chart…" />}>
                <AnomalyChart
                  width={width}
                  height={height}
                  data={data}
                  cutoff={sampleA.sample.cutoff}
                  hasPartner={Boolean(sampleB)}
                />
              </Suspense>
            )}
          </ResponsiveChart>
        </div>
      </div>
    </PanelContextMenu>
  );
}

function useResolvedAnomaly(
  timeline: BakedVisualizationTimeline | null,
  frameIdx: number,
): { frame: number; sample: AnomalyIntegrandSample } | null {
  return useMemo(() => {
    if (!timeline) return null;
    let last: { frame: number; sample: AnomalyIntegrandSample } | null = null;
    for (let i = 0; i <= Math.min(frameIdx, timeline.frames.length - 1); i++) {
      const s = timeline.frames[i].anomaly_integrand;
      if (s) last = { frame: i, sample: s };
    }
    if (!last) {
      for (let i = 0; i < timeline.frames.length; i++) {
        const s = timeline.frames[i].anomaly_integrand;
        if (s) {
          last = { frame: i, sample: s };
          break;
        }
      }
    }
    return last;
  }, [timeline, frameIdx]);
}
