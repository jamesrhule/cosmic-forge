import type { PotentialKind, RunConfig } from "@/types/domain";

/**
 * Sensible per-potential defaults for the Configurator. Backend will
 * eventually own canonical defaults; for the shell these mirror the
 * Kawai-Kim and Starobinsky benchmark fixtures.
 */
export function defaultsForPotential(
  kind: PotentialKind,
): Record<string, number> {
  switch (kind) {
    case "starobinsky":
      return { M: 1.3e-5 };
    case "natural":
      return { f: 7e16, Lambda4: 2.5e-7 };
    case "hilltop":
      return { mu: 1e16, p: 4 };
    case "custom":
      return {};
  }
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
 * initial form value.
 */
export function kawaiKimDefaults(): RunConfig {
  return {
    potential: {
      kind: "natural",
      params: { f: 7e16, Lambda4: 2.5e-7 },
    },
    couplings: {
      xi: 0.0085,
      theta_grav: 0.78,
      f_a: 1e16,
      M_star: 2.4e18,
      M1: 1e10,
      S_E2: 0.046,
    },
    reheating: {
      Gamma_phi: 1e8,
      T_reh_GeV: 1.5e9,
    },
    precision: "standard",
  };
}
