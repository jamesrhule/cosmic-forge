import { useEffect } from "react";
import { Layers, Maximize2, Radio, RefreshCw, Split } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Toggle } from "@/components/ui/toggle";
import { TransportBar } from "@/components/visualizer/transport-bar";
import { KeymapOverlay } from "@/components/visualizer/keymap-overlay";
import { PhaseSpaceCanvas } from "@/components/visualizer/panel-phase-space";
import { GBWindowTimeline } from "@/components/visualizer/panel-gb-window";
import { SGWBSnapshotPlot } from "@/components/visualizer/panel-sgwb";
import { AnomalyIntegrandPlot } from "@/components/visualizer/panel-anomaly";
import { LeptonFlowSankey } from "@/components/visualizer/panel-lepton-flow";
import { FormulaOverlay } from "@/components/visualizer/panel-formula";
import { PanelErrorBoundary } from "@/components/visualizer/panel-error-boundary";
import { StreamingProgressIndicator } from "@/components/visualizer/streaming-progress-indicator";
import { VisualizerMasterContext } from "@/components/visualizer/visualizer-context";
import { useVisualizerStore } from "@/store/visualizer";
import { useVisualizationStream } from "@/hooks/useVisualizationStream";
import { downloadBlob, exportCanvasPng } from "@/lib/exportFrame";
import { cn } from "@/lib/utils";
import { FEATURES } from "@/config/features";
import type { BakedVisualizationTimeline } from "@/types/visualizer";

const SHOW_LIVE_STREAM_TOGGLE = FEATURES.liveVisualization || import.meta.env.DEV;

export interface VisualizerLayoutProps {
  /** Master timeline (A side). `null` shows the empty state across all panels. */
  timelineA: BakedVisualizationTimeline | null;
  /** Optional partner timeline (B side). Required for ab_overlay / split_screen. */
  timelineB?: BakedVisualizationTimeline | null;
  /** Optional left-of-toolbar element (run picker, breadcrumbs, etc.). */
  toolbarLead?: React.ReactNode;
  className?: string;
}

/**
 * The visualizer's full surface: header (comparison toggles + export) /
 * panel grid / transport bar. Owns:
 *   - the comparison hotkeys (O / S / P / E),
 *   - the master-timeline context (so partner panels can phase-map),
 *   - the conditional 2-up split-screen layout.
 */
