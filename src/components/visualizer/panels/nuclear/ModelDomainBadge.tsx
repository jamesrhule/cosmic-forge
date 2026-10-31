/**
 * Nuclear model-domain caveat for the domain visualizer.
 *
 * Adapter over the app-wide `@/components/ModelDomainBadge` (one badge
 * per concept, R20) that adds the human-readable caveat the agent-branch
 * panel carried. Renders nothing when the frame has no model_domain.
 */
import { ModelDomainBadge as Badge } from "@/components/ModelDomainBadge";
import type { NuclearFrame, NuclearModelDomain } from "../types";

const CAVEAT: Record<NuclearModelDomain, string> = {
  "1+1D_toy": "1+1D toy (qualitative)",
  few_body_3d: "few-body 3D (NCSM)",
  effective_hamiltonian: "effective Hamiltonian (hypothetical-particle)",
};

export interface NuclearModelDomainBadgeProps {
  frame: NuclearFrame | null;
}

export function ModelDomainBadge({ frame }: NuclearModelDomainBadgeProps) {
  const value = frame?.model_domain ?? null;
  if (!value) return null;
  return (
    <div className="flex items-center gap-2" role="status">
      <Badge value={value} />
      <span className="text-[11px] text-muted-foreground">{CAVEAT[value]}</span>
    </div>
  );
}

export default ModelDomainBadge;
