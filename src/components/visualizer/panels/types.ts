/**
 * Canonical per-domain visualization frame types.
 *
 * One definition per concept for every domain visualizer panel. Two
 * wire shapes exist for the same frames:
 *
 *   - the structured shape (router-branch `cosmic_forge_viz`): labelled
 *     orbitals, Slater determinants, bonds with endpoints, OTOC / A(k, ω)
 *     with axes, plaquettes with cells, labelled shells, ΔL/ΔB/rate;
 *   - the flat shape (agent-branch `cosmic_forge_viz`, also the bundled
 *     `public/fixtures/visualizations/*.json`): bare numeric arrays.
 *
 * Panels consume only the structured types below. `normalizeDomainFrame`
 * (`src/lib/visualizer/domainFrames.ts`) lifts flat frames into them and
 * leaves any quantity the source did not provide as `null` / empty — it
 * never invents values.
 */

export type DomainName =
  | "cosmology"
  | "chemistry"
  | "condmat"
  | "hep"
  | "nuclear"
  | "amo"
  | "gravity"
  | "statmech";

/** Wire name used by `cosmic_forge_viz` routes (`/api/runs/{domain}/…`). */
export type VisualizationDomain = DomainName;

/** Phase tags emitted by either backend; open-ended for forward compatibility. */
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
  | "measure"
  | (string & {});

export interface BaseFrame {
  tau: number;
  phase: ManifestPhase;
  active_terms: string[];
  provenance_ref: string | null;
}

// ─── Cosmology ─────────────────────────────────────────────────────

export interface CosmologyFrame extends BaseFrame {
  domain: "cosmology";
  modes: { k: number[]; omega_re: number[]; omega_im: number[] };
  B_plus: number[];
  B_minus: number[];
  sgwb: number[];
  anomaly: number;
  lepton_flow: number;
}

// ─── Chemistry ─────────────────────────────────────────────────────

export interface ChemistryOrbital {
  index: number;
  occupation: number;
  /** Orbital energy; `null` when the source frame did not carry it. */
  energy_hartree: number | null;
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

export interface ChemistryFrame extends BaseFrame {
  domain: "chemistry";
  iteration: number | null;
  orbitals: ChemistryOrbital[];
  energy_convergence: number[];
  slater_determinants: ChemistrySlater[];
  /** Orbital→orbital flow weights (i, j); empty when not provided. */
  slater_flow: number[][];
  hamiltonian_terms: ChemistryTerm[];
}

// ─── Condensed matter ──────────────────────────────────────────────

export interface CondmatLatticeSite {
  index: number;
  x: number;
  y: number;
  z: number;
  /** Site spin; `null` when not provided. */
  spin: number | null;
}

export interface CondmatBond {
  a: number;
  b: number;
  strength: number;
}

/** `axes: "index"` means the source gave no physical axis values. */
export interface CondmatOtoc {
  times: number[];
  distances: number[];
  intensity: number[][];
  axes: "physical" | "index";
}

export interface CondmatSpectral {
  omega: number[];
  k: number[];
  /** Indexed [k][ω]. */
  Akw: number[][];
  axes: "physical" | "index";
}

export interface CondmatFrame extends BaseFrame {
  domain: "condmat";
  lattice_sites: CondmatLatticeSite[];
  /** Bonds with known endpoints. */
  bond_strengths: CondmatBond[];
  /** Bond strengths whose endpoints the source did not specify. */
  unpaired_bond_strengths: number[];
  otoc_butterfly: CondmatOtoc | null;
  spectral_function_Akw: CondmatSpectral | null;
}

// ─── HEP ───────────────────────────────────────────────────────────

export interface ParticleObservable {
  value: number | null;
  unit: string;
  uncertainty: number | null;
  status: "ok" | "unavailable" | (string & {});
  notes: string;
}

export interface HepPlaquette {
  cell: [number, number, number];
  /** Plaquette flux; `null` when not provided. */
  flux: number | null;
  /** Plaquette action / energy density; `null` when not provided. */
  energy: number | null;
}

export interface HepFrame extends BaseFrame {
  domain: "hep";
  plaquettes: HepPlaquette[];
  chiral_condensate: number;
  string_tension: number;
  particle_obs: Record<string, ParticleObservable>;
}

// ─── Nuclear ───────────────────────────────────────────────────────

export interface NuclearShell {
  shell: string;
  n: number;
  energy_MeV: number | null;
}

export interface NuclearLNV {
  delta_L: number;
  delta_B: number;
  rate: number;
}

export type NuclearModelDomain = "1+1D_toy" | "few_body_3d" | "effective_hamiltonian";

export interface NuclearFrame extends BaseFrame {
  domain: "nuclear";
  shell_occupation: NuclearShell[];
  lnv_tracker: NuclearLNV | null;
  /** Scalar LNV indicator (0 = none, 1 = present); `null` when not provided. */
  lnv_indicator: number | null;
  model_domain: NuclearModelDomain | null;
}

// ─── AMO ───────────────────────────────────────────────────────────

export interface AmoAtom {
  index: number;
  x: number;
  y: number;
  z: number;
  /** Rydberg excitation flag; `null` when not provided. */
  rydberg: boolean | null;
}

export interface AmoBlockade {
  atom: number;
  r_blockade: number;
}

/** Pair correlation g²(r) for listed atom pairs. */
export interface AmoCorrelations {
  pairs: [number, number][];
  g2: number[];
}

export interface AmoFrame extends BaseFrame {
  domain: "amo";
  atom_positions: AmoAtom[];
  blockade_radii: AmoBlockade[];
  /** g² pair correlations; `null` when not provided. */
  correlations: AmoCorrelations | null;
  /** ⟨σᶻᵢ σᶻⱼ⟩ matrix (flat wire shape); empty when not provided. */
  zz_correlations: number[][];
}

// ─── Gravity ───────────────────────────────────────────────────────

export interface GravityFrame extends BaseFrame {
  domain: "gravity";
  spectrum: number[];
  spectral_form_factor: number[];
  is_learned_hamiltonian: boolean;
  provenance_warning: string | null;
  model_domain: "toy_SYK_1+1D" | "JT_matrix_model" | "SYK_sparse";
}

// ─── Statistical mechanics ─────────────────────────────────────────

export interface StatmechFrame extends BaseFrame {
  domain: "statmech";
  estimate: number;
  sigma: number;
  truth: number | null;
  history: number[];
}

export type VisualizationFrame =
  | CosmologyFrame
  | ChemistryFrame
  | CondmatFrame
  | HepFrame
  | NuclearFrame
  | AmoFrame
  | GravityFrame
  | StatmechFrame;

/** Every non-cosmology frame (cosmology uses `src/types/visualizer.ts`). */
export type DomainVisualizationFrame = Exclude<VisualizationFrame, CosmologyFrame>;

// ─── Manifest + timeline envelopes ─────────────────────────────────

export interface ManifestMetadata {
  phases?: string[];
  seed?: number;
  synthetic?: boolean;
  source?: string;
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

/** Envelope the domain visualizer renders. */
export interface DomainTimelineResponse {
  manifest: VisualizationManifest;
  frames: DomainVisualizationFrame[];
}

/** Flat-shape wire envelope (`cosmic_forge_viz` baker / M8 qcompass route). */
export interface VisualizationTimeline {
  run_id: string;
  domain: DomainName;
  schema_version: number;
  frames: VisualizationFrame[];
}
