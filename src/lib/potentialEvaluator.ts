import type { PotentialKind } from "@/types/domain";
import { defaultsForPotential } from "@/lib/configDefaults";

export interface PotentialSample {
  psi: number;
  V: number;
}

/**
 * Sample V(Ψ) for a built-in potential. Returns null for `custom`
 * (the browser never executes user Python; backend will compute).
 *
 * All values are dimensionless / Planck-unit ratios suitable for a chart;
 * Claude Code will replace this with a server-side cached evaluator.
 */
export function samplePotential(
  kind: PotentialKind,
  params: Record<string, number>,
  points = 80,
): PotentialSample[] | null {
  if (kind === "custom") return null;

  const samples: PotentialSample[] = [];
  for (let i = 0; i < points; i++) {
    const t = i / (points - 1);
    const psi = -2 + t * 6; // sweep -2..4 (Planck units)
    samples.push({ psi, V: evalAt(kind, params, psi) });
  }
  return samples;
}

function evalAt(kind: PotentialKind, given: Record<string, number>, psi: number): number {
  // A parameter the form does not hold falls back to the Configurator's
  // default (configDefaults.json, the one source).
  const p = { ...defaultsForPotential(kind), ...given };
  switch (kind) {
    case "starobinsky": {
      const M = p.M;
      // (3/4) M² (1 − e^(−√(2/3) ψ))²
      const f = 1 - Math.exp(-Math.sqrt(2 / 3) * psi);
      return 0.75 * M * M * f * f;
    }
    case "natural": {
      const f = p.f;
      const L4 = p.Lambda4;
      // Λ⁴ (1 + cos(ψ/f_norm))  — normalize ψ so the curve is visible
      const fNorm = f / 1e17;
      return L4 * (1 + Math.cos(psi / Math.max(fNorm, 1e-3)));
    }
    case "hilltop": {
      const mu = p.mu;
      const power = Math.max(2, Math.round(p.p));
      const muNorm = mu / 1e17;
      // V0 (1 − (ψ/μ)^p); V0 is a Configurator parameter (1e-7 is its default).
      const V0 = p.V0;
      return V0 * (1 - Math.pow(psi / Math.max(muNorm, 1e-3), power));
    }
    case "custom":
      return 0;
  }
}
