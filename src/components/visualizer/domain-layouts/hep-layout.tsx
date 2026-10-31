import type {
  DomainTimelineResponse,
  HepFrame,
  VisualizationManifest,
} from "@/types/manifest";
import { GaugePlaquettes } from "@/components/visualizer/panels/hep/GaugePlaquettes";
import { ChiralCondensateTrace } from "@/components/visualizer/panels/hep/ChiralCondensateTrace";
import { StringBreakingAnim } from "@/components/visualizer/panels/hep/StringBreakingAnim";

export interface HepDomainLayoutProps {
  manifest: VisualizationManifest;
  frame: HepFrame | null;
  timeline: DomainTimelineResponse;
}

export function HepDomainLayout({ frame, timeline }: HepDomainLayoutProps) {
  return (
    <>
      <GaugePlaquettes frame={frame} />
      <ChiralCondensateTrace timeline={timeline} />
      <div className="md:col-span-2">
        <StringBreakingAnim frame={frame} />
      </div>
    </>
  );
}
