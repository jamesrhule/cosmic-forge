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

export const DEFAULT_CUSTOM_PYTHON = `# Custom inflaton potential V(psi).
# Must define a function V(psi) returning a float in Planck units.
# Pure Python (no imports). The backend AST-checks this snippet.
def V(psi):
    M = 1.3e-5
    return 0.75 * M**2 * (1.0 - 2.718281828 ** (-0.8164965809 * psi)) ** 2
`;

/**
 * The V2 Kawai-Kim baseline. Used by "Restore V2 defaults" and as the
 * initial form value. These are the Configurator's own V2 values (f = 7e16 GeV,
 * i.e. f_a ≈ 0.029 M_Pl), not the paper's benchmark (f_a = 8.7 M_Pl, JAMES
 * DECISION 11); changing them is an R19 change (LEDGER, W1-PARAMS:
 * BLOCKED-ON-JAMES:ui-v2-defaults-vs-paper-benchmark).
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
