/**
 * Neutral-atom array (AMO).
 *
 * Merged panel (P0-02): router-branch R3F array (Rydberg-excited atoms
 * highlighted when the frame says so, neutral otherwise) plus the
 * agent-branch blockade-radius overlay, drawn as translucent spheres of
 * the reported radius, and its caption.
 */
import { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type { AmoFrame } from "../types";
import { PanelShell } from "../PanelShell";

export interface AtomArray3DProps {
  frame: AmoFrame | null;
}

export function AtomArray3D({ frame }: AtomArray3DProps) {
  const positions = useMemo(() => frame?.atom_positions ?? [], [frame]);
  const radius = useMemo(
    () => new Map((frame?.blockade_radii ?? []).map((b) => [b.atom, b.r_blockade])),
    [frame],
  );
  const centre = useMemo(() => {
    if (positions.length === 0) return [0, 0, 0] as const;
    const mid = (k: "x" | "y" | "z") => {
      const v = positions.map((p) => p[k]);
      return (Math.min(...v) + Math.max(...v)) / 2;
    };
    return [mid("x"), mid("y"), mid("z")] as const;
  }, [positions]);
  const excited = positions.filter((p) => p.rydberg === true).length;
  const known = positions.some((p) => p.rydberg !== null);

  return (
    <PanelShell
      title="Neutral-atom array"
      empty={positions.length === 0}
      bodyClassName=""
      caption={
        <>
          {positions.length} atoms (μm) · {radius.size > 0 ? "blockade radii overlaid" : "no blockade radii"}
          {known ? ` · ${excited} Rydberg-excited` : ""}
        </>
      }
    >
      <Canvas camera={{ position: [10, 8, 18], fov: 45 }} dpr={[1, 1.5]} style={{ width: "100%", height: "100%" }}>
        <ambientLight intensity={0.55} />
        <directionalLight position={[10, 10, 10]} intensity={0.6} />
        {positions.map((p) => {
          const pos: [number, number, number] = [p.x - centre[0], p.y - centre[1], p.z - centre[2]];
          const r = radius.get(p.index);
          return (
            <group key={p.index} position={pos}>
              <mesh>
                <sphereGeometry args={[0.55, 18, 14]} />
                <meshStandardMaterial
                  color={p.rydberg ? "#f97316" : "#60a5fa"}
                  emissive={p.rydberg ? "#f97316" : "#000000"}
                  emissiveIntensity={p.rydberg ? 0.8 : 0}
                  roughness={0.4}
                />
              </mesh>
              {r !== undefined && r > 0 ? (
                <mesh>
                  <sphereGeometry args={[r, 24, 16]} />
                  <meshStandardMaterial color="#60a5fa" transparent opacity={0.08} depthWrite={false} />
                </mesh>
              ) : null}
            </group>
          );
        })}
        <OrbitControls />
      </Canvas>
    </PanelShell>
  );
}

export default AtomArray3D;
