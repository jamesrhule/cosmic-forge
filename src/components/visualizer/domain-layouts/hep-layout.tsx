import type { HepFrame, VisualizationManifest } from "@/types/manifest";
import { GaugePlaquettes } from "@/components/visualizer/panels/hep/GaugePlaquettes";
import { ChiralCondensateTrace } from "@/components/visualizer/panels/hep/ChiralCondensateTrace";
import { StringBreakingAnim } from "@/components/visualizer/panels/hep/StringBreakingAnim";
import { ParticleObservablesTable } from "@/components/visualizer/panels/hep/ParticleObservablesTable";
import { PanelShell } from "@/components/visualizer/panels/PanelShell";

export interface HepDomainLayoutProps {
  manifest: VisualizationManifest;
  frame: HepFrame | null;
  frames: HepFrame[];
}

export function HepDomainLayout({ frame, frames }: HepDomainLayoutProps) {
  return (
    <>
      <GaugePlaquettes frame={frame} />
      <ChiralCondensateTrace frames={frames} currentTau={frame?.tau} />
      <StringBreakingAnim frame={frame} frames={frames} />
      <PanelShell title="Particle observables" bodyClassName="overflow-auto p-3">
        <ParticleObservablesTable frame={frame} />
      </PanelShell>
    </>
  );
}
