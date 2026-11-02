/**
 * UCGLE-F1 Workbench — domain types.
 *
 * This module is the canonical handoff contract. Claude Code will mirror
 * every type here as Pydantic models server-side. Field names, casing,
 * enum values, and nesting MUST stay byte-for-byte identical.
 *
 * Treat physics labels (η_B, F_GB, audit S1–S15, validation V1–V8) as
 * opaque domain identifiers. The frontend only renders them.
 */

/* ─────────────────────────────────────────────────────────────────────
 * Run configuration
 * ────────────────────────────────────────────────────────────────── */

export type PotentialKind = "starobinsky" | "natural" | "hilltop" | "custom";

export type Precision = "fast" | "standard" | "high";

export interface RunConfig {
  potential: {
    kind: PotentialKind;
    params: Record<string, number>;
    /** Python source string. Never executed in the browser. */
    customPython?: string;
  };
  couplings: {
    xi: number;
    theta_grav: number;
    f_a: number;
    M_star: number;
    M1: number;
    S_E2: number;
  };
  reheating: {
    Gamma_phi: number;
    T_reh_GeV: number;
  };
  precision: Precision;
}

/* ─────────────────────────────────────────────────────────────────────
 * Run lifecycle
 * ────────────────────────────────────────────────────────────────── */

export type RunStatus = "queued" | "running" | "completed" | "failed" | "canceled";

export type ModuleId = "M1" | "M2" | "M3" | "M4" | "M5" | "M6" | "M7";

export type LogLevel = "info" | "warn" | "error";

export type RunEvent =
  | { type: "status"; status: RunStatus; at: string }
  | {
      type: "log";
      module: ModuleId;
      level: LogLevel;
      text: string;
      at: string;
    }
  | {
      type: "progress";
      module: ModuleId;
      fraction: number;
      detail?: string;
    }
  | { type: "metric"; name: string; value: number; unit?: string }
  | { type: "result"; payload: RunResult };

/* ─────────────────────────────────────────────────────────────────────
 * Run result
 * ────────────────────────────────────────────────────────────────── */

export interface UncertaintyBudget {
  statistical: number;
  gridSystematic: number;
  schemeSystematic: number;
  inputPropagation: number;
  total: number;
}

export type AuditVerdict = "PASS_R" | "PASS_P" | "PASS_S" | "FAIL" | "INAPPLICABLE";

export type AuditCheckId =
  | "S1"
  | "S2"
  | "S3"
  | "S4"
  | "S5"
  | "S6"
  | "S7"
  | "S8"
  | "S9"
  | "S10"
  | "S11"
  | "S12"
  | "S13"
  | "S14"
  | "S15";

export interface AuditCheck {
  id: AuditCheckId;
  name: string;
  verdict: AuditVerdict;
  value?: number;
  tolerance?: number;
  /** arXiv IDs */
  references: string[];
  notes: string;
}

export interface AuditReport {
  checks: AuditCheck[];
  summary: { passed: number; total: number; blocking: boolean };
}

export type ValidationStatus = "match" | "degraded" | "miss";

export type ValidationBenchmarkId = "V1" | "V2" | "V3" | "V4" | "V5" | "V6" | "V7" | "V8";

export interface ValidationBenchmark {
  id: ValidationBenchmarkId;
  label: string;
  arxivId: string;
  target: number;
  observed: number;
  relativeError: number;
  status: ValidationStatus;
}

export interface ValidationReport {
  benchmarks: ValidationBenchmark[];
}

export interface SgwbSpectrum {
  f_Hz: number[];
  Omega_gw: number[];
  chirality: number[];
  /**
   * M6's placeholder flag: `true` while `f_Hz` is the placeholder
   * `1e-19 · k` conversion, not a physical frequency (R6). Absent on bundled
   * fixtures and on results stored before the API carried it.
   */
  f_Hz_is_placeholder?: boolean | null;
  /** M6's explanation of the placeholder. */
  note?: string | null;
}

export interface ModeSpectrum {
  k: number[];
  h_plus: number[];
  h_minus: number[];
}

/**
 * Optional provenance — reserved for QCompass Phase 2+ to attach
 * classical reference, resource estimate, device calibration hash, and
 * error mitigation config to any run derived (in part) from a quantum
 * backend. Cosmology runs leave this `null` / omitted.
 *
 * Stored as nullable JSON so the database schema does not need to
 * change when Phase 2 lands.
 */
export interface RunProvenance {
  classicalReference: { method: string; summary: string; artifactPath?: string } | null;
  resourceEstimate: {
    kind: "classical" | "qpu-digital" | "qpu-analog";
    note: string;
    logicalQubits?: number;
    physicalQubits?: number;
    toffoliCount?: number;
    tCount?: number;
    wallSecondsEstimate?: number;
  } | null;
  deviceCalibrationHash: string | null;
  errorMitigation: { method: string; config: Record<string, unknown> } | null;
}

