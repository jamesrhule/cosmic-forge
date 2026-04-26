import { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type { ChemistryFrame } from "@/types/manifest";

export interface OrbitalOccupation3DProps {
  frame: ChemistryFrame | null;
}

/**
 * Orbital-grid stand-in: each orbital becomes a sphere whose radius is
 * driven by the occupation number and colour by orbital energy. A
 * `3dmol`-backed isosurface view is the future enhancement, dynamic-
 * imported from the panel; for now the sphere grid is the always-
 * available baseline.
 */
export function OrbitalOccupation3D({ frame }: OrbitalOccupation3DProps) {
  const orbitals = frame?.orbitals ?? [];

  const items = useMemo(() => {
    if (orbitals.length === 0) return [];
    const minE = Math.min(...orbitals.map((o) => o.energy_hartree));
    const maxE = Math.max(...orbitals.map((o) => o.energy_hartree));
    const span = Math.max(1e-9, maxE - minE);
    return orbitals.map((o, i) => {
      const t = (o.energy_hartree - minE) / span;
      const r = Math.sqrt(Math.max(0.05, o.occupation)) * 0.55;
      const x = (i % 4) * 1.6 - 2.4;
      const y = Math.floor(i / 4) * 1.6 - 1.6;
      // hue: low energy = blue, high = red.
      const hue = (1 - t) * 0.66; // 0=red, 0.66=blue
      const color = hslToHex(hue, 0.6, 0.55);
      return { id: o.index, x, y, r, color, occ: o.occupation, e: o.energy_hartree };
    });
  }, [orbitals]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        Orbital occupation
      </div>
      <div className="min-h-0 flex-1">
        {items.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
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
        )}
      </div>
    </div>
  );
}

function hslToHex(h: number, s: number, l: number): string {
  const f = (n: number) => {
    const k = (n + h * 12) % 12;
    const a = s * Math.min(l, 1 - l);
    const x = l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
    return Math.round(255 * x);
  };
  const r = f(0);
  const g = f(8);
  const b = f(4);
  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}
