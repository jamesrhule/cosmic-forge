import type { PotentialKind } from "@/types/domain";
import { defaultsForPotential, M_PL_GEV } from "@/lib/configDefaults";

export interface PotentialSample {
  psi: number;
  V: number;
}

/**
 * Sample V(Ψ) for a built-in potential. Returns null for `custom`
 * (the browser never executes user Python; backend will compute).
 *
 * The preview draws the potential the run uses: M2's expressions
 * (`ucgle_f1.m2_scalar.potentials.compile_potential`), with the API's
 * parameters converted the way `Potential.engine()` converts them (GeV ÷
 * `M_PL_GEV`, the engine's M_Pl). Ψ is in M_Pl and V in M_Pl⁴.
 * `potentialEvaluator.test.ts` checks it against V values M2 computed
 * (`scripts/gen_potential_vectors.py`).
 *
 * It is a display aid for the Configurator, not a result: R6's "every
 * physical number from the engine" is met when previews come from the API,
 * which P4-04's accuracy test ("no physical value is computed in the
 * browser") requires.
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
      // Λ⁴ (1 − cos(ψ/f_a)), M2's sign. The Configurator sends f [GeV] and
      // Λ⁴ [M_Pl⁴] (f_a = f / M_Pl); a config in M2's own names (f_a, Λ in
      // M_Pl, e.g. the Kawai–Kim fixture) is used as it is, as the engine does.
      const m2Names = "f_a" in given && "Lambda" in given;
      const fA = m2Names ? given.f_a : p.f / M_PL_GEV;
      const L4 = m2Names ? given.Lambda ** 4 : p.Lambda4;
      return L4 * (1 - Math.cos(psi / fA));
    }
    case "hilltop": {
      // V0 (1 − (ψ/μ)^p), μ = mu [GeV] / M_Pl; p is an integer (default 4).
      const mu = p.mu / M_PL_GEV;
      const power = Math.max(2, Math.round(p.p));
      return p.V0 * (1 - Math.pow(psi / mu, power));
    }
    case "custom":
      return 0;
  }
}
