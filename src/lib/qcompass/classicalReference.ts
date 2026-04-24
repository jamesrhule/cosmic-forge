/**
 * QCompass — M13 Classical Reference (Phase 1 stub).
 *
 * For every quantum-derived claim in Phase 2+, a classical reference
 * MUST be computed on the same problem instance before the result is
 * accepted into any audit pipeline. Cosmology trivially satisfies this
 * by being its own reference.
 */

import type { Manifest } from "@/lib/domains/types";

export interface ClassicalReference {
  method: string;
  summary: string;
  artifactPath?: string;
}

const COSMOLOGY_SELF_REFERENCE: ClassicalReference = {
  method: "ucglef1.friedmann_boltzmann_anomaly",
  summary:
    "UCGLE-F1 cosmology is its own classical reference — the Friedmann ODE + tensor-mode hierarchy + Boltzmann + anomaly integral pipeline runs at machine precision on CPU.",
};

export async function getClassicalReference(
  manifest: Manifest,
): Promise<ClassicalReference | null> {
  if (manifest.domain === "cosmology.ucglef1") return COSMOLOGY_SELF_REFERENCE;
  // Phase 2: dispatch to PySCF / Quimb / pyblock2 / IQuS adapters.
  return null;
}
