"""Pydantic mirror of ``src/types/domain.ts``.

Field names, casing, enum values, and nesting match the TypeScript
contract byte-for-byte. The frontend is the source of truth; if the
shapes drift, the integration test
``tests/integration/test_domain_parity.py`` fails.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ──────────────────────────────────────────────────────────────────────
# Common primitives
# ──────────────────────────────────────────────────────────────────────


class _Frozen(BaseModel):
    """Base: deep equality + camelCase tolerance from frontend JSON."""

    model_config = ConfigDict(
        populate_by_name=True,
        frozen=False,
        extra="forbid",
    )


# ──────────────────────────────────────────────────────────────────────
# Run configuration
# ──────────────────────────────────────────────────────────────────────

PotentialKind = Literal["starobinsky", "natural", "hilltop", "custom"]
Precision = Literal["fast", "standard", "high"]


class Potential(_Frozen):
    kind: PotentialKind
    params: dict[str, float] = Field(default_factory=dict)
    customPython: str | None = None


class Couplings(_Frozen):
    xi: float
    theta_grav: float
    f_a: float
    M_star: float
    M1: float
    S_E2: float


class Reheating(_Frozen):
    Gamma_phi: float
    T_reh_GeV: float


class AgentTrace(_Frozen):
    """Attached when a run is started by the agent (A6)."""

    conversationId: str
    hypothesisId: str
    approvalTokenId: str | None = None


class RunConfig(_Frozen):
    potential: Potential
    couplings: Couplings
    reheating: Reheating
    precision: Precision
    agent: AgentTrace | None = None


# ──────────────────────────────────────────────────────────────────────
# Run lifecycle
# ──────────────────────────────────────────────────────────────────────

RunStatus = Literal["queued", "running", "completed", "failed", "canceled"]
ModuleId = Literal["M1", "M2", "M3", "M4", "M5", "M6", "M7"]
LogLevel = Literal["info", "warn", "error"]


class StatusEvent(_Frozen):
    type: Literal["status"] = "status"
    status: RunStatus
    at: datetime


class LogEvent(_Frozen):
    type: Literal["log"] = "log"
    module: ModuleId
    level: LogLevel
    text: str
    at: datetime


class ProgressEvent(_Frozen):
    type: Literal["progress"] = "progress"
    module: ModuleId
    fraction: float
    detail: str | None = None


class MetricEvent(_Frozen):
    type: Literal["metric"] = "metric"
    name: str
    value: float
    unit: str | None = None


class ResultEvent(_Frozen):
    type: Literal["result"] = "result"
    payload: RunResult  # forward ref, resolved at the bottom


RunEvent = Annotated[
    StatusEvent | LogEvent | ProgressEvent | MetricEvent | ResultEvent,
    Field(discriminator="type"),
]


# ──────────────────────────────────────────────────────────────────────
# Uncertainty / audit / validation
# ──────────────────────────────────────────────────────────────────────


class UncertaintyBudget(_Frozen):
    statistical: float
    gridSystematic: float
    schemeSystematic: float
    inputPropagation: float
    total: float


AuditVerdict = Literal["PASS_R", "PASS_P", "PASS_S", "FAIL", "INAPPLICABLE"]
AuditCheckId = Literal[
    "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8",
    "S9", "S10", "S11", "S12", "S13", "S14", "S15",
]
AgentAuditId = Literal["A1", "A2", "A3", "A4", "A5", "A6"]


class AuditCheck(_Frozen):
    id: AuditCheckId
    name: str
    verdict: AuditVerdict
    value: float | None = None
    tolerance: float | None = None
    references: list[str] = Field(default_factory=list)
    notes: str = ""


class AuditSummary(_Frozen):
    passed: int
    total: int
    blocking: bool


class AuditReport(_Frozen):
    checks: list[AuditCheck]
    summary: AuditSummary


ValidationStatus = Literal["match", "degraded", "miss"]
ValidationBenchmarkId = Literal[
    "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"
]


class ValidationBenchmark(_Frozen):
    id: ValidationBenchmarkId
    label: str
    arxivId: str
    target: float
    observed: float
    relativeError: float
    status: ValidationStatus


class ValidationReport(_Frozen):
    benchmarks: list[ValidationBenchmark]


class SgwbSpectrum(_Frozen):
    f_Hz: list[float]
    Omega_gw: list[float]
    chirality: list[float]


class ModeSpectrum(_Frozen):
    k: list[float]
    h_plus: list[float]
    h_minus: list[float]


class RunSpectra(_Frozen):
    sgwb: SgwbSpectrum
    modes: ModeSpectrum


class EtaB(_Frozen):
    value: float
    uncertainty: float
    budget: UncertaintyBudget


class RunTiming(_Frozen):
    wall_seconds: float
    module_seconds: dict[str, float]  # keyed by ModuleId


class RunResult(_Frozen):
    id: str
    config: RunConfig
    status: RunStatus
    eta_B: EtaB
    F_GB: float
    audit: AuditReport
    spectra: RunSpectra
    timing: RunTiming
    validation: ValidationReport
    createdAt: datetime


# Resolve the forward ref now that RunResult is defined.
ResultEvent.model_rebuild()


# ──────────────────────────────────────────────────────────────────────
# Benchmarks & artifacts
# ──────────────────────────────────────────────────────────────────────


class BenchmarkEntry(_Frozen):
    id: str
    label: str
    arxivId: str
    description: str
    config: RunConfig
    expectedEta_B: float


class BenchmarkIndex(_Frozen):
    benchmarks: list[BenchmarkEntry]


class ArtifactRef(_Frozen):
    runId: str
    name: str
    path: str
    mimeType: str
    sizeBytes: int
    description: str


# ──────────────────────────────────────────────────────────────────────
# Chat / agent surface
# ──────────────────────────────────────────────────────────────────────

ChatRole = Literal["user", "assistant", "system", "tool"]
ToolName = Literal[
    # original frontend tool names — retained for transcript compatibility
    "load_run", "compare_runs", "start_run", "open_benchmark",
    "summarize_audit", "suggest_parameters", "export_report",
    "cite_paper", "plot_overlay",
    # M8 additions
    "list_benchmarks", "get_run", "get_audit", "get_validation",
    "scan_parameters", "validate_config", "cancel_run", "stream_run",
    "download_artifact",
    "propose_experiments", "record_hypothesis", "save_plan",
    "explain_audit", "summarize_literature", "suggest_next_parameter_scan",
    "propose_patch", "dry_run_patch", "request_human_review",
    "list_tools", "describe_tool", "get_capabilities",
]


class ToolCall(_Frozen):
    id: str
    name: ToolName
    arguments: dict[str, Any]


class ToolResult(_Frozen):
    id: str
    ok: bool
    output: Any


class ChatMessage(_Frozen):
    id: str
    role: ChatRole
    content: str
    toolCalls: list[ToolCall] | None = None
    toolResults: list[ToolResult] | None = None
    createdAt: datetime
    modelId: str | None = None


class TokenEvent(_Frozen):
    type: Literal["token"] = "token"
    delta: str


class ToolCallEvent(_Frozen):
    type: Literal["tool_call"] = "tool_call"
    call: ToolCall


class ToolResultEvent(_Frozen):
    type: Literal["tool_result"] = "tool_result"
    result: ToolResult


class MessageCompleteEvent(_Frozen):
    type: Literal["message_complete"] = "message_complete"
    message: ChatMessage


class ErrorEvent(_Frozen):
    type: Literal["error"] = "error"
    message: str


AssistantEvent = Annotated[
    TokenEvent | ToolCallEvent | ToolResultEvent
    | MessageCompleteEvent | ErrorEvent,
    Field(discriminator="type"),
]


# ──────────────────────────────────────────────────────────────────────
# Model descriptors (local + remote)
# ──────────────────────────────────────────────────────────────────────

ModelProvider = Literal["local", "remote"]
ModelFormat = Literal["gguf", "safetensors", "api"]


class ModelDescriptor(_Frozen):
    id: str
    displayName: str
    provider: ModelProvider
    format: ModelFormat
    sizeBytes: int | None = None
    contextWindow: int
    license: str
    source: str
    recommended: bool
    tags: list[str] = Field(default_factory=list)


class ModelStatusNotInstalled(_Frozen):
    state: Literal["not_installed"] = "not_installed"


class ModelStatusInstalling(_Frozen):
    state: Literal["installing"] = "installing"
    progressFraction: float
    etaSeconds: float | None = None


class ModelStatusReady(_Frozen):
    state: Literal["ready"] = "ready"
    installedAt: datetime
    diskBytes: int


class ModelStatusError(_Frozen):
    state: Literal["error"] = "error"
    message: str


ModelStatus = Annotated[
    ModelStatusNotInstalled | ModelStatusInstalling
    | ModelStatusReady | ModelStatusError,
    Field(discriminator="state"),
]


class InstallProgress(_Frozen):
    type: Literal["progress"] = "progress"
    fraction: float
    downloadedBytes: int
    totalBytes: int


class InstallVerifying(_Frozen):
    type: Literal["verifying"] = "verifying"


class InstallReady(_Frozen):
    type: Literal["ready"] = "ready"


class InstallError(_Frozen):
    type: Literal["error"] = "error"
    message: str


InstallEvent = Annotated[
    InstallProgress | InstallVerifying | InstallReady | InstallError,
    Field(discriminator="type"),
]


# ──────────────────────────────────────────────────────────────────────
# Service errors
# ──────────────────────────────────────────────────────────────────────

ServiceErrorCode = Literal[
    "NOT_FOUND",
    "INVALID_INPUT",
    "UPSTREAM_FAILURE",
    "STREAM_ABORTED",
    "NOT_IMPLEMENTED",
    "APPROVAL_REQUIRED",
    "AUDIT_VIOLATION",
]


class ServiceError(Exception):
    """Mirror of the frontend ``ServiceError``."""

    def __init__(self, code: ServiceErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


# ──────────────────────────────────────────────────────────────────────
# Scan / comparison / experiment plan (M8-side extensions)
# ──────────────────────────────────────────────────────────────────────


class ScanAxis(_Frozen):
    name: str
    path: str  # e.g. "couplings.xi"
    min: float
    max: float
    points: int
    log: bool = False


class ScanSpec(_Frozen):
    base: RunConfig
    axes: list[ScanAxis]


class ScanCell(_Frozen):
    coords: dict[str, float]
    eta_B: float
    F_GB: float
    status: RunStatus


class ScanResult(_Frozen):
    id: str
    spec: ScanSpec
    cells: list[ScanCell]
    createdAt: datetime


class ComparisonReport(_Frozen):
    runIds: list[str]
    metrics: dict[str, list[float]]  # metric → value per run in runIds order
    notes: str


class ExperimentPlan(_Frozen):
    hypothesis: str
    steps: list[str]
    suggestedConfigs: list[RunConfig]
    citations: list[str]  # arXiv IDs


class HypothesisRef(_Frozen):
    conversationId: str
    hypothesisId: str
    text: str
    createdAt: datetime


class PlanRef(_Frozen):
    conversationId: str
    planId: str
    path: str  # artifacts/agent-sandbox/{conversationId}/plans/{planId}.json


class CitationRecord(_Frozen):
    arxivId: str
    title: str
    authors: list[str]
    year: int
    references: list[AgentAuditId | AuditCheckId | ValidationBenchmarkId]


class LiteratureSummary(_Frozen):
    topic: str
    entries: list[CitationRecord]
    summary: str


class AuditExplanation(_Frozen):
    runId: str
    checkId: AuditCheckId
    verdict: AuditVerdict
    reasoning: str
    references: list[str]


class PatchProposal(_Frozen):
    patchId: str
    targetPath: str
    rationale: str
    unifiedDiff: str
    createdAt: datetime


class PatchTestReport(_Frozen):
    patchId: str
    passed: bool
    testsRun: list[str]
    auditChecksPreserved: list[AuditCheckId]
    auditChecksBroken: list[AuditCheckId]
    sandboxLog: str


class ReviewTicket(_Frozen):
    patchId: str
    ticketId: str
    createdAt: datetime
    status: Literal["open", "approved", "rejected"]


class Capabilities(_Frozen):
    schemaVersion: str
    tools: list[str]
    models: list[ModelDescriptor]
    approvalScopesRequired: dict[str, list[str]]
    precisionPolicy: dict[str, float]


class ConfigDiagnostic(_Frozen):
    severity: Literal["error", "warning", "info"]
    path: str
    message: str


class ConfigDiagnostics(_Frozen):
    valid: bool
    diagnostics: list[ConfigDiagnostic]
    normalized: RunConfig | None = None


class ToolSpec(_Frozen):
    name: str
    family: Literal["simulator", "research", "patch", "introspection"]
    description: str
    approvalRequired: bool
    inputSchema: dict[str, Any]
    outputSchema: dict[str, Any]
