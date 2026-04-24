/**
 * QCompass — M11 Hamiltonian Registry (Phase 1: schema-only).
 *
 * Canonical problem-instance formats per domain. Phase 1 registers
 * exactly one format (`cosmology_runconfig`) so the existing UCGLE-F1
 * `RunConfig` can be addressed through the same registry as future
 * FCIDUMP / lattice-HDF5 instances.
 *
 * No Hamiltonian instances are stored in Phase 1 — this is the
 * interface the eventual M11 service will speak.
 */

import type { DomainId } from "@/lib/domains/types";

export type HamiltonianFormat =
  | "cosmology_runconfig"
  | "fcidump"
  | "lqcd_hdf5"
  | "spin_hamiltonian_json"
  | "majorana_sparse"
  | "ncsm_tbme";

export interface HamiltonianFormatDescriptor {
  format: HamiltonianFormat;
  domains: DomainId[];
  description: string;
  /** Reference / spec URL when one exists. */
  spec?: string;
}

const FORMATS: HamiltonianFormatDescriptor[] = [
  {
    format: "cosmology_runconfig",
    domains: ["cosmology.ucglef1"],
    description:
      "UCGLE-F1 RunConfig payload (potential, GB/CS couplings, seesaw, reheating).",
  },
  {
    format: "fcidump",
    domains: ["chemistry.molecular"],
    description: "Standard 1- and 2-electron integral dump used by chemistry codes.",
    spec: "https://doi.org/10.1016/0010-4655(89)90033-7",
  },
  {
    format: "lqcd_hdf5",
    domains: ["hep.lattice"],
    description: "IQuS-compatible HDF5 layout for staggered/Wilson fermions.",
  },
  {
    format: "spin_hamiltonian_json",
    domains: ["condmat.lattice", "amo.rydberg"],
    description: "Lattice + coupling tensor JSON for spin/Hubbard models.",
  },
  {
    format: "majorana_sparse",
    domains: ["gravity.syk"],
    description:
      "Sparse Majorana coupling tensor; LEARNED Hamiltonians MUST be flagged in provenance.",
  },
  {
    format: "ncsm_tbme",
    domains: ["nuclear.structure"],
    description: "No-core shell model two-body matrix elements.",
  },
];

export function listHamiltonianFormats(): readonly HamiltonianFormatDescriptor[] {
  return FORMATS;
}

export function formatsForDomain(id: DomainId): HamiltonianFormatDescriptor[] {
  return FORMATS.filter((f) => f.domains.includes(id));
}
