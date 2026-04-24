import { useMemo, useRef } from "react";
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
import { ResponsiveChart } from "@/components/charts/responsive-chart";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import { PanelContextMenu } from "@/components/visualizer/panel-context-menu";
import { useVisualizerStore } from "@/store/visualizer";
import type { BakedVisualizationTimeline } from "@/types/visualizer";

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
 * Shows the full timeline of `B_plus`, `B_minus`, and `xi_dot_H` versus τ
 * with phase-band shading. Doubles as the global scrubber: clicking the
 * chart seeks the transport to the matching frame index.
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
                if (typeof f === "number") seek(f);
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
              {timelineB ? (
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
