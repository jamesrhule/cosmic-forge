import type { PotentialKind } from "@/types/domain";

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

function evalAt(
  kind: PotentialKind,
  p: Record<string, number>,
  psi: number,
): number {
  switch (kind) {
    case "starobinsky": {
      const M = p.M ?? 1.3e-5;
      // (3/4) M² (1 − e^(−√(2/3) ψ))²
      const f = 1 - Math.exp(-Math.sqrt(2 / 3) * psi);
      return 0.75 * M * M * f * f;
    }
    case "natural": {
      const f = p.f ?? 7e16;
      const L4 = p.Lambda4 ?? 2.5e-7;
      // Λ⁴ (1 + cos(ψ/f_norm))  — normalize ψ so the curve is visible
      const fNorm = f / 1e17;
      return L4 * (1 + Math.cos(psi / Math.max(fNorm, 1e-3)));
    }
    case "hilltop": {
      const mu = p.mu ?? 1e16;
      const power = Math.max(2, Math.round(p.p ?? 4));
      const muNorm = mu / 1e17;
      // V0 (1 − (ψ/μ)^p)
      const V0 = 1e-7;
      return V0 * (1 - Math.pow(psi / Math.max(muNorm, 1e-3), power));
    }
    case "custom":
      return 0;
  }
}
