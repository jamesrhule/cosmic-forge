import type { AmoFrame, VisualizationManifest } from "@/types/manifest";
import { AtomArray3D } from "@/components/visualizer/panels/amo/AtomArray3D";
import { BlockadeCorrelations } from "@/components/visualizer/panels/amo/BlockadeCorrelations";

export interface AmoDomainLayoutProps {
  manifest: VisualizationManifest;
  frame: AmoFrame | null;
}

export function AmoDomainLayout({ frame }: AmoDomainLayoutProps) {
  return (
    <>
      <AtomArray3D frame={frame} />
      <BlockadeCorrelations frame={frame} />
    </>
  );
}
