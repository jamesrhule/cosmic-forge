/**
 * Orbital occupation (chemistry).
 *
 * Merged panel (P0-02): the router-branch R3F sphere grid (radius ∝
 * √occupation, colour by orbital energy) plus the agent-branch summary
 * caption. When the frame carries no orbital energies the spheres are
 * drawn in one neutral colour — an energy scale is never invented.
 */
import { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type { ChemistryFrame } from "../types";
import { WebGLGate } from "../WebGLGate";
import { PanelShell, hslToHex } from "../PanelShell";

export interface OrbitalOccupation3DProps {
  frame: ChemistryFrame | null;
}

const NEUTRAL = "#60a5fa";

export function OrbitalOccupation3D({ frame }: OrbitalOccupation3DProps) {
  const orbitals = useMemo(() => frame?.orbitals ?? [], [frame]);

  const { items, hasEnergy, maxOcc } = useMemo(() => {
    const energies = orbitals.map((o) => o.energy_hartree).filter((e): e is number => e !== null);
    const known = energies.length === orbitals.length && orbitals.length > 0;
    const minE = known ? Math.min(...energies) : 0;
    const span = known ? Math.max(1e-9, Math.max(...energies) - minE) : 1;
    const out = orbitals.map((o, i) => {
      const r = Math.sqrt(Math.max(0.05, o.occupation)) * 0.55;
      const x = (i % 4) * 1.6 - 2.4;
      const y = Math.floor(i / 4) * 1.6 - 1.6;
      // hue: low energy = blue (0.66), high = red (0).
      const color =
        known && o.energy_hartree !== null
          ? hslToHex((1 - (o.energy_hartree - minE) / span) * 0.66, 0.6, 0.55)
          : NEUTRAL;
      return { id: o.index, x, y, r, color };
    });
    return {
      items: out,
      hasEnergy: known,
      maxOcc: orbitals.reduce((m, o) => Math.max(m, o.occupation), 0),
    };
  }, [orbitals]);

  return (
    <PanelShell
      title="Orbital occupation"
      empty={items.length === 0}
      bodyClassName=""
      caption={
        <>
          {items.length} orbitals · max occupancy {maxOcc.toFixed(2)}
          {hasEnergy ? " · colour = orbital energy" : " · orbital energies not provided"}
        </>
      }
    >
      <WebGLGate title="Orbital occupation (3D)">
        <Canvas
          camera={{ position: [0, 0, 8], fov: 45 }}
          dpr={[1, 1.5]}
          style={{ width: "100%", height: "100%" }}
        >
          <ambientLight intensity={0.6} />
          <directionalLight position={[5, 5, 5]} intensity={0.6} />
          {items.map((it) => (
            <mesh key={it.id} position={[it.x, it.y, 0]}>
              <sphereGeometry args={[it.r, 24, 16]} />
              <meshStandardMaterial color={it.color} roughness={0.35} />
            </mesh>
          ))}
          <OrbitControls enablePan={false} />
        </Canvas>
      </WebGLGate>
    </PanelShell>
  );
}

export default OrbitalOccupation3D;