export function VisualizerLayout({
  timelineA,
  timelineB,
  toolbarLead,
  className,
}: VisualizerLayoutProps) {
  const comparisonMode = useVisualizerStore((s) => s.comparisonMode);
  const setComparisonMode = useVisualizerStore((s) => s.setComparisonMode);
  const syncByPhase = useVisualizerStore((s) => s.syncByPhase);
  const setSyncByPhase = useVisualizerStore((s) => s.setSyncByPhase);

  // Keep the transport store's totalFrames in lockstep with the master.
  const loadTimelines = useVisualizerStore((s) => s.loadTimelines);
  useEffect(() => {
    loadTimelines({
      runIdA: timelineA?.runId ?? "",
      runIdB: timelineB?.runId ?? null,
      totalFrames: timelineA?.frames.length ?? 0,
    });
  }, [timelineA, timelineB, loadTimelines]);

  // Comparison + export hotkeys (transport hotkeys live on TransportBar).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || e.metaKey || e.ctrlKey) return;
      switch (e.key) {
        case "o":
        case "O":
          if (!timelineB) return;
          e.preventDefault();
          setComparisonMode(comparisonMode === "ab_overlay" ? "single" : "ab_overlay");
          return;
        case "s":
        case "S":
          if (!timelineB) return;
          e.preventDefault();
          setComparisonMode(comparisonMode === "split_screen" ? "single" : "split_screen");
          return;
        case "p":
        case "P":
          e.preventDefault();
          setSyncByPhase(!syncByPhase);
          return;
        case "e":
        case "E":
          e.preventDefault();
          exportFirstCanvas();
          return;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [comparisonMode, syncByPhase, timelineB, setComparisonMode, setSyncByPhase]);

  const showB =
    !!timelineB && (comparisonMode === "ab_overlay" || comparisonMode === "split_screen");
  const splitScreen = !!timelineB && comparisonMode === "split_screen";

  return (
    <VisualizerMasterContext.Provider value={timelineA}>
      <div
        className={cn(
          "flex h-full w-full min-h-0 flex-col bg-background text-foreground",
          className,
        )}
        data-testid="visualizer-layout"
      >
        <header className="flex items-center justify-between gap-3 border-b border-border bg-card/60 px-3 py-2">
          <div className="flex min-w-0 items-center gap-2">{toolbarLead}</div>
          <div className="flex items-center gap-2">
            <Toggle
              size="sm"
              pressed={comparisonMode === "ab_overlay"}
              onPressedChange={(on) => setComparisonMode(on ? "ab_overlay" : "single")}
              disabled={!timelineB}
              aria-label="A↔B overlay"
              title="A↔B overlay (O)"
            >
              <Layers className="mr-1 h-3.5 w-3.5" />
              <span className="text-[11px]">Overlay</span>
            </Toggle>
            <Toggle
              size="sm"
              pressed={comparisonMode === "split_screen"}
              onPressedChange={(on) => setComparisonMode(on ? "split_screen" : "single")}
              disabled={!timelineB}
              aria-label="Split screen"
              title="Split screen (S)"
            >
              <Split className="mr-1 h-3.5 w-3.5" />
              <span className="text-[11px]">Split</span>
            </Toggle>
            <Toggle
              size="sm"
              pressed={syncByPhase}
              onPressedChange={setSyncByPhase}
              aria-label="Sync by phase"
              title="Sync by phase (P)"
            >
              <RefreshCw className="mr-1 h-3.5 w-3.5" />
              <span className="text-[11px]">Sync phase</span>
            </Toggle>
            {SHOW_LIVE_STREAM_TOGGLE && timelineA?.runId ? (
              <LiveStreamControl runId={timelineA.runId} />
            ) : null}
            <Button
              size="sm"
              variant="ghost"
              aria-label="Export phase space"
              title="Export phase space (E)"
              onClick={exportFirstCanvas}
            >
              <Maximize2 className="mr-1 h-3.5 w-3.5" />
              <span className="text-[11px]">Export</span>
            </Button>
          </div>
        </header>

        <main className="min-h-0 flex-1">
          {splitScreen && timelineB ? (
            <div className="grid h-full min-h-0 grid-cols-2 gap-2 p-2">
              <PanelGrid timelineA={timelineA} timelineB={null} dense />
              <PanelGrid timelineA={timelineB} timelineB={null} dense />
            </div>
          ) : (
            <div className="h-full min-h-0 p-2">
              <PanelGrid timelineA={timelineA} timelineB={showB ? (timelineB ?? null) : null} />
            </div>
          )}
        </main>

        <TransportBar
          label={
            timelineA
              ? `${timelineA.runId}${timelineB && showB ? ` ↔ ${timelineB.runId}` : ""}`
              : "no run loaded"
          }
        />
        <KeymapOverlay />
      </div>
    </VisualizerMasterContext.Provider>
  );
}

interface PanelGridProps {
  timelineA: BakedVisualizationTimeline | null;
  timelineB: BakedVisualizationTimeline | null;
  /** Compact mode for split-screen halves. */
  dense?: boolean;
}

