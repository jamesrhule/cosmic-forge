import type { PotentialKind, Precision, RunConfig } from "@/types/domain";
import defaults from "./configDefaults.json";

/**
 * Sensible per-potential defaults for the Configurator, in the API's units
 * (backend `ucgle_f1.domain.POTENTIAL_PARAM_FORMS`; the backend converts them
 * to reduced-Planck units, JAMES DECISION 11): starobinsky M [M_Pl]; natural
 * f [GeV], Lambda4 [M_Pl⁴]; hilltop V0 [M_Pl⁴], mu [GeV], p (integer).
 *
 * The values live in `configDefaults.json`, which the backend test
 * `backend/tests/test_frontend_potential_configs.py` reads too, so every
 * default the Configurator can send is checked against the API (one source).
 */
export function defaultsForPotential(kind: PotentialKind): Record<string, number> {
  return { ...defaults.potentialParams[kind] };
}

/**
 * The custom potential's default snippet, in the canonical shape (JAMES
 * DECISION 17): one sympy expression in phi, in reduced-Planck units. It is
 * the potential main's default `def V(psi)` computed (Starobinsky with
 * M = 1.3e-5), literal for literal. The backend parses it with Python's `ast`
 * and builds it with sympy (`ucgle_f1.m2_scalar.potentials`); comments are
 * ignored.
 */
export const DEFAULT_CUSTOM_PYTHON = `# Custom inflaton potential V(phi): one sympy expression in phi.
# Reduced-Planck units (M_Pl = 1). Calls: sqrt log exp sin cos tanh cosh sinh.
0.75 * (1.3e-5)**2 * (1.0 - 2.718281828 ** (-0.8164965809 * phi)) ** 2
`;

/**
 * The V2 Kawai-Kim baseline. Used by "Restore V2 defaults" and as the
 * initial form value. Its natural potential is the paper's benchmark in the
 * Configurator's units (JAMES DECISION 15): f = 8.7 M_Pl = 2.118624e19 GeV
 * (8.7 × `M_PL_GEV`) and Λ⁴ = 2.563334027300118e-9 M_Pl⁴, which the backend
 * converts back to f_a = 8.7 and Λ = 0.0071154324599829784 M_Pl (Decision 11:
 * Λ fixed by A_s = 2.207e-9 at N_e = 60). The couplings are UCGLE-F1's own.
 */
export function kawaiKimDefaults(): RunConfig {
  return {
    potential: {
      kind: "natural",
      params: defaultsForPotential("natural"),
    },
    couplings: { ...defaults.v2.couplings },
    reheating: { ...defaults.v2.reheating },
    precision: defaults.v2.precision as Precision,
  };
}
