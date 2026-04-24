/**
 * QCompass — M14 Backend Router (Phase 1 stub).
 *
 * Domain-aware routing per the assessment table in Section 4. Phase 1
 * has exactly one rule: cosmology → cpu-classical. The router is the
 * place where, in Phase 2+, QDMI/QRMI cost-aware routing across
 * simulators and QPUs will live.
 */

import type { DomainId, Manifest } from "@/lib/domains/types";

export type BackendChoice =
  | { kind: "cpu-classical"; reason: string }
  | { kind: "gpu-classical"; reason: string }
  | { kind: "tn-classical"; reason: string }
  | { kind: "qpu-digital"; vendor: string; reason: string }
  | { kind: "qpu-analog"; vendor: string; reason: string }
  | { kind: "unavailable"; reason: string };

const RULES: Partial<Record<DomainId, (manifest: Manifest) => BackendChoice>> = {
  "cosmology.ucglef1": () => ({
    kind: "cpu-classical",
    reason:
      "Smooth ODE + Boltzmann + anomaly integral. No sign problem, no real-time correlator that classical methods cannot deliver.",
  }),
};

export function route(manifest: Manifest): BackendChoice {
  const rule = RULES[manifest.domain];
  if (!rule) {
    return {
      kind: "unavailable",
      reason: `No router rule for ${manifest.domain}; backend deferred to Phase 2.`,
    };
  }
  return rule(manifest);
}