export interface RunResult {
  id: string;
  config: RunConfig;
  status: RunStatus;
  eta_B: {
    /**
     * Finite when published. When the engine refuses η_B it is NaN, which
     * arrives as `null` (or the stored marker "NaN"); `refusal` says why.
     * Display through `readEtaB` (`@/lib/etaB`).
     */
    value: number | null;
    uncertainty: number | null;
    budget: UncertaintyBudget;
    /** Why η_B is not published (`pipeline.eta_B_refusal`); absent on fixtures. */
    refusal?: string | null;
  };
  F_GB: number;
  audit: AuditReport;
  spectra: {
    sgwb: SgwbSpectrum;
    modes: ModeSpectrum;
  };
  timing: {
    wall_seconds: number;
    module_seconds: Record<ModuleId, number>;
  };
  validation: ValidationReport;
  createdAt: string;
  /** QCompass Phase 2+; `null` / omitted for cosmology. */
  provenance?: RunProvenance | null;
  /** R7 / Decision 13a: a bundled fixture whose results were never computed. */
  synthetic?: boolean;
}

/* ─────────────────────────────────────────────────────────────────────
 * Parameter scans
 * ────────────────────────────────────────────────────────────────── */

export type CouplingField = keyof RunConfig["couplings"];

export interface ScanResult {
  id: string;
  xAxis: { field: CouplingField; values: number[]; log: boolean };
  yAxis: { field: CouplingField; values: number[]; log: boolean };
  /** [y][x] grid of η_B values. */
  eta_B_grid: number[][];
  planckBand: { low: number; high: number };
}

/* ─────────────────────────────────────────────────────────────────────
 * Benchmarks & artifacts
 * ────────────────────────────────────────────────────────────────── */

export interface BenchmarkEntry {
  id: string;
  label: string;
  arxivId: string;
  description: string;
  config: RunConfig;
  expectedEta_B: number;
}

export interface BenchmarkIndex {
  benchmarks: BenchmarkEntry[];
}

export interface ArtifactRef {
  runId: string;
  name: string;
  /** Relative path inside /public/fixtures/artifacts/ */
  path: string;
  mimeType: string;
  sizeBytes: number;
  description: string;
}

/* ─────────────────────────────────────────────────────────────────────
 * Assistant
 * ────────────────────────────────────────────────────────────────── */

export type ChatRole = "user" | "assistant" | "system" | "tool";

export type ToolName =
  | "load_run"
  | "compare_runs"
  | "start_run"
  | "open_benchmark"
  | "summarize_audit"
  | "suggest_parameters"
  | "export_report"
  | "cite_paper"
  | "plot_overlay";

export interface ToolCall {
  id: string;
  name: ToolName;
  arguments: Record<string, unknown>;
}

export interface ToolResult {
  id: string;
  ok: boolean;
  output: unknown;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  /** Markdown */
  content: string;
  toolCalls?: ToolCall[];
  toolResults?: ToolResult[];
  createdAt: string;
  modelId?: string;
}

export type AssistantEvent =
  | { type: "token"; delta: string }
  | { type: "tool_call"; call: ToolCall }
  | { type: "tool_result"; result: ToolResult }
  | { type: "message_complete"; message: ChatMessage }
  | { type: "error"; message: string };

/* ─────────────────────────────────────────────────────────────────────
 * Models
 * ────────────────────────────────────────────────────────────────── */

export type ModelProvider = "local" | "remote";

export type ModelFormat = "gguf" | "safetensors" | "api";

export interface ModelDescriptor {
  id: string;
  displayName: string;
  provider: ModelProvider;
  format: ModelFormat;
  sizeBytes?: number;
  contextWindow: number;
  license: string;
  /** Source URL (HuggingFace, model card, etc.) */
  source: string;
  recommended: boolean;
  tags: string[];
}

export type ModelStatus =
  | { state: "not_installed" }
  | { state: "installing"; progressFraction: number; etaSeconds?: number }
  | { state: "ready"; installedAt: string; diskBytes: number }
  | { state: "error"; message: string };

export type InstallEvent =
  | {
      type: "progress";
      fraction: number;
      downloadedBytes: number;
      totalBytes: number;
    }
  | { type: "verifying" }
  | { type: "ready" }
  | { type: "error"; message: string };

/* ─────────────────────────────────────────────────────────────────────
 * Errors
 * ────────────────────────────────────────────────────────────────── */

export type ServiceErrorCode =
  | "NOT_FOUND"
  | "INVALID_INPUT"
  | "UPSTREAM_FAILURE"
  | "STREAM_ABORTED"
  | "NOT_IMPLEMENTED"
  // Plan limits and budgets (P3-05): the compute API's machine-readable codes.
  | "PLAN_RUNS_PER_MONTH_EXCEEDED"
  | "PLAN_CONCURRENT_JOBS_EXCEEDED"
  | "PLAN_GPU_REQUIRED"
  | "PLAN_TIMELINE_BYTES_EXCEEDED"
  | "BUDGET_EXCEEDED";

/** Limit/budget codes the API returns with 429 or 402 (P3-05). */
export const PLAN_ERROR_CODES = [
  "PLAN_RUNS_PER_MONTH_EXCEEDED",
  "PLAN_CONCURRENT_JOBS_EXCEEDED",
  "PLAN_GPU_REQUIRED",
  "PLAN_TIMELINE_BYTES_EXCEEDED",
  "BUDGET_EXCEEDED",
] as const satisfies readonly ServiceErrorCode[];

export class ServiceError extends Error {
  readonly code: ServiceErrorCode;
  constructor(code: ServiceErrorCode, message: string) {
    super(message);
    this.code = code;
    this.name = "ServiceError";
  }
}
