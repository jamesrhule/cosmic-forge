/**
 * QCompass — Domain plugin contracts (Phase 1: shell only).
 *
 * This module defines the typed seam that lets us add other physics
 * domains (chemistry, condensed matter, HEP, nuclear, AMO, gravity,
 * statmech) later as opt-in plugins, WITHOUT touching the audited
 * UCGLE-F1 cosmology core (M1–M7, S1–S15).
 *
 * Isolation rule: nothing under `src/services/` may import from this
 * module. Coupling is one-way — domain plugins wrap services, not the
 * other way around. The leptogenesis path keeps running unchanged
 * whether the registry is loaded or not.
 *
 * Naming: see Section 6 of the architect assessment. Internal codename
 * `QCompass`; user-facing product name unchanged in this phase.
 */

import type { RunConfig, RunResult, AuditReport } from "@/types/domain";

/* ─────────────────────────────────────────────────────────────────────
 * Domain identity
 * ────────────────────────────────────────────────────────────────── */

/**
 * Stable, dotted domain ids. The cosmology id is locked — it backs the
 * existing UCGLE-F1 fixtures and persisted run rows.
 *
 * Phase 2 will register additional ids (e.g. `chemistry.molecular`,
 * `hep.lattice.schwinger_1p1`). New ids MUST follow `<area>.<flavor>`.
 */
export type DomainId =
  | "cosmology.ucglef1"
  | "chemistry.molecular"
  | "condmat.lattice"
  | "hep.lattice"
  | "nuclear.structure"
  | "amo.rydberg"
  | "gravity.syk"
  | "statmech.sampling";

export interface DomainCapability {
  /** True if a classical reference solver exists in-tree. */
  classical: boolean;
  /** True if at least one quantum experiment template is registered. */
  quantum: boolean;
  /** True if this domain is wired through the audit pipeline. */
  audited: boolean;
}

/* ─────────────────────────────────────────────────────────────────────
 * Manifest envelope
 * ────────────────────────────────────────────────────────────────── */

/**
 * Top-level envelope for a domain run request. Each domain owns its
 * `problem` schema; the envelope is versioned independently so we can
 * evolve cosmology and (eventually) chemistry payloads on different
 * cadences.
 */
export interface Manifest<TProblem = unknown> {
  domain: DomainId;
  /** Manifest envelope version, not the problem schema version. */
  version: 1;
  problem: TProblem;
  backendRequest?: BackendRequest;
}

export interface BackendRequest {
  /** Hint, not a binding contract — router has the last word. */
  preferred?: "cpu-classical" | "gpu-classical" | "tn-classical" | "qpu-digital" | "qpu-analog";
  shots?: number;
  maxWallSeconds?: number;
}

/* ─────────────────────────────────────────────────────────────────────
 * Provenance — reserved for Phase 2 quantum claims
 * ────────────────────────────────────────────────────────────────── */

/**
 * Attached to any RunResult derived (in part) from a quantum backend
 * or a heuristic surrogate. Cosmology runs leave this `null`.
 *
 * Storing provenance now as an optional, nullable field on `RunResult`
 * keeps the database schema forward-compatible without a migration.
 */
export interface ProvenanceRecord {
  /** Pointer to the classical reference computation used to validate. */
  classicalReference: {
    method: string;
    summary: string;
    artifactPath?: string;
  } | null;
  /** Output of M12 resource estimator (Azure-QRE-shaped). */
  resourceEstimate: ResourceEstimate | null;
  /** Hash of device calibration / FoMaC snapshot at run time. */
  deviceCalibrationHash: string | null;
  /** Error mitigation policy actually applied (ZNE, PEC, ODR, …). */
  errorMitigation: {
    method: string;
    config: Record<string, unknown>;
  } | null;
}

export interface ResourceEstimate {
  kind: "classical" | "qpu-digital" | "qpu-analog";
  note: string;
  logicalQubits?: number;
  physicalQubits?: number;
  toffoliCount?: number;
  tCount?: number;
  wallSecondsEstimate?: number;
}

/* ─────────────────────────────────────────────────────────────────────
 * Simulation protocol — what every domain plugin implements
 * ────────────────────────────────────────────────────────────────── */

export interface PreparedInstance<TProblem = unknown> {
  manifest: Manifest<TProblem>;
  /** Backend-resolvable handle; opaque to the orchestrator. */
  handle: string;
}

export interface ValidationOutcome {
  ok: boolean;
  audit: AuditReport | null;
  notes: string;
}

export interface Simulation<TProblem = unknown, TResult = unknown> {
  prepare(manifest: Manifest<TProblem>): Promise<PreparedInstance<TProblem>>;
  run(instance: PreparedInstance<TProblem>): Promise<TResult>;
  validate(result: TResult): Promise<ValidationOutcome>;
}

/* ─────────────────────────────────────────────────────────────────────
 * Domain plugin descriptor
 * ────────────────────────────────────────────────────────────────── */

export interface DomainPlugin<TProblem = unknown, TResult = unknown> {
  id: DomainId;
  /** Human label for the domain selector chip. */
  label: string;
  /** Short, one-line description. */
  description: string;
  capability: DomainCapability;
  /** True when the plugin is ready to be invoked from UI. */
  enabled: boolean;
  /** Optional reason shown when `enabled === false`. */
  disabledReason?: string;
  simulation: Simulation<TProblem, TResult>;
}

/* ─────────────────────────────────────────────────────────────────────
 * Re-exports for the cosmology adapter
 * ────────────────────────────────────────────────────────────────── */

/**
 * The cosmology problem payload IS the existing `RunConfig`. Locked in
 * Phase 1 — do not edit without coordinating with the S1–S15 audit.
 */
export type CosmologyProblem = RunConfig;
export type CosmologyResult = RunResult;
