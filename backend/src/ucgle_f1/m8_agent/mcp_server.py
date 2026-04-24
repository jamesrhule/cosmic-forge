"""Thin MCP-style tool server.

Exposes every tool at /tools/{family}/{name} plus a ``/mcp/tools``
endpoint that lists the full OpenAPI schema. We deliberately do not
hard-code MCP protocol details; the ``mcp`` Python package can wrap
this surface when present, but the server is usable standalone.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..domain import ServiceError
from .tools import ALL_TOOL_SPECS
from .tools import introspection as _intros
from .tools import patch as _patch
from .tools import research as _research
from .tools import simulator as _sim


def _dispatch(name: str, payload: dict[str, Any]) -> Any:
    """Route ``name`` to its implementation."""
    # Simulator
    if name == "list_benchmarks":
        return _sim.list_benchmarks().model_dump()
    if name == "get_run":
        return _sim.get_run(payload["run_id"]).model_dump()
    if name == "get_audit":
        return _sim.get_audit(payload["run_id"]).model_dump()
    if name == "get_validation":
        return _sim.get_validation(payload["run_id"]).model_dump()
    if name == "validate_config":
        from ..domain import RunConfig
        return _sim.validate_config(RunConfig.model_validate(payload["config"])).model_dump()
    if name == "compare_runs":
        return _sim.compare_runs(payload["ids"]).model_dump()
    if name == "download_artifact":
        return _sim.download_artifact(payload["run_id"], payload["name"]).model_dump()

    # Research
    if name == "propose_experiments":
        return _research.propose_experiments(
            hypothesis=payload["hypothesis"],
            constraints=payload.get("constraints"),
            budget=payload.get("budget"),
        ).model_dump()
    if name == "record_hypothesis":
        return _research.record_hypothesis(
            conversation_id=payload["conversation_id"],
            text=payload["text"],
        ).model_dump()
    if name == "cite_paper":
        return _research.cite_paper(payload["arxiv_id"]).model_dump()
    if name == "explain_audit":
        return _research.explain_audit(payload["run_id"], payload["check_id"]).model_dump()
    if name == "summarize_literature":
        return _research.summarize_literature(payload["topic"], payload.get("k", 5)).model_dump()
    if name == "suggest_next_parameter_scan":
        return _research.suggest_next_parameter_scan(payload["run_id"]).model_dump()

    # Patch
    if name == "propose_patch":
        return _patch.propose_patch(
            conversation_id=payload["conversation_id"],
            target_path=payload["target_path"],
            rationale=payload["rationale"],
            unified_diff=payload["unified_diff"],
        ).model_dump()
    if name == "dry_run_patch":
        return _patch.dry_run_patch(
            patch_id=payload["patch_id"],
            in_docker=payload.get("in_docker", True),
        ).model_dump()
    if name == "request_human_review":
        return _patch.request_human_review(payload["patch_id"]).model_dump()

    # Introspection
    if name == "list_tools":
        return [t.model_dump() for t in _intros.list_tools()]
    if name == "describe_tool":
        return _intros.describe_tool(payload["name"]).model_dump()
    if name == "get_capabilities":
        return _intros.get_capabilities().model_dump()

    raise ServiceError("NOT_FOUND", f"no tool '{name}'")


def build_router() -> APIRouter:
    router = APIRouter(prefix="/mcp")

    @router.get("/tools")
    def _list_tools() -> list[dict]:
        return [t.model_dump() for t in ALL_TOOL_SPECS]

    @router.post("/tools/{name}")
    def _invoke(name: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result = _dispatch(name, payload)
            return {"ok": True, "output": result}
        except ServiceError as e:
            raise HTTPException(
                status_code=_status_for(e.code),
                detail=e.to_dict(),
            ) from e

    return router


def _status_for(code: str) -> int:
    return {
        "NOT_FOUND": 404,
        "INVALID_INPUT": 422,
        "APPROVAL_REQUIRED": 403,
        "AUDIT_VIOLATION": 409,
        "UPSTREAM_FAILURE": 502,
        "STREAM_ABORTED": 499,
        "NOT_IMPLEMENTED": 501,
    }.get(code, 500)
