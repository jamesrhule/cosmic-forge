"""Pydantic mirror of ``src/types/domain.ts``.

Field names, casing, enum values, and nesting match the TypeScript
contract byte-for-byte. The frontend is the source of truth; if the
shapes drift, the integration test
``tests/integration/test_domain_parity.py`` fails.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema, model_validator

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


# ── Potential parameters at the API boundary (W1-PARAMS) ─────────────
#
# JAMES DECISION 11: the engine works in reduced-Planck units
# (M_Pl = M_PL_GEV GeV = 1, m1_background/background.py); GeV appears only
# at the API/UI boundary. A RunConfig carries the potential's parameters as
# the client sent them, in the units below, and ``Potential.engine()`` makes
# the one conversion to M2's form, with M_PL_GEV, at the pipeline's entry
# (beside Γ_φ, m7_infer/pipeline.py). Every parameter name has one unit.


@dataclass(frozen=True)
class PotentialParam:
    unit: str
    description: str
    integer: bool = False
    optional: bool = False


@dataclass(frozen=True)
class PotentialParamForm:
    """One accepted set of parameter names for a built-in potential kind."""

    name: str
    params: dict[str, PotentialParam]

    @property
    def required(self) -> tuple[str, ...]:
        return tuple(k for k, p in self.params.items() if not p.optional)


HILLTOP_P_DEFAULT = 4
HILLTOP_P_MAX = 64

POTENTIAL_PARAM_FORMS: dict[str, tuple[PotentialParamForm, ...]] = {
    "starobinsky": (
        PotentialParamForm("starobinsky", {
            "M": PotentialParam("M_Pl", "mass scale M: V = (3/4) M² (1 − e^(−√(2/3) φ))²"),
        }),
    ),
    "natural": (
        # What the configurator sends (src/lib/configDefaults.json).
        PotentialParamForm("configurator", {
            "f": PotentialParam("GeV", "axion decay constant; M2 gets f_a = f / M_Pl"),
            "Lambda4": PotentialParam("M_Pl^4", "Λ⁴; M2 gets Λ = (Λ⁴)^(1/4)"),
        }),
        # M2's own names, already in M_Pl (Decision 11's fixture, the audits).
        PotentialParamForm("M2", {
            "f_a": PotentialParam("M_Pl", "axion decay constant f_a: V = Λ⁴ (1 − cos φ/f_a)"),
            "Lambda": PotentialParam("M_Pl", "Λ"),
        }),
    ),
    "hilltop": (
        PotentialParamForm("configurator", {
            "V0": PotentialParam("M_Pl^4", "height V₀: V = V₀ (1 − (φ/μ)^p)"),
            "mu": PotentialParam("GeV", "width μ; M2 gets μ / M_Pl"),
            "p": PotentialParam(
                "1", f"integer power, 2 to {HILLTOP_P_MAX}; default {HILLTOP_P_DEFAULT}",
                integer=True, optional=True,
            ),
        }),
    ),
}
# Any kind may carry the initial inflaton value (m7_infer.couplings.initial_field).
PHI0 = PotentialParam("M_Pl", "initial inflaton value (optional; default per kind)", optional=True)


def potential_forms_text(kind: str) -> str:
    forms = " or ".join(
        f"{', '.join(f'{k} [{p.unit}]' for k, p in f.params.items())} ({f.name} form)"
        for f in POTENTIAL_PARAM_FORMS[kind]
    )
    return f"{kind} takes {forms}, plus optional phi0 [M_Pl]"


def _chosen_form(kind: str, names: set[str]) -> PotentialParamForm | None:
    forms = POTENTIAL_PARAM_FORMS.get(kind)
    if not forms:
        return None
    return next((f for f in forms if names & f.params.keys()), forms[0])


def potential_param_errors(kind: str, params: dict[str, float]) -> list[str]:
    """Why ``params`` is not a valid parameter set for ``kind`` (empty if it is).

    Completeness is checked separately (:meth:`Potential.missing_params`):
    the agent's config tools accept partial dicts; the run route does not.
    """
    errors = [f"{kind} potential: {k} must be finite, got {v!r}" for k, v in params.items()
              if not math.isfinite(v)]
    forms = POTENTIAL_PARAM_FORMS.get(kind)
    if not forms:  # custom: the snippet's own symbols, in M_Pl units
        return errors
    names = set(params) - {"phi0"}
    known = {k: p for f in forms for k, p in f.params.items()}
    unknown = sorted(names - set(known))
    if unknown:
        errors.append(
            f"{kind} potential: unknown parameter(s) {unknown}; {potential_forms_text(kind)}",
        )
    used = [f for f in forms if names & f.params.keys()]
    if len(used) > 1:
        mixed = " with ".join(f"the {f.name} form ({', '.join(f.params)})" for f in used)
        errors.append(
            f"{kind} potential: ambiguous parameters {sorted(names)} mix {mixed}; send one form",
        )
    for k, v in params.items():
        p = known.get(k)
        if p is None or not math.isfinite(v):
            continue
        if p.integer:
            if not (float(v).is_integer() and 2 <= v <= HILLTOP_P_MAX):
                errors.append(f"{kind} potential: {k} must be an integer from 2 to "
                              f"{HILLTOP_P_MAX}, got {v!r}")
        elif v <= 0:
            errors.append(f"{kind} potential: {k} [{p.unit}] must be positive, got {v!r}")
    return errors


def potential_params_json_schema(*, required: bool) -> dict[str, Any]:
    """``Potential.params`` per kind and form, with units (the SDK's types)."""

    def prop(p: PotentialParam) -> dict[str, Any]:
        if p.integer:
            return {"type": "integer", "minimum": 2, "maximum": HILLTOP_P_MAX,
                    "default": HILLTOP_P_DEFAULT, "description": p.description}
        return {"type": "number", "exclusiveMinimum": 0,
                "description": f"[{p.unit}] {p.description}"}

    variants: list[dict[str, Any]] = []
    for kind, forms in POTENTIAL_PARAM_FORMS.items():
        for f in forms:
            props = {k: prop(p) for k, p in f.params.items()}
            props["phi0"] = {"type": "number",
                             "description": f"[{PHI0.unit}] {PHI0.description}"}
            form = "" if f.name == kind else f.name[0].upper() + f.name[1:]
            title = f"{kind.title()}{form}Params"
            v: dict[str, Any] = {
                "title": title, "type": "object", "properties": props,
                "additionalProperties": False, "description": f"kind={kind!r}, {f.name} form",
            }
            if required:
                v["required"] = list(f.required)
            variants.append(v)
    variants.append({
        "title": "CustomParams", "type": "object", "additionalProperties": {"type": "number"},
        "description": (
            "kind='custom': values of the symbols customPython uses besides phi [M_Pl units]"
        ),
    })
    return {
        "title": "Params",
        "description": (
            "Potential parameters in API units (JAMES DECISION 11: GeV only at the API; the "
            "backend converts them to reduced-Planck units with its M_Pl, M_PL_GEV). One form "
            "per dict: mixing forms, unknown names and non-positive values are rejected (422)."
            + (" Every parameter of the form is required." if required else
               " The run route requires every parameter of the form; the agent's config tools "
               "accept a partial dict.")
        ),
        "anyOf": variants,
    }


class Potential(_Frozen):
    """The potential as the API receives it (units: ``POTENTIAL_PARAM_FORMS``)."""

    kind: PotentialKind
    params: Annotated[
        dict[str, float], WithJsonSchema(potential_params_json_schema(required=False)),
    ] = Field(default_factory=dict)
    customPython: str | None = None

    @model_validator(mode="after")
    def _check_params(self) -> Potential:
        errors = potential_param_errors(self.kind, self.params)
        if errors:
            raise ValueError("; ".join(errors))
        return self

    def missing_params(self) -> list[str]:
        """The chosen form's required parameters that ``params`` lacks, with units."""
        form = _chosen_form(self.kind, set(self.params))
        if form is None:
            return []
        return [f"{k} [{form.params[k].unit}]" for k in form.required if k not in self.params]

    def engine(self) -> EnginePotential:
        """M2's reduced-Planck form: the one GeV → M_Pl conversion (Decision 11).

        natural (configurator form): f_a = f / M_Pl, Λ = (Λ⁴)^(1/4); hilltop:
        μ / M_Pl. Every other parameter (M, V0, p, phi0, M2's natural names,
        custom symbols) is already in M_Pl units and passes through unchanged.
        Idempotent: an :class:`EnginePotential` is returned as is.
        """
        from .m1_background.background import M_PL_GEV  # the one M_Pl

        p = dict(self.params)
        if self.kind == "natural":
            if "f" in p:
                p["f_a"] = p.pop("f") / M_PL_GEV
            if "Lambda4" in p:
                p["Lambda"] = p.pop("Lambda4") ** 0.25
        elif self.kind == "hilltop" and "mu" in p:
            p["mu"] = p["mu"] / M_PL_GEV
        return EnginePotential.model_construct(
            kind=self.kind, params=p, customPython=self.customPython,
        )


class EnginePotential(Potential):
    """A potential in M2's units (from :meth:`Potential.engine`); never converted twice."""

    def engine(self) -> EnginePotential:
        return self


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


class ClassicalReference(_Frozen):
    method: str
    summary: str
    artifactPath: str | None = None


class ResourceEstimate(_Frozen):
    kind: Literal["classical", "qpu-digital", "qpu-analog"]
    note: str
    logicalQubits: int | None = None
    physicalQubits: int | None = None
    toffoliCount: int | None = None
    tCount: int | None = None
    wallSecondsEstimate: float | None = None


class ErrorMitigation(_Frozen):
    method: str
    config: dict[str, Any] = Field(default_factory=dict)


class RunProvenance(_Frozen):
    """Mirror of ``RunProvenance`` in ``src/types/domain.ts``.

    QCompass Phase 2+; ``None`` for cosmology runs.
    """

    classicalReference: ClassicalReference | None = None
    resourceEstimate: ResourceEstimate | None = None
    deviceCalibrationHash: str | None = None
    errorMitigation: ErrorMitigation | None = None


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
    provenance: RunProvenance | None = None


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
    # Plan limits and budgets (P3-05, ucgle_f1.plans; mirrored in src/types/domain.ts)
    "PLAN_RUNS_PER_MONTH_EXCEEDED",
    "PLAN_CONCURRENT_JOBS_EXCEEDED",
    "PLAN_GPU_REQUIRED",
    "PLAN_TIMELINE_BYTES_EXCEEDED",
    "BUDGET_EXCEEDED",
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
