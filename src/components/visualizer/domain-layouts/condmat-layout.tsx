import type { CondmatFrame, VisualizationManifest } from "@/types/manifest";
import { LatticeWithBondColors } from "@/components/visualizer/panels/condmat/LatticeWithBondColors";
import { OtocButterflyCone } from "@/components/visualizer/panels/condmat/OtocButterflyCone";
import { SpectralHeatmap } from "@/components/visualizer/panels/condmat/SpectralHeatmap";

export interface CondmatDomainLayoutProps {
  manifest: VisualizationManifest;
  frame: CondmatFrame | null;
}

export function CondmatDomainLayout({ frame }: CondmatDomainLayoutProps) {
  return (
    <>
      <LatticeWithBondColors frame={frame} />
      <OtocButterflyCone frame={frame} />
      <div className="md:col-span-2">
        <SpectralHeatmap frame={frame} />
      </div>
    </>
  );
}
