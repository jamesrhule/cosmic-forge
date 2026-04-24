import { Suspense, lazy, useMemo, useRef } from "react";
import { ResponsiveChart } from "@/components/charts/responsive-chart";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import { PanelContextMenu } from "@/components/visualizer/panel-context-menu";
import { PanelSkeleton } from "@/components/visualizer/panel-skeleton";
import { useVisualizerStore } from "@/store/visualizer";
import type { BakedVisualizationTimeline, SgwbSnapshot } from "@/types/visualizer";

const SgwbChart = lazy(() => import("./lazy/sgwb-chart"));

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
 * The Recharts surface lives in a lazy chunk; this file owns the
 * snapshot resolution and chirality dash heuristic.
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
              <Suspense fallback={<PanelSkeleton label="Loading chart…" />}>
                <SgwbChart
                  width={width}
                  height={height}
                  data={data}
                  snapADash={chiralityDash(snapA.snapshot)}
                  snapBDash={snapB ? chiralityDash(snapB.snapshot) : undefined}
                  hasPartner={Boolean(snapB)}
                />
              </Suspense>
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
  if (Math.abs(mean) < 0.05) return undefined;
  return mean > 0 ? "6 2" : "2 4";
}
