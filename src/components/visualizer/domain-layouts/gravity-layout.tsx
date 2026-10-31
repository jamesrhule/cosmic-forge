import type { GravityFrame, VisualizationManifest } from "@/types/manifest";
import { ProvenanceWarningBanner } from "@/components/visualizer/panels/gravity/ProvenanceWarningBanner";
import { SpectralFormFactor } from "@/components/visualizer/panels/gravity/SpectralFormFactor";
import { PanelShell } from "@/components/visualizer/panels/PanelShell";

export interface GravityDomainLayoutProps {
  manifest: VisualizationManifest;
  frame: GravityFrame | null;
  frames: GravityFrame[];
}

/** R18: the provenance guard wraps every gravity panel. */
export function GravityDomainLayout({ frame, frames }: GravityDomainLayoutProps) {
  return (
    <div className="space-y-3 md:col-span-2">
      <ProvenanceWarningBanner frames={frames}>
        <PanelShell title="Spectral form factor g(t)" bodyClassName="overflow-auto p-3">
          <SpectralFormFactor frame={frame} />
        </PanelShell>
      </ProvenanceWarningBanner>
    </div>
  );
}
