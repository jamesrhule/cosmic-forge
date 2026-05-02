/**
 * Model-domain caveat badge for nuclear runs.
 *
 * Surfaces the run's model_domain tag so the audit reviewer
 * sees the right caveat banner:
 *   - "1+1D toy"             → Chernyshev et al. 2026 toy.
 *   - "few-body 3D"          → NCSM matrix elements.
 *   - "effective Hamiltonian" → hypothetical-particle search.
 */

import type { NuclearFrame } from "../types";

const _LABELS: Record<NuclearFrame["model_domain"], string> = {
  "1+1D_toy": "1+1D toy (qualitative)",
  "few_body_3d": "few-body 3D (NCSM)",
  "effective_hamiltonian": "effective Hamiltonian (hypothetical-particle)",
};

const _COLORS: Record<NuclearFrame["model_domain"], string> = {
  "1+1D_toy": "hsl(45 90% 50%)",
  "few_body_3d": "hsl(220 60% 50%)",
  "effective_hamiltonian": "hsl(280 60% 55%)",
};

interface Props {
  frame: NuclearFrame | undefined;
}

export function ModelDomainBadge({ frame }: Props) {
  if (!frame) return null;
  const label = _LABELS[frame.model_domain] ?? frame.model_domain;
  const colour = _COLORS[frame.model_domain] ?? "hsl(220 10% 50%)";
  return (
    <div
      className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs"
      style={{ borderColor: colour, borderWidth: 1, color: colour }}
      role="status"
    >
      <span
        className="inline-block w-2 h-2 rounded-full"
        style={{ background: colour }}
      />
      <span>model_domain: {label}</span>
    </div>
  );
}

export default ModelDomainBadge;
