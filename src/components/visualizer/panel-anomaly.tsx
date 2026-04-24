import { useMemo, useRef } from "react";
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
import { ResponsiveChart } from "@/components/charts/responsive-chart";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import { PanelContextMenu } from "@/components/visualizer/panel-context-menu";
import { useVisualizerStore } from "@/store/visualizer";
import type {
  AnomalyIntegrandSample,
  BakedVisualizationTimeline,
} from "@/types/visualizer";

export interface AnomalyIntegrandPlotProps {
  timelineA: BakedVisualizationTimeline | null;
  timelineB?: BakedVisualizationTimeline | null;
}

/**
 * Panel 4 — anomaly integrand vs k.
 *
 * Bar = `integrand[k]`, line = `running_integral[k]` (right axis),
 * reference line = `cutoff`. Snapshots are attached every ~10 frames in
 * the fixtures; we surface the most recent one ≤ current frame so the
 * chart never goes blank mid-playback.
 */
export function AnomalyIntegrandPlot({
  timelineA,
  timelineB,
}: AnomalyIntegrandPlotProps) {
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
      <PanelContextMenu
        panelId="anomaly"
        label="Anomaly integrand"
        timelineA={timelineA}
      >
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
        containerRef.current?.querySelector<SVGSVGElement>(
          "svg.recharts-surface",
        ) ?? null
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
              <ComposedChart
                width={width}
                height={height}
                data={data}
                margin={{ left: 8, right: 16, top: 4, bottom: 12 }}
              >
                <CartesianGrid
                  stroke="var(--color-border)"
                  strokeDasharray="3 3"
                />
                <XAxis
                  dataKey="k"
                  type="number"
                  scale="log"
                  domain={["auto", "auto"]}
                  tickFormatter={(v: number) =>
                    `10^${Math.round(Math.log10(v))}`
                  }
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
                  labelFormatter={(label) =>
                    `k = ${Number(label).toExponential(2)}`
                  }
                />
                <ReferenceLine
                  x={sampleA.sample.cutoff}
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
                {sampleB ? (
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
                {sampleB ? (
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
      // Fall back to the very first attached sample (so we never blank).
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