function PanelGrid({ timelineA, timelineB, dense = false }: PanelGridProps) {
  return (
    <div
      className={cn(
        "grid h-full min-h-0 gap-2",
        dense ? "grid-cols-2 grid-rows-3" : "grid-cols-3 grid-rows-2",
      )}
    >
      <PanelTile>
        <PanelErrorBoundary label="Phase space" dense={dense}>
          <PhaseSpaceCanvas timelineA={timelineA} timelineB={timelineB} />
        </PanelErrorBoundary>
      </PanelTile>
      <PanelTile>
        <PanelErrorBoundary label="Gauss-Bonnet window" dense={dense}>
          <GBWindowTimeline timelineA={timelineA} timelineB={timelineB} />
        </PanelErrorBoundary>
      </PanelTile>
      <PanelTile>
        <PanelErrorBoundary label="Chiral SGWB" dense={dense}>
          <SGWBSnapshotPlot timelineA={timelineA} timelineB={timelineB} />
        </PanelErrorBoundary>
      </PanelTile>
      <PanelTile>
        <PanelErrorBoundary label="Anomaly integrand" dense={dense}>
          <AnomalyIntegrandPlot timelineA={timelineA} timelineB={timelineB} />
        </PanelErrorBoundary>
      </PanelTile>
      <PanelTile>
        <PanelErrorBoundary label="Lepton flow" dense={dense}>
          <LeptonFlowSankey timelineA={timelineA} timelineB={timelineB} />
        </PanelErrorBoundary>
      </PanelTile>
      <PanelTile>
        <PanelErrorBoundary label="Formula" dense={dense}>
          <FormulaOverlay timelineA={timelineA} timelineB={timelineB} />
        </PanelErrorBoundary>
      </PanelTile>
    </div>
  );
}

function PanelTile({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-0 min-w-0 overflow-hidden rounded-md border border-border bg-card">
      {children}
    </div>
  );
}


/**
 * Header control: "Live" toggle + streaming progress pill.
 *
 * Mounts the JSONL stream consumer for the active master timeline and
 * surfaces frame-arrival counters next to the Export button. The pill
 * stays hidden until the user starts a stream so the chrome is quiet
 * by default.
 */
function LiveStreamControl({ runId }: { runId: string }) {
  const stream = useVisualizationStream(runId);
  const isActive = stream.status === "connecting" || stream.status === "streaming";
  // Until the live WS path is wired the toggle drives a bundled JSONL
  // demo stream; surface that distinction in the title so dev users
  // aren't confused when the indicator caps at 60 frames.
  const isLive = FEATURES.liveVisualization;
  const tooltip = isActive
    ? "Stop stream"
    : isLive
      ? "Start live stream"
      : "Start demo stream (fixture)";
  const ariaLabel = isActive
    ? "Stop stream"
    : isLive
      ? "Start live stream"
      : "Start demo stream";
  return (
    <div className="flex items-center gap-2">
      <Toggle
        size="sm"
        pressed={isActive}
        onPressedChange={(on) => (on ? stream.start() : stream.stop())}
        aria-label={ariaLabel}
        title={tooltip}
      >
        <Radio className="mr-1 h-3.5 w-3.5" />
        <span className="text-[11px]">{isLive ? "Live" : "Demo"}</span>
      </Toggle>
      <StreamingProgressIndicator
        status={stream.status}
        framesReceived={stream.framesReceived}
        framesExpected={stream.framesExpected}
      />
    </div>
  );
}


/**
 * Best-effort PNG export hotkey. Picks the first WebGL canvas inside the
 * visualizer (the phase-space panel). Per-panel exports are still
 * available via right-click → "Export this panel as PNG".
 */
async function exportFirstCanvas() {
  const root = document.querySelector<HTMLElement>("[data-testid='visualizer-layout']");
  if (!root) return;
  const canvas = root.querySelector<HTMLCanvasElement>(
    "[data-testid='visualizer-phase-space'] canvas",
  );
  const { toast } = await import("sonner");
  if (!canvas) {
    toast.error("Nothing to export", {
      description: "The phase-space panel hasn't rendered yet.",
    });
    return;
  }
  try {
    const blob = await exportCanvasPng(canvas);
    downloadBlob(blob, `visualizer-frame.png`);
    toast.success("Frame exported");
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("[visualizer] export hotkey failed", err);
    toast.error("Export failed", {
      description: err instanceof Error ? err.message : "Unknown error",
    });
  }
}
