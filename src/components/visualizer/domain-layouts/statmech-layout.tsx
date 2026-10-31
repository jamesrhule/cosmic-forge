import type { StatmechFrame, VisualizationManifest } from "@/types/manifest";
import { EstimatorTrace } from "@/components/visualizer/panels/statmech/EstimatorTrace";
import { PanelShell } from "@/components/visualizer/panels/PanelShell";

export interface StatmechDomainLayoutProps {
  manifest: VisualizationManifest;
  frame: StatmechFrame | null;
  frames: StatmechFrame[];
}

export function StatmechDomainLayout({ frame }: StatmechDomainLayoutProps) {
  return (
    <div className="md:col-span-2">
      <PanelShell title="Estimator trace" bodyClassName="overflow-auto p-3">
        <EstimatorTrace frame={frame} />
      </PanelShell>
    </div>
  );
}
