import { Suspense, forwardRef, lazy, useEffect, useRef, useState } from "react";
import { ClientOnly } from "@/components/client-only";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import { PanelContextMenu } from "@/components/visualizer/panel-context-menu";
import { PanelSkeleton } from "@/components/visualizer/panel-skeleton";
import { useVisualizerStore } from "@/store/visualizer";
import { useChat } from "@/store/ui";
import type { BakedVisualizationTimeline } from "@/types/visualizer";

// R3F + three.js are bundled in this chunk only.
const PhaseSpaceR3F = lazy(() => import("./lazy/phase-space-r3f"));

export interface PhaseSpaceCanvasProps {
  timelineA: BakedVisualizationTimeline | null;
  timelineB?: BakedVisualizationTimeline | null;
  /** Pixel height. Defaults to 100% of parent. */
  height?: number | string;
}

/**
 * Panel 1 — chiral mode phase space.
 *
 * The R3F renderer + three.js sit in a lazy chunk gated behind
 * `<ClientOnly>` so they never enter the SSR bundle. When WebGL is
 * unavailable the panel falls back to a Canvas-2D scatter driven by the
 * same baked buffers.
 */
export function PhaseSpaceCanvas({ timelineA, timelineB, height = "100%" }: PhaseSpaceCanvasProps) {
  const r3fCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const fallbackRef = useRef<HTMLCanvasElement | null>(null);
  const [webglOk, setWebglOk] = useState<boolean | null>(null);

  useEffect(() => {
    setWebglOk(detectWebGL());
  }, []);

  if (!timelineA) {
    return (
      <PanelContextMenu panelId="phase-space" label="Phase space" timelineA={null}>
        <div className="h-full w-full" style={{ height }}>
          <EmptyPanel title="Phase space" reason="Pick a run to populate the chiral mode field." />
        </div>
      </PanelContextMenu>
    );
  }

  return (
    <PanelContextMenu
      panelId="phase-space"
      label="Phase space"
      timelineA={timelineA}
      timelineB={timelineB}
      getExportTarget={() => r3fCanvasRef.current ?? fallbackRef.current ?? null}
    >
      <div
        className="relative h-full w-full overflow-hidden rounded-md bg-card"
        style={{ height }}
        data-testid="visualizer-phase-space"
      >
        <ClientOnly fallback={<PanelSkeleton label="Loading 3D…" />}>
          {webglOk === false ? (
            <Canvas2DFallback
              ref={fallbackRef}
              timelineA={timelineA}
              timelineB={timelineB ?? null}
            />
          ) : (
            <Suspense fallback={<PanelSkeleton label="Loading 3D…" />}>
              <PhaseSpaceR3F
                ref={r3fCanvasRef}
                timelineA={timelineA}
                timelineB={timelineB ?? null}
              />
            </Suspense>
          )}
        </ClientOnly>
        <PinFrameCorner timelineA={timelineA} />
      </div>
    </PanelContextMenu>
  );
}

/* ─── Canvas-2D fallback ─────────────────────────────────────────── */

interface FallbackProps {
  timelineA: BakedVisualizationTimeline;
  timelineB: BakedVisualizationTimeline | null;
}

const Canvas2DFallback = forwardRef<HTMLCanvasElement, FallbackProps>(function Canvas2DFallback(
  { timelineA, timelineB },
  ref,
) {
  const localRef = useRef<HTMLCanvasElement | null>(null);
  const setRefs = (el: HTMLCanvasElement | null) => {
    localRef.current = el;
    if (typeof ref === "function") ref(el);
    else if (ref) (ref as React.MutableRefObject<HTMLCanvasElement | null>).current = el;
  };

  const frame = useVisualizerStore((s) => s.currentFrameIndex);

  useEffect(() => {
    const canvas = localRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);

    ctx.strokeStyle = "rgba(120,120,140,0.18)";
    ctx.lineWidth = 1;
    const cols = 12;
    for (let i = 0; i <= cols; i++) {
      const x = (i / cols) * rect.width;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, rect.height);
      ctx.stroke();
    }
    for (let i = 0; i <= 6; i++) {
      const y = (i / 6) * rect.height;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(rect.width, y);
      ctx.stroke();
    }

    drawTimeline(ctx, rect, timelineA, frame, 0);
    if (timelineB) drawTimeline(ctx, rect, timelineB, frame, 1);
  }, [frame, timelineA, timelineB]);

  return <canvas ref={setRefs} className="h-full w-full" aria-label="Phase space (2D fallback)" />;
});

function drawTimeline(
  ctx: CanvasRenderingContext2D,
  rect: DOMRect,
  timeline: BakedVisualizationTimeline,
  masterFrame: number,
  variant: 0 | 1,
) {
  const idx = Math.min(masterFrame, timeline.frames.length - 1);
  const positions = timeline.baked.positions[idx];
  const colors = timeline.baked.colors[idx];
  const count = timeline.baked.modeCount[idx];
  if (!positions || !colors) return;

  for (let i = 0; i < count; i++) {
    const off = i * 3;
    const lk = positions[off];
    if (!Number.isFinite(lk)) continue;
    const yval = positions[off + 1];
    const x = ((lk + 4) / 8) * rect.width;
    const y = rect.height / 2 - yval * (rect.height / 4) + (variant === 1 ? rect.height / 6 : 0);
    const r = Math.round((colors[off] || 0.4) * 255);
    const g = Math.round((colors[off + 1] || 0.4) * 255);
    const b = Math.round((colors[off + 2] || 0.4) * 255);
    ctx.fillStyle = `rgba(${r},${g},${b},${variant === 1 ? 0.6 : 0.9})`;
    ctx.beginPath();
    ctx.arc(x, y, variant === 1 ? 2.5 : 3, 0, Math.PI * 2);
    ctx.fill();
  }
}

/* ─── Pin-frame corner badge ────────────────────────────────────── */

function PinFrameCorner({ timelineA }: { timelineA: BakedVisualizationTimeline }) {
  const frame = useVisualizerStore((s) => s.currentFrameIndex);
  const addContext = useChat((s) => s.addContext);
  const setOpen = useChat((s) => s.setOpen);
  const tau = timelineA.frames[frame]?.tau ?? 0;
  return (
    <button
      type="button"
      onClick={() => {
        addContext({
          kind: "visualizer_frame",
          label: `${timelineA.runId} @ τ=${tau.toFixed(2)}`,
          runId: timelineA.runId,
          frameIndex: frame,
          tau,
        });
        setOpen(true);
      }}
      className="absolute right-2 top-2 rounded bg-card/80 px-2 py-1 font-mono text-[10px] text-muted-foreground shadow-sm hover:bg-accent hover:text-accent-foreground"
    >
      τ={tau.toFixed(2)} · pin
    </button>
  );
}

function detectWebGL(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const c = document.createElement("canvas");
    return Boolean(
      c.getContext("webgl2") || c.getContext("webgl") || c.getContext("experimental-webgl"),
    );
  } catch {
    return false;
  }
}
