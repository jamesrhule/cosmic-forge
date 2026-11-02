/**
 * Public SDK types (P4-02).
 *
 * Response and model types are aliases of the generated OpenAPI schemas
 * (`./api.ts`), so they cannot drift from the backend. The few types the
 * OpenAPI document does not describe are written by hand below and say why.
 */
import type { JsonResponse, Schemas } from "./api";

// ── Generated (OpenAPI) ─────────────────────────────────────────────

export type DomainSummary = Schemas["DomainEntry"];
export type DomainsResponse = Schemas["DomainsResponse"];
export type SubmitRunResponse = Schemas["SubmitRunResponse"];
export type DomainRunResult = Schemas["DomainRunResult"];
export type RunSummary = Schemas["RunSummary"];
export type ProvenanceRecord = Schemas["ProvenanceRecordExt"];
export type ScanEnvelope = Schemas["ScanEnvelope"];
export type ScanListResponse = Schemas["ScanListResponse"];
export type VisualizationTimeline = Schemas["VisualizationResponse"];
export type BenchmarkIndex = Schemas["BenchmarkIndex"];
export type RunConfig = Schemas["RunConfig"];
export type RunResult = Schemas["RunResult"];
export type AuditReport = Schemas["AuditReport"];
export type StartRunResponse = Schemas["StartRunResponse"];
export type ModelDescriptor = Schemas["ModelDescriptor"];
export type Tenant = Schemas["Tenant"];
export type LiteratureReference = Schemas["LiteratureReference"];
export type VerdictSample = Schemas["VerdictSample"];
export type HealthResponse = Schemas["HealthResponse"];
export type ReadinessResponse = Schemas["ReadinessResponse"];
export type ErrorEnvelope = Schemas["ErrorEnvelope"];
export type ModelStatus = JsonResponse<"/api/models/{mid}/status", "get">;
export type DomainId = DomainRunResult["domain"] | DomainSummary["id"];

// ── Hand-written: request bodies the API accepts as free-form JSON ─
// `POST /api/qcompass/domains/{domain}/runs` and `POST /api/qcompass/scans`
// take `dict` bodies (the manifest's `problem` is per-domain and validated
// by the domain plugin: cosmology's at submit, 422 INVALID_INPUT; the others
// in the worker), so OpenAPI has no schema for them. These mirror
// `qcompass_core.Manifest`. A cosmology problem is a `RunConfig`, whose
// `potential.params` schema gives each kind's parameters and units.

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

export interface SubmitRunRequest<TProblem = Record<string, unknown>> {
  manifest: QcompassManifest<TProblem>;
  runId?: string;
}

export interface CreateScanRequest {
  domain: string;
  kind: string;
  axes?: Record<string, unknown>;
  payload?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
}

// ── Hand-written: SSE event payloads (OpenAPI describes the stream's
// media type, not its events) ───────────────────────────────────────

/** `…/runs/{run_id}/stream` events, written by the worker (ucgle_f1.worker). */
export type QcompassRunStreamEvent =
  | { event: "history"; data: { runId: string; domain: string; createdAt: string } }
  | { event: "status"; data: { status: string; at?: string } }
  | {
      event: "progress";
      data: { stage?: string; module?: string; fraction?: number; seconds?: number };
    }
  | { event: "log"; data: { level?: string; text?: string; module?: string } }
  | { event: "result"; data: Record<string, unknown> }
  | { event: "end"; data: Record<string, never> }
  | { event: string; data: unknown };

// ── Visualization frames (mirror cosmic_forge_viz.schema; the API types
// frames as JSON objects) ───────────────────────────────────────────

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
