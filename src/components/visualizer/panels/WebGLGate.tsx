import type { ReactNode } from "react";
import { useWebGLAvailable } from "@/lib/webgl";
import { EmptyPanel } from "@/components/visualizer/empty-panel";

/**
 * Renders its children (an R3F `<Canvas>`) only when WebGL is available.
 * Otherwise it says so plainly instead of letting three.js throw.
 */
export function WebGLGate({ title, children }: { title: string; children: ReactNode }) {
  const ok = useWebGLAvailable();
  if (ok === null) return null;
  if (!ok) {
    return (
      <EmptyPanel
        dense
        title={title}
        reason="This 3D view needs WebGL, which this browser has disabled or doesn't support. The other panels show the same frame data."
      />
    );
  }
  return <>{children}</>;
}
