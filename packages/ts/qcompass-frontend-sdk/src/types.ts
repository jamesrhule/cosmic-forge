/**
 * Mirror of the qcompass_core / qfull-* / cosmic_forge_viz Pydantic
 * models used by the frontend SDK (PROMPT 8 v2 §C).
 *
 * NOTE: this file would normally be generated from the Pydantic
 * schemas via `datamodel-code-generator >= 0.26`. The sandbox
 * can't run the generator (no node + no pip install), so the
 * types are hand-aligned. Whenever the Python schemas change, run
 * the generator (see ../README.md) and replace this file's body
 * verbatim. Field ordering matches the Pydantic JSON-schema
 * output so the regenerated diff stays minimal.
 */

// ── Shared ──────────────────────────────────────────────────────────

export type DomainId =
  | "cosmology"
  | "cosmology.ucglef1"
  | "chemistry"
  | "condmat"
  | "hep"
  | "nuclear"
  | "amo"
  | "gravity"
  | "statmech";

export interface DomainSummary {
  id: string;
  label: string;
}

export interface DomainsResponse {
  domains: DomainSummary[];
}

// ── qcompass_core.Manifest envelope ─────────────────────────────────

export interface BackendRequest {
  kind: "classical" | "ibm" | "ionq" | "iqm" | "azure" | "braket" | "auto";
  target?: string | null;
  shots?: number;
  seed?: number;
  max_runtime_seconds?: number | null;
}

export interface QcompassManifest<TProblem = Record<string, unknown>> {
  domain: string;
  version: string;
  problem: TProblem;
  backend_request: BackendRequest;
}

export interface ProvenanceRecord {
  classical_reference_hash: string;
  calibration_hash: string | null;
  error_mitigation: Record<string, unknown> | null;
}

export interface ProvenanceSidecar {
  schemaVersion: number;
  runId: string;
  domain: string;
  status: string;
  createdAt: string;
  manifest: Record<string, unknown>;
  provenance: ProvenanceRecord;
}

// ── Run submission / lookup ─────────────────────────────────────────

export interface SubmitRunRequest<TProblem = Record<string, unknown>> {
  manifest: QcompassManifest<TProblem>;
  runId?: string;
}

export interface SubmitRunResponse {
  runId: string;
  domain: string;
  status: string;
  provenanceSidecar: string;
  classicalReferenceHash: string;
}

// ── Visualization frames (mirror cosmic_forge_viz.schema) ───────────

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
  status: string;
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
  domain: string;
  schema_version: number;
  n_frames: number;
  frames: VisualizationFrame[];
}

// ── Scans ───────────────────────────────────────────────────────────

export interface ScanEnvelope {
  scanId: string;
  domain: string;
  kind: string;
  axes: Record<string, unknown>;
  payload: Record<string, unknown>;
  provenance: Record<string, unknown>;
  createdAt: string;
}

export interface CreateScanRequest {
  domain: string;
  kind: string;
  axes?: Record<string, unknown>;
  payload?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
}
