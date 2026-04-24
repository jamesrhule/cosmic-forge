import { useMemo, useRef } from "react";
import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { ResponsiveChart } from "@/components/charts/responsive-chart";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import { PanelContextMenu } from "@/components/visualizer/panel-context-menu";
import { useVisualizerStore } from "@/store/visualizer";
import type { BakedVisualizationTimeline, SgwbSnapshot } from "@/types/visualizer";

export interface SGWBSnapshotPlotProps {
  timelineA: BakedVisualizationTimeline | null;
  timelineB?: BakedVisualizationTimeline | null;
}

interface ResolvedSnapshot {
  snapshot: SgwbSnapshot;
  frame: number;
  label: string;
}

/**
 * Panel 3 — chiral SGWB spectrum at the active snapshot.
 *
 * Snapshots are sparse (~3 per timeline). We resolve "the most recent
 * snapshot at or before the current frame" and label it heuristically
 * (source / post-reheat / today) by ordinal position.
 *
 * Chirality is encoded in stroke-dash pattern so colour-blind users can
 * still distinguish helicities.
 */
export function SGWBSnapshotPlot({ timelineA, timelineB }: SGWBSnapshotPlotProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const currentFrameIndex = useVisualizerStore((s) => s.currentFrameIndex);

  const snapA = useResolvedSnapshot(timelineA, currentFrameIndex);
  const snapB = useResolvedSnapshot(timelineB ?? null, currentFrameIndex);

  const data = useMemo(() => {
    if (!snapA) return [];
    const rows: Record<string, number>[] = [];
    for (let i = 0; i < snapA.snapshot.f_Hz.length; i++) {
      const row: Record<string, number> = {
        f: snapA.snapshot.f_Hz[i],
        omegaA: Math.max(snapA.snapshot.Omega_gw[i] ?? 1e-30, 1e-30),
        chiA: snapA.snapshot.chirality[i] ?? 0,
      };
      if (snapB && snapB.snapshot.f_Hz.length === snapA.snapshot.f_Hz.length) {
        row.omegaB = Math.max(snapB.snapshot.Omega_gw[i] ?? 1e-30, 1e-30);
        row.chiB = snapB.snapshot.chirality[i] ?? 0;
      }
      rows.push(row);
    }
    return rows;
  }, [snapA, snapB]);

  if (!timelineA || !snapA) {
    return (
      <PanelContextMenu panelId="sgwb" label="Chiral SGWB" timelineA={timelineA}>
        <div className="h-full w-full">
          <EmptyPanel
            title="Chiral SGWB"
            reason={
              timelineA
                ? "No SGWB snapshot at or before this frame yet."
                : "Pick a run to see the SGWB spectrum."
            }
          />
        </div>
      </PanelContextMenu>
    );
  }

  return (
    <PanelContextMenu
      panelId="sgwb"
      label="Chiral SGWB"
      timelineA={timelineA}
      timelineB={timelineB}
      getExportTarget={() =>
        containerRef.current?.querySelector<SVGSVGElement>("svg.recharts-surface") ?? null
      }
    >
      <div ref={containerRef} className="flex h-full w-full flex-col" data-testid="visualizer-sgwb">
        <div className="flex items-center justify-between px-2 pt-1 text-[10px] font-mono text-muted-foreground">
          <span>{snapA.label}</span>
          <span>frame {snapA.frame}</span>
        </div>
        <div className="min-h-0 flex-1">
          <ResponsiveChart height="100%" label="sgwb-snap">
            {({ width, height }) => (
              <LineChart
                width={width}
                height={height}
                data={data}
                margin={{ left: 8, right: 16, top: 4, bottom: 12 }}
              >
                <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
                <XAxis
                  dataKey="f"
                  type="number"
                  scale="log"
                  domain={["auto", "auto"]}
                  tickFormatter={(v: number) => `10^${Math.round(Math.log10(v))}`}
                  tick={{
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    fill: "var(--color-muted-foreground)",
                  }}
                  label={{
                    value: "f [Hz]",
                    position: "insideBottom",
                    offset: -4,
                    fontSize: 11,
                    fill: "var(--color-muted-foreground)",
                  }}
                />
                <YAxis
                  type="number"
                  scale="log"
                  domain={["auto", "auto"]}
                  tickFormatter={(v: number) => `10^${Math.round(Math.log10(v))}`}
                  tick={{
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    fill: "var(--color-muted-foreground)",
                  }}
                  label={{
                    value: "ΩGW",
                    angle: -90,
                    position: "insideLeft",
                    fontSize: 11,
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
                  labelFormatter={(label) => `f = ${Number(label).toExponential(2)} Hz`}
                />
                <Line
                  type="monotone"
                  dataKey="omegaA"
                  name="ΩGW (A)"
                  stroke="var(--color-accent-indigo)"
                  strokeDasharray={chiralityDash(snapA.snapshot)}
                  strokeWidth={1.6}
                  dot={false}
                  isAnimationActive={false}
                />
                {snapB ? (
                  <Line
                    type="monotone"
                    dataKey="omegaB"
                    name="ΩGW (B)"
                    stroke="var(--color-chart-4)"
                    strokeDasharray={chiralityDash(snapB.snapshot)}
                    strokeWidth={1.6}
                    dot={false}
                    isAnimationActive={false}
                  />
                ) : null}
              </LineChart>
            )}
          </ResponsiveChart>
        </div>
      </div>
    </PanelContextMenu>
  );
}

function useResolvedSnapshot(
  timeline: BakedVisualizationTimeline | null,
  frameIdx: number,
): ResolvedSnapshot | null {
  return useMemo(() => {
    if (!timeline) return null;
    const indexed: { frame: number; snapshot: SgwbSnapshot }[] = [];
    for (let i = 0; i < timeline.frames.length; i++) {
      const s = timeline.frames[i].sgwb_snapshot;
      if (s) indexed.push({ frame: i, snapshot: s });
    }
    if (indexed.length === 0) return null;
    let active = indexed[0];
    for (const entry of indexed) {
      if (entry.frame <= frameIdx) active = entry;
      else break;
    }
    const ordinal = indexed.indexOf(active);
    const labels = ["source", "post-reheat", "today"];
    const label = labels[ordinal] ?? `snapshot ${ordinal + 1}`;
    return { ...active, label };
  }, [timeline, frameIdx]);
}

function chiralityDash(snap: SgwbSnapshot): string | undefined {
  if (snap.chirality.length === 0) return undefined;
  let acc = 0;
  for (const c of snap.chirality) acc += c;
  const mean = acc / snap.chirality.length;
  if (Math.abs(mean) < 0.05) return undefined; // ~unpolarised
  return mean > 0 ? "6 2" : "2 4";
}
