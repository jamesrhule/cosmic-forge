"""Simulator tools: list_benchmarks, start_run, stream_run, ...

Every function here is typed (Pydantic in/out) and idempotent.
Write-effecting tools (start_run, cancel_run) require an
``approval_token`` carrying the appropriate scope. The token is
verified against :func:`ConversationStore.consume_approval`.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import AsyncIterator

from pydantic import BaseModel, ValidationError

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
    potential_forms_text,
)
from ...m2_scalar.check import CompileCapacityError, check_potential
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


# Tenant-scoped tools take ``tenant`` (the principal's tenant, SEC-H1). The
# HTTP and chat paths always pass it; ``None`` means the bound tenant, or the
# dev tenant under QCOMPASS_ENV=dev only (``principal.resolve_tenant_slug``).


def get_run(run_id: str, *, tenant: str | None = None) -> RunResult:
    r = get_registry().result(run_id, tenant=tenant)
    if r is None:
        raise ServiceError("NOT_FOUND", f"run {run_id} not found")
    return r


def get_audit(run_id: str, *, tenant: str | None = None) -> AuditReport:
    return get_run(run_id, tenant=tenant).audit


def get_validation(run_id: str, *, tenant: str | None = None) -> ValidationReport:
    return get_run(run_id, tenant=tenant).validation


def validate_config(
    cfg: RunConfig, *, tenant: str | None = None, potential_checks: dict[str, str | None] | None = None,
) -> ConfigDiagnostics:
    """Static checks of a RunConfig, and whether its potential would run (W1 API3).

    The potential must have every parameter of its form
    (``Potential.missing_params``) and pass
    :func:`ucgle_f1.m2_scalar.check.check_potential` (compiles with every
    parameter bound, has a starting field value; a custom potential is
    compiled in a time-limited child process). ``start_run`` (and so
    ``POST /api/runs``) and ``scan_parameters`` refuse an invalid config
    before they spend an approval. The compile counts against ``tenant``'s
    share of compile slots; a refusal for capacity is not a diagnostic but a
    ``CompileCapacityError`` (503/429 with Retry-After, W1 R4-API).
    ``potential_checks`` memoises the potential check across calls (a scan):
    potential JSON → None (accepted) or the refusal message.
    """
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
    pot = cfg.potential
    missing = pot.missing_params()
    if missing:
        diags.append(ConfigDiagnostic(
            severity="error", path="potential.params",
            message=f"{pot.kind} potential: missing {', '.join(missing)}; {potential_forms_text(pot.kind)}",
        ))
    elif pot.kind != "custom" or pot.customPython:
        memo = pot.model_dump_json()
        if potential_checks is not None and memo in potential_checks:
            refusal = potential_checks[memo]
        else:
            try:
                check_potential(pot, tenant=tenant)
                refusal = None
            except CompileCapacityError:
                raise  # the server's capacity, not the config: answered 503/429
            except ValueError as exc:
                refusal = str(exc)
            if potential_checks is not None:
                potential_checks[memo] = refusal
        if refusal is not None:
            diags.append(ConfigDiagnostic(
                severity="error", path="potential.customPython" if pot.kind == "custom" else "potential",
                message=refusal,
            ))
    if cfg.precision == "high" and cfg.couplings.xi == 0.0:
        diags.append(ConfigDiagnostic(
            severity="info", path="couplings.xi",
            message="xi=0 with precision=high is unusual — GB sector is inert",
        ))
    valid = not any(d.severity == "error" for d in diags)
    return ConfigDiagnostics(valid=valid, diagnostics=diags, normalized=cfg if valid else None)


async def start_run(cfg: RunConfig, approval_token: str, *, tenant: str | None = None) -> RunIdOutput:
    """Validate, then spend the approval, then enqueue (round 2, c4).

    A refused request never spends the token, as in ``cancel_run``.
    """
    store = get_store()
    # A6: every agent-initiated run MUST carry (conversationId, hypothesisId),
    # and the hypothesis must be one this tenant recorded (record_hypothesis).
    if cfg.agent is None or not cfg.agent.conversationId or not cfg.agent.hypothesisId:
        raise ServiceError(
            "AUDIT_VIOLATION",
            "RunConfig.agent.{conversationId,hypothesisId} required for agent runs (A6)",
        )
    hypothesis = await asyncio.to_thread(
        store.get_hypothesis, cfg.agent.hypothesisId, tenant=tenant,
    )
    if hypothesis is None:
        raise ServiceError(
            "AUDIT_VIOLATION",
            "RunConfig.agent.hypothesisId must name a hypothesis recorded in this tenant "
            "(record_hypothesis) (A6)",
        )
    diags = await asyncio.to_thread(validate_config, cfg, tenant=tenant)  # may compile a potential
    if not diags.valid:
        raise ServiceError("INVALID_INPUT", f"config invalid: {_errors(diags)}")
    spent = await asyncio.to_thread(
        store.consume_approval, approval_token, "start_run", tenant=tenant,
    )
    if not spent:
        raise ServiceError("APPROVAL_REQUIRED",
                           "valid approval_token with scope 'start_run' required")
    rid = await get_registry().submit(cfg, tenant=tenant)
    store.link_run(rid, cfg.agent.conversationId, cfg.agent.hypothesisId, tenant=tenant)
    return RunIdOutput(run_id=rid)


async def cancel_run(run_id: str, approval_token: str, *, tenant: str | None = None) -> dict[str, bool]:
    registry = get_registry()
    # B1: another tenant's run (or none) is NOT_FOUND, before the approval
    # is spent; a run that already ended answers ok=False.
    if await asyncio.to_thread(lambda: registry.get(run_id, tenant=tenant)) is None:
        raise ServiceError("NOT_FOUND", f"run {run_id} not found")
    spent = await asyncio.to_thread(
        get_store().consume_approval, approval_token, "cancel_run", tenant=tenant,
    )
    if not spent:
        raise ServiceError("APPROVAL_REQUIRED", "approval required for cancel_run")
    ok = await registry.cancel(run_id, tenant=tenant)
    return {"ok": ok}


async def stream_run(run_id: str, *, tenant: str | None = None) -> AsyncIterator[RunEvent]:
    async for ev in get_registry().stream(run_id, tenant=tenant):
        yield ev


def compare_runs(ids: list[str], *, tenant: str | None = None) -> ComparisonReport:
    results = [get_run(i, tenant=tenant) for i in ids]
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


def _errors(diags: ConfigDiagnostics) -> list[str]:
    return [f"{d.path}: {d.message}" for d in diags.diagnostics if d.severity == "error"]


def _scan_cells(spec: ScanSpec, *, tenant: str | None = None) -> list[tuple[dict[str, float], RunConfig]]:
    """Every cell's coordinates and RunConfig, each one validated (R2-START-ORDER).

    Raises ServiceError INVALID_INPUT for an axis that cannot be swept or a
    cell whose config is invalid, so the scan is refused before its
    approval is spent. ``ScanSpec`` caps the cells (``MAX_SCAN_CELLS``); each
    distinct config is validated once, and each distinct potential compiled
    once (W1 R4-API: a couplings axis no longer recompiles the potential).
    """
    from itertools import product

    import numpy as np

    for a in spec.axes:
        if a.points < 1 or not (np.isfinite(a.min) and np.isfinite(a.max)):
            raise ServiceError("INVALID_INPUT", f"scan axis {a.name!r}: points >= 1 and finite bounds")
        if a.log and not (a.min > 0 and a.max > 0):
            raise ServiceError("INVALID_INPUT", f"scan axis {a.name!r}: a log axis needs positive bounds")
    axis_values = [
        np.linspace(a.min, a.max, a.points) if not a.log
        else np.logspace(np.log10(a.min), np.log10(a.max), a.points)
        for a in spec.axes
    ]
    cells: list[tuple[dict[str, float], RunConfig]] = []
    checked: dict[str, ConfigDiagnostics] = {}
    potential_checks: dict[str, str | None] = {}
    for combo in product(*axis_values):
        coords = {a.name: float(v) for a, v in zip(spec.axes, combo)}
        cfg_dict = spec.base.model_dump()
        try:
            for axis, value in zip(spec.axes, combo):
                _set_path(cfg_dict, axis.path, float(value))
            cfg = RunConfig.model_validate(cfg_dict)
        except (KeyError, TypeError, ValidationError) as exc:
            raise ServiceError("INVALID_INPUT", f"scan cell {coords}: {exc}") from exc
        key = cfg.model_dump_json(exclude={"agent"})
        if key not in checked:  # one check per distinct config, one compile per potential
            checked[key] = validate_config(cfg, tenant=tenant, potential_checks=potential_checks)
        diags = checked[key]
        if not diags.valid:
            raise ServiceError("INVALID_INPUT", f"scan cell {coords}: config invalid: {_errors(diags)}")
        cells.append((coords, cfg))
    return cells


async def scan_parameters(spec: ScanSpec, approval_token: str, *, tenant: str | None = None) -> ScanResult:
    """Validate every cell, then spend the approval, then run (R2-START-ORDER).

    A refused scan never spends the token, as in ``start_run``. A token that
    could not be spent is refused first, before any cell is validated (W1
    R4-API: validating costs a compile per distinct potential); the spend
    after validation is still the one that counts.
    """
    store = get_store()
    usable = await asyncio.to_thread(
        store.approval_is_valid, approval_token, "scan_parameters", tenant=tenant,
    )
    if not usable:
        raise ServiceError("APPROVAL_REQUIRED",
                           "approval required for scan_parameters")
    cells_in = await asyncio.to_thread(_scan_cells, spec, tenant=tenant)
    spent = await asyncio.to_thread(
        store.consume_approval, approval_token, "scan_parameters", tenant=tenant,
    )
    if not spent:
        raise ServiceError("APPROVAL_REQUIRED",
                           "approval required for scan_parameters")
    cells: list[ScanCell] = []
    for coords, cfg in cells_in:
        # Scans run sequentially on the same pipeline for reproducibility.
        from ..runs import RunPipeline
        pr = RunPipeline(seed=0).run(cfg)
        cells.append(_scan_cell(coords, pr))
    return ScanResult(
        id=f"scan_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        spec=spec,
        cells=cells,
        createdAt=datetime.now(UTC),
    )


def _scan_cell(coords: dict[str, float], pr) -> ScanCell:  # type: ignore[no-untyped-def]
    """One scan cell. A refused η_B (``eta_B_refusal``, the rule
    ``RunResult.eta_B`` uses) is NaN, serialised as null, never the raw value."""
    import numpy as np

    from ...m7_infer import pipeline as _pipeline

    eta_b = float("nan") if _pipeline.eta_B_refusal(pr) is not None else float(pr.eta_B)
    return ScanCell(
        coords=coords,
        eta_B=eta_b,
        F_GB=float(np.mean(pr.modes.F_GB_per_mode())),
        status="completed",
    )


def _set_path(obj: dict, path: str, value: float) -> None:
    parts = path.split(".")
    cur = obj
    for p in parts[:-1]:
        cur = cur[p]
    cur[parts[-1]] = value


def download_artifact(run_id: str, name: str, *, tenant: str | None = None) -> DownloadArtifactOutput:
    import base64

    result = get_run(run_id, tenant=tenant)
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
