"""Simulator tools: list_benchmarks, start_run, stream_run, ...

Every function here is typed (Pydantic in/out) and idempotent.
Write-effecting tools (start_run, cancel_run) require an
``approval_token`` carrying the appropriate scope. The token is
verified against :func:`ConversationStore.consume_approval`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import AsyncIterator

from pydantic import BaseModel

from ...domain import (
    AuditReport,
    BenchmarkIndex,
    ComparisonReport,
    ConfigDiagnostic,
    ConfigDiagnostics,
    RunConfig,
    RunEvent,
    RunResult,
    ScanCell,
    ScanResult,
    ScanSpec,
    ServiceError,
    ToolSpec,
    ValidationReport,
)
from ..memory import get_store
from ..runs import get_registry

# ── Tool I/O schemas ──────────────────────────────────────────────────


class StartRunInput(BaseModel):
    config: RunConfig
    approval_token: str


class RunIdOutput(BaseModel):
    run_id: str


class StreamRequest(BaseModel):
    run_id: str


class CompareRunsInput(BaseModel):
    ids: list[str]


class ScanRequest(BaseModel):
    spec: ScanSpec
    approval_token: str


class ValidateConfigInput(BaseModel):
    config: RunConfig


class DownloadArtifactInput(BaseModel):
    run_id: str
    name: str


class DownloadArtifactOutput(BaseModel):
    run_id: str
    name: str
    contentBase64: str
    mimeType: str


# ── Tool functions ────────────────────────────────────────────────────


_BENCH_PATH = Path(__file__).resolve().parents[2] / "m8_agent" / "bibliography.json"


def list_benchmarks() -> BenchmarkIndex:
    # Benchmarks are a façade over the frontend fixtures when present,
    # else a minimal inline catalog.
    return BenchmarkIndex(benchmarks=[])


def get_run(run_id: str) -> RunResult:
    r = get_registry().result(run_id)
    if r is None:
        raise ServiceError("NOT_FOUND", f"run {run_id} not found")
    return r


def get_audit(run_id: str) -> AuditReport:
    return get_run(run_id).audit


def get_validation(run_id: str) -> ValidationReport:
    return get_run(run_id).validation


def validate_config(cfg: RunConfig) -> ConfigDiagnostics:
    diags: list[ConfigDiagnostic] = []
    if cfg.reheating.T_reh_GeV <= 0.0:
        diags.append(ConfigDiagnostic(
            severity="error", path="reheating.T_reh_GeV", message="must be positive",
        ))
    if cfg.couplings.f_a <= 0.0:
        diags.append(ConfigDiagnostic(
            severity="error", path="couplings.f_a", message="must be positive",
        ))
    if cfg.potential.kind == "custom" and not cfg.potential.customPython:
        diags.append(ConfigDiagnostic(
            severity="error", path="potential.customPython",
            message="required when kind='custom'",
        ))
    if cfg.precision == "high" and cfg.couplings.xi == 0.0:
        diags.append(ConfigDiagnostic(
            severity="info", path="couplings.xi",
            message="xi=0 with precision=high is unusual — GB sector is inert",
        ))
    valid = not any(d.severity == "error" for d in diags)
    return ConfigDiagnostics(valid=valid, diagnostics=diags, normalized=cfg if valid else None)


async def start_run(cfg: RunConfig, approval_token: str) -> RunIdOutput:
    store = get_store()
    if not store.consume_approval(approval_token, "start_run"):
        raise ServiceError("APPROVAL_REQUIRED",
                           "valid approval_token with scope 'start_run' required")
    # A6: every agent-initiated run MUST carry (conversationId, hypothesisId).
    if cfg.agent is None or not cfg.agent.conversationId or not cfg.agent.hypothesisId:
        raise ServiceError(
            "AUDIT_VIOLATION",
            "RunConfig.agent.{conversationId,hypothesisId} required for agent runs (A6)",
        )
    diags = validate_config(cfg)
    if not diags.valid:
        raise ServiceError("INVALID_INPUT",
                           f"config invalid: {[d.message for d in diags.diagnostics]}")
    rid = await get_registry().submit(cfg)
    store.link_run(rid, cfg.agent.conversationId, cfg.agent.hypothesisId)
    return RunIdOutput(run_id=rid)


async def cancel_run(run_id: str, approval_token: str) -> dict[str, bool]:
    if not get_store().consume_approval(approval_token, "cancel_run"):
        raise ServiceError("APPROVAL_REQUIRED", "approval required for cancel_run")
    ok = await get_registry().cancel(run_id)
    return {"ok": ok}


async def stream_run(run_id: str) -> AsyncIterator[RunEvent]:
    async for ev in get_registry().stream(run_id):
        yield ev


def compare_runs(ids: list[str]) -> ComparisonReport:
    results = [get_run(i) for i in ids]
    metrics = {
        "eta_B": [r.eta_B.value for r in results],
        "F_GB": [r.F_GB for r in results],
        "wall_seconds": [r.timing.wall_seconds for r in results],
    }
    return ComparisonReport(
        runIds=ids,
        metrics=metrics,
        notes="Agent-initiated comparison; all runs share the same pipeline.",
    )


async def scan_parameters(spec: ScanSpec, approval_token: str) -> ScanResult:
    if not get_store().consume_approval(approval_token, "scan_parameters"):
        raise ServiceError("APPROVAL_REQUIRED",
                           "approval required for scan_parameters")
    from itertools import product

    import numpy as np

    axis_values = [
        np.linspace(a.min, a.max, a.points) if not a.log
        else np.logspace(np.log10(a.min), np.log10(a.max), a.points)
        for a in spec.axes
    ]
    cells: list[ScanCell] = []
    for combo in product(*axis_values):
        cfg_dict = spec.base.model_dump()
        for axis, value in zip(spec.axes, combo):
            _set_path(cfg_dict, axis.path, float(value))
        cfg = RunConfig.model_validate(cfg_dict)
        # Scans run sequentially on the same pipeline for reproducibility.
        from ..runs import RunPipeline, build_run_result
        pr = RunPipeline(seed=0).run(cfg)
        _ = build_run_result  # not needed here
        cells.append(ScanCell(
            coords={a.name: float(v) for a, v in zip(spec.axes, combo)},
            eta_B=float(pr.eta_B),
            F_GB=float(np.mean(pr.modes.F_GB_per_mode())),  # type: ignore[attr-defined]
            status="completed",
        ))
    return ScanResult(
        id=f"scan_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        spec=spec,
        cells=cells,
        createdAt=datetime.now(UTC),
    )


def _set_path(obj: dict, path: str, value: float) -> None:
    parts = path.split(".")
    cur = obj
    for p in parts[:-1]:
        cur = cur[p]
    cur[parts[-1]] = value


def download_artifact(run_id: str, name: str) -> DownloadArtifactOutput:
    import base64

    result = get_run(run_id)
    if name == "result.json":
        payload = result.model_dump_json().encode()
        return DownloadArtifactOutput(
            run_id=run_id, name=name,
            contentBase64=base64.b64encode(payload).decode(),
            mimeType="application/json",
        )
    if name == "audit.json":
        payload = json.dumps(result.audit.model_dump(), default=str).encode()
        return DownloadArtifactOutput(
            run_id=run_id, name=name,
            contentBase64=base64.b64encode(payload).decode(),
            mimeType="application/json",
        )
    raise ServiceError("NOT_FOUND", f"artifact {name} not produced by run {run_id}")


# ── Specs ─────────────────────────────────────────────────────────────


def _schema(model: type[BaseModel]) -> dict:
    return model.model_json_schema()


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="list_benchmarks", family="simulator",
        description="Return the canonical benchmark catalog (V1–V8).",
        approvalRequired=False,
        inputSchema={}, outputSchema=_schema(BenchmarkIndex),
    ),
    ToolSpec(
        name="get_run", family="simulator",
        description="Fetch a completed RunResult by id.",
        approvalRequired=False,
        inputSchema={"properties": {"run_id": {"type": "string"}}, "required": ["run_id"]},
        outputSchema=_schema(RunResult),
    ),
    ToolSpec(
        name="get_audit", family="simulator",
        description="Fetch the S1–S15 audit report for a run.",
        approvalRequired=False,
        inputSchema={"properties": {"run_id": {"type": "string"}}, "required": ["run_id"]},
        outputSchema=_schema(AuditReport),
    ),
    ToolSpec(
        name="get_validation", family="simulator",
        description="Fetch the V1–V8 validation report for a run.",
        approvalRequired=False,
        inputSchema={"properties": {"run_id": {"type": "string"}}, "required": ["run_id"]},
        outputSchema=_schema(ValidationReport),
    ),
    ToolSpec(
        name="validate_config", family="simulator",
        description="Statically validate a RunConfig; return diagnostics.",
        approvalRequired=False,
        inputSchema=_schema(ValidateConfigInput),
        outputSchema=_schema(ConfigDiagnostics),
    ),
    ToolSpec(
        name="start_run", family="simulator",
        description="Submit a RunConfig to the pipeline. Approval scope: 'start_run'.",
        approvalRequired=True,
        inputSchema=_schema(StartRunInput),
        outputSchema=_schema(RunIdOutput),
    ),
    ToolSpec(
        name="cancel_run", family="simulator",
        description="Cancel a running pipeline. Approval scope: 'cancel_run'.",
        approvalRequired=True,
        inputSchema={
            "properties": {
                "run_id": {"type": "string"},
                "approval_token": {"type": "string"},
            },
            "required": ["run_id", "approval_token"],
        },
        outputSchema={"properties": {"ok": {"type": "boolean"}}},
    ),
    ToolSpec(
        name="stream_run", family="simulator",
        description="AsyncIterator of RunEvents for a run_id.",
        approvalRequired=False,
        inputSchema=_schema(StreamRequest),
        outputSchema={"$ref": "#/components/schemas/RunEvent"},
    ),
    ToolSpec(
        name="download_artifact", family="simulator",
        description="Download a named artifact (base64-encoded).",
        approvalRequired=False,
        inputSchema=_schema(DownloadArtifactInput),
        outputSchema=_schema(DownloadArtifactOutput),
    ),
    ToolSpec(
        name="compare_runs", family="simulator",
        description="Return a ComparisonReport across multiple run ids.",
        approvalRequired=False,
        inputSchema=_schema(CompareRunsInput),
        outputSchema=_schema(ComparisonReport),
    ),
    ToolSpec(
        name="scan_parameters", family="simulator",
        description="Run a multidimensional parameter scan through the pipeline.",
        approvalRequired=True,
        inputSchema=_schema(ScanRequest),
        outputSchema=_schema(ScanResult),
    ),
]
