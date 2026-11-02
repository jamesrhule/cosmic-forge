import type { NuclearFrame, VisualizationManifest } from "@/types/manifest";
import { ShellOccupation } from "@/components/visualizer/panels/nuclear/ShellOccupation";
import { LNVTracker } from "@/components/visualizer/panels/nuclear/LNVTracker";
import { ModelDomainBadge } from "@/components/visualizer/panels/nuclear/ModelDomainBadge";

export interface NuclearDomainLayoutProps {
  manifest: VisualizationManifest;
  frame: NuclearFrame | null;
  frames: NuclearFrame[];
}

export function NuclearDomainLayout({ frame, frames }: NuclearDomainLayoutProps) {
  return (
    <>
      <div className="md:col-span-2">
        <ModelDomainBadge frame={frame} />
      </div>
      <ShellOccupation frame={frame} />
      <LNVTracker frames={frames} frame={frame} />
    </>
  );
}
