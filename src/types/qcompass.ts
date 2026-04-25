/**
 * QCompass workspace — TypeScript mirror of the Pydantic models in
 * `packages/qcompass-core/src/qcompass_core/manifest.py` and the
 * chemistry-domain payload from
 * `packages/qfull-chemistry/src/qfull_chem/manifest.py`.
 *
 * Field names, casing, and Literal values must match the Python side
 * byte-for-byte. The chemistry service round-trips this contract
 * unchanged.
 */

/* ─────────────────────────────────────────────────────────────────────
 * qcompass-core envelope
 * ────────────────────────────────────────────────────────────────── */

export type QcompassDomain =
  | "cosmology"
  | "chemistry"
  | "condmat"
  | "hep"
  | "nuclear"
  | "amo"
  | "gravity"
  | "statmech"
  | "null";

export type BackendKind =
  | "classical"
  | "quantum_simulator"
  | "quantum_hardware"
  | "auto";

export interface BackendRequest {
  kind: BackendKind;
  target?: string | null;
  priority?: string[];
  shots?: number;
  seed?: number | null;
  max_runtime_seconds?: number;
}

export interface ResourceEstimate {
  physical_qubits: number;
  logical_qubits: number;
  t_count: number;
  rotation_count: number;
  depth: number;
  runtime_seconds: number;
  estimator: "microsoft" | "qrechem" | "tfermion" | "stub";
  notes: string;
}

export interface ProvenanceRecord {
  classical_reference_hash: string;
  resource_estimate: ResourceEstimate | null;
  device_calibration_hash: string | null;
  error_mitigation_config: Record<string, unknown> | null;
  recorded_at: string;
}

export interface QcompassManifest<TProblem = Record<string, unknown>> {
  domain: QcompassDomain;
  version: string;
  problem: TProblem;
  backend_request: BackendRequest;
  metadata?: Record<string, unknown>;
}

/* ─────────────────────────────────────────────────────────────────────
 * Chemistry-domain payload
 * ────────────────────────────────────────────────────────────────── */

export type MoleculeName = "H2" | "LiH" | "N2" | "FeMoco_toy";
export type ReferenceMethod = "FCI" | "DMRG" | "CCSD(T)";
export type BackendPreference = "classical" | "sqd" | "dice" | "auto";

export interface ChemistryProblem {
  molecule: MoleculeName | string;
  basis: string | null;
  active_space: [number, number] | null;
  backend_preference: BackendPreference;
  reference: ReferenceMethod | null;
  shots: number;
  seed: number;
  geometry: string | null;
  fcidump_path: string | null;
  charge: number;
  spin: number;
}

/* ─────────────────────────────────────────────────────────────────────
 * Run lifecycle (chemistry)
 * ────────────────────────────────────────────────────────────────── */

export type ChemistryPathTaken = "classical" | "sqd" | "dice";

export type ChemistryRunStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "canceled";

export interface ChemistryEnergies {
  classical_energy: number | null;
  quantum_energy: number | null;
  classical_method: string;
  /**
   * One-line scientific summary surfaced as the run-card tagline,
   * e.g. "FCI -1.137274 Ha (chemical accuracy)".
   */
  summary: string;
}

export interface ChemistryRunResult {
  id: string;
  manifest: QcompassManifest<ChemistryProblem>;
  status: ChemistryRunStatus;
  pathTaken: ChemistryPathTaken;
  energies: ChemistryEnergies;
  provenance: ProvenanceRecord;
  /**
   * Set when the classical reference is unavailable (e.g. FeMoco-toy).
   * The frontend renders a yellow advisory rather than a red error in
   * that case — qualitative results are still useful.
   */
  provenance_warning: "no_classical_reference" | null;
  metadata: Record<string, unknown>;
  createdAt: string;
}

export type ChemistryLogLevel = "info" | "warn" | "error";

export type ChemistryRunEvent =
  | { type: "status"; status: ChemistryRunStatus; at: string }
  | {
      type: "log";
      level: ChemistryLogLevel;
      text: string;
      at: string;
    }
  | { type: "metric"; name: string; value: number; unit?: string }
  | { type: "result"; payload: ChemistryRunResult };

/* ─────────────────────────────────────────────────────────────────────
 * JSON Schema (manifest form loader)
 * ────────────────────────────────────────────────────────────────── */

/** Minimal shape we depend on. Real schemas may carry more fields. */
export interface JsonSchema {
  $defs?: Record<string, JsonSchema>;
  type?: string | string[];
  title?: string;
  description?: string;
  enum?: Array<string | number>;
  default?: unknown;
  format?: string;
  pattern?: string;
  minimum?: number;
  maximum?: number;
  items?: JsonSchema;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  $ref?: string;
  additionalProperties?: boolean | JsonSchema;
  /** OpenAPI / pydantic anyOf for nullable + literal unions. */
  anyOf?: JsonSchema[];
  oneOf?: JsonSchema[];
  /** OpenAPI / pydantic allOf for inline composition. */
  allOf?: JsonSchema[];
  prefixItems?: JsonSchema[];
}
