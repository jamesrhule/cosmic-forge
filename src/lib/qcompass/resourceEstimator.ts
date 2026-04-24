/**
 * QCompass — M12 Resource Estimator (Phase 1 stub).
 *
 * Azure-QRE-shaped result type. Cosmology returns "classical" with a
 * note; quantum domains will plug in real estimators (Azure QRE,
 * QREChem, TFermion) in Phase 2. The architect's posture: NEVER submit
 * a workload to a QPU without running this first.
 */

import type { Manifest, ResourceEstimate } from "@/lib/domains/types";

export interface ResourceEstimator {
  estimate(manifest: Manifest): Promise<ResourceEstimate>;
}

const cosmologyEstimator: ResourceEstimator = {
  async estimate(_manifest: Manifest): Promise<ResourceEstimate> {
    return {
      kind: "classical",
      note: "ODE + Boltzmann + anomaly integral — solved at machine precision on CPU. No QPU resources required.",
    };
  },
};

const ESTIMATORS: Partial<Record<Manifest["domain"], ResourceEstimator>> = {
  "cosmology.ucglef1": cosmologyEstimator,
};

export async function estimateResources(manifest: Manifest): Promise<ResourceEstimate> {
  const estimator = ESTIMATORS[manifest.domain];
  if (!estimator) {
    return {
      kind: "classical",
      note: `No estimator registered for ${manifest.domain}; defaulting to classical/no-op.`,
    };
  }
  return estimator.estimate(manifest);
}
