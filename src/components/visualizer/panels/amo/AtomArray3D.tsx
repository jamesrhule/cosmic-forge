import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type { AmoFrame } from "@/types/manifest";

export interface AtomArray3DProps {
  frame: AmoFrame | null;
}

export function AtomArray3D({ frame }: AtomArray3DProps) {
  const positions = frame?.atom_positions ?? [];

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        Neutral-atom array
      </div>
      <div className="min-h-0 flex-1">
        {positions.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
          <Canvas
            camera={{ position: [10, 8, 18], fov: 45 }}
            dpr={[1, 1.5]}
            style={{ width: "100%", height: "100%" }}
          >
            <ambientLight intensity={0.55} />
            <directionalLight position={[10, 10, 10]} intensity={0.6} />
            {positions.map((p) => (
              <mesh
                key={p.index}
                position={[p.x - 7.5, p.y - 7.5, p.z]}
              >
                <sphereGeometry args={[0.55, 18, 14]} />
                <meshStandardMaterial
                  color={p.rydberg ? "#f97316" : "#60a5fa"}
                  emissive={p.rydberg ? "#f97316" : "#000000"}
                  emissiveIntensity={p.rydberg ? 0.8 : 0}
                  roughness={0.4}
                />
              </mesh>
            ))}
            <OrbitControls />
          </Canvas>
        )}
      </div>
    </div>
  );
}
