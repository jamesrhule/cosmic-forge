import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { useChat } from "@/store/ui";
import { useVisualizerStore } from "@/store/visualizer";
import { downloadBlob, exportCanvasPng, exportSvgPng } from "@/lib/exportFrame";
import type { BakedVisualizationTimeline } from "@/types/visualizer";

export interface PanelContextMenuProps {
  /** Short identifier for the panel — used in the export filename. */
  panelId: string;
  /** Human-readable label shown at the top of the menu. */
  label: string;
  /** Currently rendered timeline (A side). Required for context chips. */
  timelineA: BakedVisualizationTimeline | null;
  /** Optional B-side timeline (overlay / split-screen). */
  timelineB?: BakedVisualizationTimeline | null;
  /**
   * Provider for the panel's exportable element. Return either an
   * `HTMLCanvasElement` (R3F) or an `SVGSVGElement` (Recharts / Sankey),
   * or `null` if export isn't supported. The function is invoked at the
   * moment the user clicks "Export…" — not at mount — so the panel can
   * walk its own DOM tree lazily.
   */
  getExportTarget?: () => HTMLCanvasElement | SVGSVGElement | null | undefined;
  children: React.ReactNode;
}

/**
 * Wraps any visualizer panel with a Radix context menu offering:
 *   - "Pin frame to assistant" (always)
 *   - "Pin A↔B comparison" (only when timelineB is present)
 *   - "Export this panel as PNG" (when getExportTarget yields a node)
 *
 * Keeps the UI surface uniform across the six panels without forcing
 * each one to import the chat store or the export helpers directly.
 */
export function PanelContextMenu({
  panelId,
  label,
  timelineA,
  timelineB,
  getExportTarget,
  children,
}: PanelContextMenuProps) {
  const addContext = useChat((s) => s.addContext);
  const setOpen = useChat((s) => s.setOpen);
  const currentFrameIndex = useVisualizerStore((s) => s.currentFrameIndex);

  const pinFrame = () => {
    if (!timelineA) return;
    const frame = timelineA.frames[currentFrameIndex];
    addContext({
      kind: "visualizer_frame",
      label: `${timelineA.runId} @ frame ${currentFrameIndex}`,
      runId: timelineA.runId,
      frameIndex: currentFrameIndex,
      tau: frame?.tau ?? 0,
    });
    setOpen(true);
  };

  const pinComparison = () => {
    if (!timelineA || !timelineB) return;
    addContext({
      kind: "visualizer_comparison",
      label: `${timelineA.runId} vs ${timelineB.runId} @ frame ${currentFrameIndex}`,
      runIdA: timelineA.runId,
      runIdB: timelineB.runId,
      frameIndex: currentFrameIndex,
    });
    setOpen(true);
  };

  const exportPng = async () => {
    const target = getExportTarget?.();
    if (!target) return;
    const filename = `${panelId}-${timelineA?.runId ?? "frame"}-${currentFrameIndex}.png`;
    try {
      let blob: Blob;
      if (target instanceof HTMLCanvasElement) {
        blob = await exportCanvasPng(target);
      } else {
        const rect = target.getBoundingClientRect();
        blob = await exportSvgPng(target, {
          width: rect.width,
          height: rect.height,
          background: "white",
        });
      }
      downloadBlob(blob, filename);
    } catch (err) {
      // Failures are non-fatal — surfaced via console for the dev overlay.
      // eslint-disable-next-line no-console
      console.warn(`[visualizer] PNG export failed for ${panelId}`, err);
    }
  };

  const canExport = Boolean(getExportTarget);
  const canCompare = Boolean(timelineA && timelineB);

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent className="w-56">
        <div className="px-2 pb-1 pt-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
        <ContextMenuSeparator />
        <ContextMenuItem onSelect={pinFrame} disabled={!timelineA}>
          Pin frame to assistant
        </ContextMenuItem>
        <ContextMenuItem onSelect={pinComparison} disabled={!canCompare}>
          Pin A↔B comparison
        </ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem onSelect={exportPng} disabled={!canExport}>
          Export this panel as PNG
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}
