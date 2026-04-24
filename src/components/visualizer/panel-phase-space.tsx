import { Suspense, forwardRef, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { ClientOnly } from "@/components/client-only";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import { PanelContextMenu } from "@/components/visualizer/panel-context-menu";
import { useVisualizerMaster } from "@/components/visualizer/visualizer-context";
import { useVisualizerStore } from "@/store/visualizer";
import { useChat } from "@/store/ui";
import { mapFrameByPhase } from "@/hooks/useFrameAt";
import type { BakedVisualizationTimeline } from "@/types/visualizer";

export interface PhaseSpaceCanvasProps {
  timelineA: BakedVisualizationTimeline | null;
  timelineB?: BakedVisualizationTimeline | null;
  /** Pixel height. Defaults to 100% of parent. */
  height?: number | string;
}

/**
 * Panel 1 — chiral mode phase space.
 *
 * Per-frame `useFrame` reads `timeline.baked.positions[frame]` and
 * pushes a 4×4 matrix into a single `InstancedMesh`. Per-particle
 * data never round-trips through React.
 *
 * When WebGL is unavailable the panel falls back to a Canvas-2D scatter
 * driven by the same baked buffers.
 */
export function PhaseSpaceCanvas({
  timelineA,
  timelineB,
  height = "100%",
}: PhaseSpaceCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const r3fCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const fallbackRef = useRef<HTMLCanvasElement | null>(null);
  const [webglOk, setWebglOk] = useState<boolean | null>(null);

  useEffect(() => {
    setWebglOk(detectWebGL());
  }, []);

  // R3F's <Canvas> renders an internal <canvas>. Walk the container once
  // we know the renderer is mounted so the export menu can grab it.
  useEffect(() => {
    if (!containerRef.current) return;
    r3fCanvasRef.current =
      containerRef.current.querySelector<HTMLCanvasElement>("canvas");
  }, [webglOk]);

  if (!timelineA) {
    return (
      <PanelContextMenu
        panelId="phase-space"
        label="Phase space"
        timelineA={null}
      >
        <div className="h-full w-full" style={{ height }}>
          <EmptyPanel
            title="Phase space"
            reason="Pick a run to populate the chiral mode field."
          />
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
      getExportTarget={() =>
        r3fCanvasRef.current ?? fallbackRef.current ?? null
      }
    >
      <div
        ref={containerRef}
        className="relative h-full w-full overflow-hidden rounded-md bg-card"
        style={{ height }}
        data-testid="visualizer-phase-space"
      >
        <ClientOnly
          fallback={
            <EmptyPanel title="Phase space" reason="Loading renderer…" dense />
          }
        >
          {webglOk === false ? (
            <Canvas2DFallback
              ref={fallbackRef}
              timelineA={timelineA}
              timelineB={timelineB ?? null}
            />
          ) : (
            <Canvas
              dpr={[1, 2]}
              orthographic
              camera={{ zoom: 80, position: [0, 0, 8] }}
              gl={{ antialias: true, preserveDrawingBuffer: true }}
              onCreated={({ gl }) => {
                gl.setClearColor(new THREE.Color("#0b0b14"), 0);
              }}
            >
              <ambientLight intensity={0.6} />
              <Suspense fallback={null}>
                <ParticleField
                  timeline={timelineA}
                  isPartner={false}
                  partnerOffset={timelineB ? -0.45 : 0}
                />
                {timelineB ? (
                  <ParticleField
                    timeline={timelineB}
                    isPartner
                    partnerOffset={0.45}
                  />
                ) : null}
              </Suspense>
              <Axes />
            </Canvas>
          )}
        </ClientOnly>
        <PinFrameCorner timelineA={timelineA} />
      </div>
    </PanelContextMenu>
  );
}

/* ─── R3F particle field ─────────────────────────────────────────── */

interface ParticleFieldProps {
  timeline: BakedVisualizationTimeline;
  isPartner: boolean;
  /** Y-offset so A vs B don't overlap in overlay mode. */
  partnerOffset: number;
}

function ParticleField({
  timeline,
  isPartner,
  partnerOffset,
}: ParticleFieldProps) {
  const meshRef = useRef<THREE.InstancedMesh | null>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const tmpColor = useMemo(() => new THREE.Color(), []);
  const { invalidate } = useThree();

  // Subscribe to currentFrameIndex without re-rendering React on every tick.
  const frameRef = useRef(useVisualizerStore.getState().currentFrameIndex);
  useEffect(
    () =>
      useVisualizerStore.subscribe(
        (s) => s.currentFrameIndex,
        (i) => {
          frameRef.current = i;
          invalidate();
        },
      ),
    [invalidate],
  );

  const syncByPhase = useVisualizerStore((s) => s.syncByPhase);
  const master = useVisualizerMaster();

  useFrame(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const masterIdx = frameRef.current;
    const frameIdx =
      isPartner && syncByPhase && master
        ? mapFrameByPhase(master, timeline, masterIdx)
        : Math.min(masterIdx, timeline.frames.length - 1);

    const positions = timeline.baked.positions[frameIdx];
    const colors = timeline.baked.colors[frameIdx];
    const count = timeline.baked.modeCount[frameIdx];
    if (!positions || !colors) return;

    for (let i = 0; i < timeline.baked.maxModes; i++) {
      const off = i * 3;
      if (i >= count || !Number.isFinite(positions[off])) {
        dummy.position.set(0, 0, 0);
        dummy.scale.setScalar(0);
      } else {
        const x = positions[off]; // log10(k)
        const y = positions[off + 1]; // h_+ re
        const z = positions[off + 2]; // h_+ im
        dummy.position.set(x * 0.4, y * 0.6 + partnerOffset, z * 0.6);
        dummy.scale.setScalar(0.04);
      }
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      tmpColor.setRGB(
        colors[off] || 0.4,
        colors[off + 1] || 0.4,
        colors[off + 2] || 0.4,
      );
      mesh.setColorAt(i, tmpColor);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, timeline.baked.maxModes]}
      frustumCulled={false}
    >
      <sphereGeometry args={[1, 12, 12]} />
      <meshStandardMaterial
        vertexColors
        toneMapped={false}
        emissiveIntensity={isPartner ? 0.4 : 0.6}
      />
    </instancedMesh>
  );
}

function Axes() {
  return (
    <group>
      <gridHelper
        args={[6, 12, "#3f3f5a", "#26263a"]}
        rotation={[Math.PI / 2, 0, 0]}
      />
    </group>
  );
}

/* ─── Canvas-2D fallback ─────────────────────────────────────────── */

interface FallbackProps {
  timelineA: BakedVisualizationTimeline;
  timelineB: BakedVisualizationTimeline | null;
}

const Canvas2DFallback = forwardRef<HTMLCanvasElement, FallbackProps>(
  function Canvas2DFallback({ timelineA, timelineB }, ref) {
    const localRef = useRef<HTMLCanvasElement | null>(null);
    const setRefs = (el: HTMLCanvasElement | null) => {
      localRef.current = el;
      if (typeof ref === "function") ref(el);
      else if (ref)
        (ref as React.MutableRefObject<HTMLCanvasElement | null>).current = el;
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

      // Background grid.
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

    return (
      <canvas
        ref={setRefs}
        className="h-full w-full"
        aria-label="Phase space (2D fallback)"
      />
    );
  },
);

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
    // Map log10(k) ∈ [-4, 4] → x; H_+ re ∈ [-1, 1] → y around centre.
    const x = ((lk + 4) / 8) * rect.width;
    const y =
      rect.height / 2 -
      yval * (rect.height / 4) +
      (variant === 1 ? rect.height / 6 : 0);
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

function PinFrameCorner({
  timelineA,
}: {
  timelineA: BakedVisualizationTimeline;
}) {
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
      c.getContext("webgl2") ||
        c.getContext("webgl") ||
        c.getContext("experimental-webgl"),
    );
  } catch {
    return false;
  }
}
