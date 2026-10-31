/**
 * Lattice + bond strengths (condensed matter).
 *
 * Reconciles the agent-branch `LatticeBonds` and the router-branch
 * `LatticeWithBondColors` (P0-02). A bond is drawn only when the frame
 * names both endpoints; strengths without endpoints (the flat wire
 * shape) are counted in the caption, never paired with guessed sites.
 * Sites are coloured by spin when provided, otherwise neutral.
 */
import { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { CondmatFrame } from "../types";
import { PanelShell } from "../PanelShell";

export interface LatticeWithBondColorsProps {
  frame: CondmatFrame | null;
}

interface BondMesh {
  key: string;
  position: [number, number, number];
  rotation: [number, number, number];
  length: number;
  color: string;
}

export function LatticeWithBondColors({ frame }: LatticeWithBondColorsProps) {
  const sites = useMemo(() => frame?.lattice_sites ?? [], [frame]);
  const bonds = useMemo(() => frame?.bond_strengths ?? [], [frame]);
  const unpaired = frame?.unpaired_bond_strengths.length ?? 0;

  const centre = useMemo(() => {
    if (sites.length === 0) return [0, 0] as const;
    const xs = sites.map((s) => s.x);
    const ys = sites.map((s) => s.y);
    return [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2] as const;
  }, [sites]);

  const bondMeshes = useMemo<BondMesh[]>(() => {
    if (sites.length === 0 || bonds.length === 0) return [];
    const byIndex = new Map(sites.map((s) => [s.index, s]));
    const minS = Math.min(...bonds.map((b) => b.strength));
    const span = Math.max(1e-9, Math.max(...bonds.map((b) => b.strength)) - minS);
    const up = new THREE.Vector3(0, 1, 0);
    return bonds.flatMap((b): BondMesh[] => {
      const a = byIndex.get(b.a);
      const c = byIndex.get(b.b);
      if (!a || !c) return [];
      const dir = new THREE.Vector3(c.x - a.x, c.y - a.y, c.z - a.z);
      const length = dir.length();
      const euler = new THREE.Euler().setFromQuaternion(
        new THREE.Quaternion().setFromUnitVectors(up, dir.clone().normalize()),
      );
      const t = (b.strength - minS) / span;
      const color = new THREE.Color().setHSL(0.66 - 0.66 * t, 0.7, 0.55); // blue weak → red strong
      return [
        {
          key: `${b.a}-${b.b}`,
          position: [(a.x + c.x) / 2, (a.y + c.y) / 2, (a.z + c.z) / 2],
          rotation: [euler.x, euler.y, euler.z],
          length,
          color: `#${color.getHexString()}`,
        },
      ];
    });
  }, [sites, bonds]);

  return (
    <PanelShell
      title="Lattice + bond strengths"
      empty={sites.length === 0}
      bodyClassName=""
      caption={
        <>
          {sites.length} sites · {bondMeshes.length} bonds drawn
          {unpaired > 0 ? ` · ${unpaired} bond strengths without endpoints (not drawn)` : ""}
        </>
      }
    >
      <Canvas camera={{ position: [3, 3, 10], fov: 45 }} dpr={[1, 1.5]} style={{ width: "100%", height: "100%" }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 5, 5]} intensity={0.5} />
        {sites.map((s) => (
          <mesh key={s.index} position={[s.x - centre[0], s.y - centre[1], s.z]}>
            <sphereGeometry args={[0.18, 18, 14]} />
            <meshStandardMaterial color={s.spin === null ? "#94a3b8" : s.spin > 0 ? "#fbbf24" : "#3b82f6"} />
          </mesh>
        ))}
        {bondMeshes.map((b) => (
          <mesh key={b.key} position={[b.position[0] - centre[0], b.position[1] - centre[1], b.position[2]]} rotation={b.rotation}>
            <cylinderGeometry args={[0.045, 0.045, b.length, 8]} />
            <meshStandardMaterial color={b.color} />
          </mesh>
        ))}
        <OrbitControls />
      </Canvas>
    </PanelShell>
  );
}

export default LatticeWithBondColors;
