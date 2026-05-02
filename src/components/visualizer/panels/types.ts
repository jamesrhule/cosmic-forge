/**
 * Shared TypeScript types for the per-domain visualization panels
 * (PROMPT 7 v2 §PART C). Mirrors `cosmic_forge_viz.schema` —
 * keep these in sync with the Python Pydantic models when frame
 * shapes change.
 */

export type DomainName =
  | "cosmology"
  | "chemistry"
  | "condmat"
  | "hep"
  | "nuclear"
  | "amo";

export interface BaseFrame {
  tau: number;
  phase: string;
  active_terms: string[];
  provenance_ref: string | null;
}

export interface CosmologyFrame extends BaseFrame {
  domain: "cosmology";
  modes: { k: number[]; omega_re: number[]; omega_im: number[] };
  B_plus: number[];
  B_minus: number[];
  sgwb: number[];
  anomaly: number;
  lepton_flow: number;
}

export interface ChemistryFrame extends BaseFrame {
  domain: "chemistry";
  orbitals: number[];
  energy_convergence: number[];
  slater: number[][];
}

export interface CondmatFrame extends BaseFrame {
  domain: "condmat";
  lattice_sites: number[][];
  bond_strengths: number[];
  otoc: number[][];
  spectral: number[][];
}

export interface ParticleObservable {
  value: number | null;
  unit: string;
  uncertainty: number | null;
  status: "ok" | "unavailable" | string;
  notes: string;
}

export interface HepFrame extends BaseFrame {
  domain: "hep";
  plaquettes: number[];
  chiral_condensate: number;
  string_tension: number;
  particle_obs: Record<string, ParticleObservable>;
}

export interface NuclearFrame extends BaseFrame {
  domain: "nuclear";
  shell_occupation: number[];
  lnv_tracker: number;
  model_domain: "1+1D_toy" | "few_body_3d" | "effective_hamiltonian";
}

export interface AmoFrame extends BaseFrame {
  domain: "amo";
  atom_positions: number[][];
  blockade_radii: number[];
  correlations: number[][];
}

export type VisualizationFrame =
  | CosmologyFrame
  | ChemistryFrame
  | CondmatFrame
  | HepFrame
  | NuclearFrame
  | AmoFrame;

export interface VisualizationTimeline {
  run_id: string;
  domain: DomainName;
  schema_version: number;
  frames: VisualizationFrame[];
}
