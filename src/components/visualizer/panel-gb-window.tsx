import { Suspense, lazy, useMemo, useRef } from "react";
import { ResponsiveChart } from "@/components/charts/responsive-chart";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import { PanelContextMenu } from "@/components/visualizer/panel-context-menu";
import { PanelSkeleton } from "@/components/visualizer/panel-skeleton";
import { useVisualizerStore } from "@/store/visualizer";
import type { BakedVisualizationTimeline } from "@/types/visualizer";

const GBWindowChart = lazy(() => import("./lazy/gb-window-chart"));

export interface GBWindowTimelineProps {
  timelineA: BakedVisualizationTimeline | null;
  timelineB?: BakedVisualizationTimeline | null;
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

/**
 * Panel 2 — chiral GB window.
 *
 * The Recharts surface is split into a lazy chunk so the visualizer
 * entry doesn't pull recharts on first paint. Data preparation +
 * resize observation stay here; only the chart JSX is in the chunk.
 */
export function GBWindowTimeline({ timelineA, timelineB }: GBWindowTimelineProps) {
  const seek = useVisualizerStore((s) => s.seek);
  const currentFrameIndex = useVisualizerStore((s) => s.currentFrameIndex);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const data = useMemo<SeriesPoint[]>(() => {
    if (!timelineA) return [];
    const len = timelineA.frames.length;
    const rows: SeriesPoint[] = new Array(len);
    for (let i = 0; i < len; i++) {
      const a = timelineA.frames[i];
      const b = timelineB?.frames[i];
      rows[i] = {
        tau: a.tau,
        frame: i,
        bPlusA: a.B_plus,
        bMinusA: a.B_minus,
        xiHA: a.xi_dot_H,
        bPlusB: b?.B_plus,
        bMinusB: b?.B_minus,
        xiHB: b?.xi_dot_H,
      };
    }
    return rows;
  }, [timelineA, timelineB]);

  if (!timelineA) {
    return (
      <PanelContextMenu panelId="gb-window" label="Gauss-Bonnet window" timelineA={null}>
        <div className="h-full w-full">
          <EmptyPanel
            title="Gauss-Bonnet window"
            reason="Pick a run to see the chiral GB transport timeline."
          />
        </div>
      </PanelContextMenu>
    );
  }

  const phaseBands = phaseBandsFor(timelineA);
  const currentTau = timelineA.frames[currentFrameIndex]?.tau ?? timelineA.frames[0].tau;

  return (
    <PanelContextMenu
      panelId="gb-window"
      label="Gauss-Bonnet window"
      timelineA={timelineA}
      timelineB={timelineB}
      getExportTarget={() =>
        containerRef.current?.querySelector<SVGSVGElement>("svg.recharts-surface") ?? null
      }
    >
      <div ref={containerRef} className="h-full w-full" data-testid="visualizer-gb-window">
        <ResponsiveChart height="100%" label="gb">
          {({ width, height }) => (
            <Suspense fallback={<PanelSkeleton label="Loading chart…" />}>
              <GBWindowChart
                width={width}
                height={height}
                data={data}
                phaseBands={phaseBands}
                currentTau={currentTau}
                hasPartner={Boolean(timelineB)}
                onSeek={seek}
              />
            </Suspense>
          )}
        </ResponsiveChart>
      </div>
    </PanelContextMenu>
  );
}

interface PhaseBand {
  label: string;
  tauStart: number;
  tauEnd: number;
  fill: string;
}

const PHASE_FILL: Record<string, string> = {
  inflation: "var(--color-chart-2)",
  gb_window: "var(--color-accent-indigo)",
  reheating: "var(--color-chart-4)",
  radiation: "var(--color-chart-3)",
  sphaleron: "var(--color-chart-5)",
};

function phaseBandsFor(timeline: BakedVisualizationTimeline): PhaseBand[] {
  const frames = timeline.frames;
  const out: PhaseBand[] = [];
  for (const [name, [lo, hi]] of Object.entries(timeline.meta.phaseBoundaries)) {
    const start = frames[Math.min(lo, frames.length - 1)]?.tau;
    const end = frames[Math.min(hi, frames.length - 1)]?.tau;
    if (start === undefined || end === undefined) continue;
    out.push({
      label: name,
      tauStart: start,
      tauEnd: end,
      fill: PHASE_FILL[name] ?? "var(--color-muted)",
    });
  }
  return out;
}
