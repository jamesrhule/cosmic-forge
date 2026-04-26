/**
 * Visualization manifest — frontend mirror of
 * `cosmic_forge_viz.schema.VisualizationManifest`.
 *
 * Field names + casing are part of the wire contract; do not rename
 * without changing the Pydantic model in lockstep.
 */

export type VisualizationDomain =
  | "cosmology"
  | "chemistry"
  | "condmat"
  | "hep"
  | "nuclear"
  | "amo";

/** Coarse-grained phase tags shared across domains. */
export type ManifestPhase =
  | "inflation"
  | "gb_window"
  | "reheating"
  | "radiation"
  | "sphaleron"
  | "warmup"
  | "scf"
  | "post_scf"
  | "thermalize"
  | "quench"
  | "equilibrium"
  | "vacuum"
  | "string_break"
  | "ground"
  | "decay"
  | "load"
  | "rydberg"
  | "measure";

export interface ManifestMetadata {
  phases?: string[];
  seed?: number;
  synthetic?: boolean;
  [key: string]: unknown;
}

export interface VisualizationManifest {
  run_id: string;
  domain: VisualizationDomain;
  frame_count: number;
  formula_variant: string | null;
  bake_uri: string | null;
  metadata: ManifestMetadata;
}

export interface BaseVisualizationFrame {
  tau: number;
  phase: ManifestPhase;
  active_terms: string[];
  provenance_ref: string | null;
  domain: VisualizationDomain;
}

export interface ChemistryOrbital {
  index: number;
  energy_hartree: number;
  occupation: number;
  coefficients: number[];
}

export interface ChemistrySlater {
  label: string;
  weight: number;
  occupations: number[];
}

export interface ChemistryTerm {
  label: string;
  coefficient: number;
  operator: string;
}

export interface ChemistryFrame extends BaseVisualizationFrame {
  domain: "chemistry";
  iteration: number;
  orbitals: ChemistryOrbital[];
  energy_convergence: number[];
  slater_determinants: ChemistrySlater[];
  hamiltonian_terms: ChemistryTerm[];
}

export interface CondmatLatticeSite {
  index: number;
  x: number;
  y: number;
  z: number;
  spin: number;
}

export interface CondmatBond {
  a: number;
  b: number;
  strength: number;
}

export interface CondmatOtoc {
  times: number[];
  distances: number[];
  intensity: number[][];
}

export interface CondmatSpectral {
  omega: number[];
  k: number[];
  Akw: number[][];
}

export interface CondmatFrame extends BaseVisualizationFrame {
  domain: "condmat";
  lattice_sites: CondmatLatticeSite[];
  bond_strengths: CondmatBond[];
  otoc_butterfly: CondmatOtoc | null;
  spectral_function_Akw: CondmatSpectral | null;
}

export interface HepPlaquette {
  cell: [number, number, number];
  flux: number;
  energy: number;
}

export interface HepFrame extends BaseVisualizationFrame {
  domain: "hep";
  plaquettes: HepPlaquette[];
  chiral_condensate: number;
  string_tension: number;
}

export interface NuclearShell {
  shell: string;
  n: number;
  energy_MeV: number;
}

export interface NuclearLNV {
  delta_L: number;
  delta_B: number;
  rate: number;
}

export interface NuclearFrame extends BaseVisualizationFrame {
  domain: "nuclear";
  shell_occupation: NuclearShell[];
  lnv_tracker: NuclearLNV | null;
}

export interface AmoAtom {
  index: number;
  x: number;
  y: number;
  z: number;
  rydberg: boolean;
}

export interface AmoBlockade {
  atom: number;
  r_blockade: number;
}

export interface AmoCorrelations {
  pairs: [number, number][];
  g2: number[];
}

export interface AmoFrame extends BaseVisualizationFrame {
  domain: "amo";
  atom_positions: AmoAtom[];
  blockade_radii: AmoBlockade[];
  correlations: AmoCorrelations | null;
}

/**
 * Cosmology frames travel through the existing `BakedVisualizationTimeline`
 * contract in `src/types/visualizer.ts`. The domain route narrows them
 * via the manifest's `domain` field rather than via a separate frame
 * type here.
 */
export type DomainVisualizationFrame =
  | ChemistryFrame
  | CondmatFrame
  | HepFrame
  | NuclearFrame
  | AmoFrame;

export interface DomainTimelineResponse {
  manifest: VisualizationManifest;
  frames: DomainVisualizationFrame[];
}
