import type {
  DomainTimelineResponse,
  NuclearFrame,
  VisualizationManifest,
} from "@/types/manifest";
import { ShellOccupation } from "@/components/visualizer/panels/nuclear/ShellOccupation";
import { LNVTracker } from "@/components/visualizer/panels/nuclear/LNVTracker";

export interface NuclearDomainLayoutProps {
  manifest: VisualizationManifest;
  frame: NuclearFrame | null;
  timeline: DomainTimelineResponse;
}

export function NuclearDomainLayout({ frame, timeline }: NuclearDomainLayoutProps) {
  return (
    <>
      <ShellOccupation frame={frame} />
      <LNVTracker timeline={timeline} frame={frame} />
    </>
  );
}
