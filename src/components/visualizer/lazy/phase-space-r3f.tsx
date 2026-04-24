import { Suspense, forwardRef, useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { useVisualizerMaster } from "@/components/visualizer/visualizer-context";
import { useVisualizerStore } from "@/store/visualizer";
import { mapFrameByPhase } from "@/hooks/useFrameAt";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import type { BakedVisualizationTimeline } from "@/types/visualizer";

interface PhaseSpaceR3FProps {
  timelineA: BakedVisualizationTimeline;
  timelineB?: BakedVisualizationTimeline | null;
}

/**
 * Lazy chunk: holds @react-three/fiber + three.js. Pulled in only when
 * the Phase-Space panel actually mounts and WebGL is available.
 */
const PhaseSpaceR3F = forwardRef<HTMLCanvasElement, PhaseSpaceR3FProps>(function PhaseSpaceR3F(
  { timelineA, timelineB },
  ref,
) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Surface the underlying <canvas> so the export menu can grab it.
  useEffect(() => {
    const el = containerRef.current?.querySelector<HTMLCanvasElement>("canvas") ?? null;
    if (typeof ref === "function") ref(el);
    else if (ref) (ref as React.MutableRefObject<HTMLCanvasElement | null>).current = el;
  }, [ref]);

  return (
    <div ref={containerRef} className="h-full w-full">
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
            <ParticleField timeline={timelineB} isPartner partnerOffset={0.45} />
          ) : null}
        </Suspense>
        <Axes />
      </Canvas>
    </div>
  );
});

export default PhaseSpaceR3F;

interface ParticleFieldProps {
  timeline: BakedVisualizationTimeline;
  isPartner: boolean;
  partnerOffset: number;
}

function ParticleField({ timeline, isPartner, partnerOffset }: ParticleFieldProps) {
  const meshRef = useRef<THREE.InstancedMesh | null>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const tmpColor = useMemo(() => new THREE.Color(), []);
  const { invalidate } = useThree();

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
  const reducedMotion = usePrefersReducedMotion();
  const lastFrameRef = useRef(-1);

  useFrame(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const masterIdx = frameRef.current;
    const frameIdx =
      isPartner && syncByPhase && master
        ? mapFrameByPhase(master, timeline, masterIdx)
        : Math.min(masterIdx, timeline.frames.length - 1);

    // Reduced motion: only re-skin instances when the master frame
    // index actually changes (driven by user scrub or transport step).
    // Skips the per-rAF buffer rewrite so playback is felt as discrete
    // jumps instead of continuous motion.
    if (reducedMotion && frameIdx === lastFrameRef.current) return;
    lastFrameRef.current = frameIdx;

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
        const x = positions[off];
        const y = positions[off + 1];
        const z = positions[off + 2];
        dummy.position.set(x * 0.4, y * 0.6 + partnerOffset, z * 0.6);
        dummy.scale.setScalar(0.04);
      }
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      tmpColor.setRGB(colors[off] || 0.4, colors[off + 1] || 0.4, colors[off + 2] || 0.4);
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
      <gridHelper args={[6, 12, "#3f3f5a", "#26263a"]} rotation={[Math.PI / 2, 0, 0]} />
    </group>
  );
}
