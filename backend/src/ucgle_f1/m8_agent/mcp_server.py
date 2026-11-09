"""Thin MCP-style tool server.

Exposes every tool at /tools/{family}/{name} plus a ``/mcp/tools``
endpoint that lists the full OpenAPI schema. We deliberately do not
hard-code MCP protocol details; the ``mcp`` Python package can wrap
this surface when present, but the server is usable standalone.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from ..domain import ConfigDiagnostic, ConfigDiagnostics, RunConfig, ServiceError, ToolSpec
from .api_errors import status_for
from .api_models import ToolInvocationResponse
from .principal import Principal, require_scope
from .tools import ALL_TOOL_SPECS
from .tools import introspection as _intros
from .tools import patch as _patch
from .tools import research as _research
from .tools import simulator as _sim


def _run_coroutine(coro: Any) -> Any:
    """Run an async tool from sync dispatch.

    Callers on an event loop must not call ``_dispatch`` there: /v1/chat runs
    it in ``asyncio.to_thread`` (round 2, c1), and /mcp/tools/* is a sync
    route (FastAPI's threadpool), so the first branch is the one taken. The
    second only guards a direct call made from a loop's thread, which blocks
    that thread until the tool finishes.
    """
    import asyncio
    import concurrent.futures
    import contextvars

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    ctx = contextvars.copy_context()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(ctx.run, asyncio.run, coro).result()


def _dispatch(name: str, payload: dict[str, Any], *, tenant: str | None = None) -> Any:
    """Route ``name`` to its implementation.

    ``tenant`` is the caller's tenant (``Principal.tenant_id``); every
    run-reading tool is scoped to it (SEC-H1). HTTP and chat callers always
    pass it; ``None`` is for in-process use (``resolve_tenant_slug``).
    Outputs are JSON-mode dumps: they are returned as JSON (ToolInvocationResponse).
    """
    # Simulator
    if name == "list_benchmarks":
        return _sim.list_benchmarks().model_dump(mode="json")
    if name == "get_run":
        return _sim.get_run(payload["run_id"], tenant=tenant).model_dump(mode="json")
    if name == "get_audit":
        return _sim.get_audit(payload["run_id"], tenant=tenant).model_dump(mode="json")
    if name == "get_validation":
        return _sim.get_validation(payload["run_id"], tenant=tenant).model_dump(mode="json")
    if name == "validate_config":
        return _validate_config(payload, tenant=tenant).model_dump(mode="json")
    if name == "compare_runs":
        return _sim.compare_runs(payload["ids"], tenant=tenant).model_dump(mode="json")
    if name == "cancel_run":
        # B1: an approval-gated write, scoped to the caller's tenant.
        return _run_coroutine(_sim.cancel_run(
            payload["run_id"], payload.get("approval_token", ""), tenant=tenant,
        ))
    if name == "download_artifact":
        return _sim.download_artifact(payload["run_id"], payload["name"], tenant=tenant).model_dump(mode="json")

    # Research
    if name == "propose_experiments":
        return _research.propose_experiments(
            hypothesis=payload["hypothesis"],
            constraints=payload.get("constraints"),
            budget=payload.get("budget"),
        ).model_dump(mode="json")
    if name == "record_hypothesis":
        return _research.record_hypothesis(
            conversation_id=payload["conversation_id"],
            text=payload["text"],
            tenant=tenant,
        ).model_dump(mode="json")
    if name == "cite_paper":
        return _research.cite_paper(payload["arxiv_id"]).model_dump(mode="json")
    if name == "explain_audit":
        return _research.explain_audit(payload["run_id"], payload["check_id"], tenant=tenant).model_dump(mode="json")
    if name == "summarize_literature":
        return _research.summarize_literature(payload["topic"], payload.get("k", 5)).model_dump(mode="json")
    if name == "suggest_next_parameter_scan":
        return _research.suggest_next_parameter_scan(payload["run_id"], tenant=tenant).model_dump(mode="json")

    # Patch
    if name == "propose_patch":
        return _patch.propose_patch(
            conversation_id=payload["conversation_id"],
            target_path=payload["target_path"],
            rationale=payload["rationale"],
            unified_diff=payload["unified_diff"],
            tenant=tenant,
        ).model_dump(mode="json")
    if name == "dry_run_patch":
        return _patch.dry_run_patch(
            patch_id=payload["patch_id"],
            in_docker=payload.get("in_docker", True),
            tenant=tenant,
        ).model_dump(mode="json")
    if name == "request_human_review":
        return _patch.request_human_review(payload["patch_id"], tenant=tenant).model_dump(mode="json")

    # Introspection
    if name == "list_tools":
        return [t.model_dump(mode="json") for t in _intros.list_tools()]
    if name == "describe_tool":
        return _intros.describe_tool(payload["name"]).model_dump(mode="json")
    if name == "get_capabilities":
        return _intros.get_capabilities().model_dump(mode="json")

    raise ServiceError("NOT_FOUND", f"no tool '{name}'")


def _validate_config(payload: dict[str, Any], *, tenant: str | None = None) -> ConfigDiagnostics:
    """validate_config's answer for any payload: a config the models refuse
    (e.g. ambiguous potential parameters) is diagnostics, not a 500 (W1 API3)."""
    try:
        cfg = RunConfig.model_validate(payload.get("config"))
    except ValidationError as exc:
        errors = exc.errors(include_url=False, include_context=False, include_input=False)
        return ConfigDiagnostics(valid=False, diagnostics=[
            ConfigDiagnostic(
                severity="error",
                path=".".join(str(x) for x in e["loc"]) or "config",
                message=str(e["msg"]).removeprefix("Value error, "),
            )
            for e in errors
        ])
    return _sim.validate_config(cfg, tenant=tenant)


def build_router() -> APIRouter:
    router = APIRouter(prefix="/mcp")

    @router.get("/tools", response_model=list[ToolSpec], dependencies=[Depends(require_scope("read"))])
    def _list_tools() -> list[dict]:
        return [t.model_dump() for t in ALL_TOOL_SPECS]

    @router.post("/tools/{name}", response_model=ToolInvocationResponse)
    def _invoke(
        name: str, payload: dict[str, Any], principal: Principal = Depends(require_scope("run")),
    ) -> dict[str, Any]:
        try:
            result = _dispatch(name, payload, tenant=principal.tenant_id)
            return {"ok": True, "output": result}
        except ServiceError as e:
            raise HTTPException(
                status_code=status_for(e.code),
                detail=e.to_dict(),
            ) from e

    return router


def _status_for(code: str) -> int:
    """Kept for callers; delegates to the single table (R20)."""
    return status_for(code)
