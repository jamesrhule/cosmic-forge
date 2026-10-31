import { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { CondmatFrame } from "@/types/manifest";

export interface LatticeWithBondColorsProps {
  frame: CondmatFrame | null;
}

export function LatticeWithBondColors({ frame }: LatticeWithBondColorsProps) {
  const sites = frame?.lattice_sites ?? [];
  const bonds = frame?.bond_strengths ?? [];

  const bondMeshes = useMemo(() => {
    if (sites.length === 0 || bonds.length === 0) return [];
    const byIndex = new Map(sites.map((s) => [s.index, s]));
    const minS = Math.min(...bonds.map((b) => b.strength));
    const maxS = Math.max(...bonds.map((b) => b.strength));
    const span = Math.max(1e-9, maxS - minS);
    return bonds
      .map((b) => {
        const a = byIndex.get(b.a);
        const c = byIndex.get(b.b);
        if (!a || !c) return null;
        const ax = a.x;
        const ay = a.y;
        const az = a.z;
        const bx = c.x;
        const by = c.y;
        const bz = c.z;
        const mid = [(ax + bx) / 2, (ay + by) / 2, (az + bz) / 2] as const;
        const dx = bx - ax;
        const dy = by - ay;
        const dz = bz - az;
        const len = Math.sqrt(dx * dx + dy * dy + dz * dz);
        const t = (b.strength - minS) / span;
        const hue = 0.66 - 0.66 * t; // blue (weak) → red (strong)
        const color = new THREE.Color().setHSL(hue, 0.7, 0.55);
        const dir = new THREE.Vector3(dx, dy, dz).normalize();
        const up = new THREE.Vector3(0, 1, 0);
        const quaternion = new THREE.Quaternion().setFromUnitVectors(up, dir);
        const euler = new THREE.Euler().setFromQuaternion(quaternion);
        return {
          key: `${b.a}-${b.b}`,
          position: mid,
          rotation: [euler.x, euler.y, euler.z] as const,
          length: len,
          color: `#${color.getHexString()}`,
        };
      })
      .filter(Boolean) as Array<{
      key: string;
      position: readonly [number, number, number];
      rotation: readonly [number, number, number];
      length: number;
      color: string;
    }>;
  }, [sites, bonds]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        Lattice + bond strengths
      </div>
      <div className="min-h-0 flex-1">
        {sites.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
          <Canvas
            camera={{ position: [3, 3, 8], fov: 45 }}
            dpr={[1, 1.5]}
            style={{ width: "100%", height: "100%" }}
          >
            <ambientLight intensity={0.6} />
            <directionalLight position={[5, 5, 5]} intensity={0.5} />
            {sites.map((s) => (
              <mesh key={s.index} position={[s.x - 2.5, s.y - 2.5, s.z]}>
                <sphereGeometry args={[0.18, 18, 14]} />
                <meshStandardMaterial color={s.spin > 0 ? "#fbbf24" : "#3b82f6"} />
              </mesh>
            ))}
            {bondMeshes.map((b) => (
              <mesh
                key={b.key}
                position={[b.position[0] - 2.5, b.position[1] - 2.5, b.position[2]]}
                rotation={[b.rotation[0], b.rotation[1], b.rotation[2]]}
              >
                <cylinderGeometry args={[0.045, 0.045, b.length, 8]} />
                <meshStandardMaterial color={b.color} />
              </mesh>
            ))}
            <OrbitControls />
          </Canvas>
        )}
      </div>
    </div>
  );
}
