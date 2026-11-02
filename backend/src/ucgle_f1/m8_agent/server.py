"""FastAPI app: /v1/chat (SSE), /mcp, /api/* mirrors of frontend.

The /v1/chat endpoint streams tool-call and assistant tokens on a
single SSE channel so the UI can interleave them. Both /v1/chat and
/mcp/tools/{name} end up calling the exact same functions — there is
no divergent code path.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from sse_starlette.sse import EventSourceResponse

from ..domain import (
    AssistantEvent,
    AuditReport,
    BenchmarkIndex,
    ModelDescriptor,
    ModelStatus,
    RunResult,
    ChatMessage,
    MessageCompleteEvent,
    RunConfig,
    ServiceError,
    TokenEvent,
    ToolCall,
    ToolCallEvent,
    ToolResult,
    ToolResultEvent,
)
from . import mcp_server
from .api_errors import (
    BodySizeLimitMiddleware,
    ErrorEnvelope,
    install_error_handlers,
    invalid_input,
    status_for,
)
from .api_models import SSE_RESPONSES, ApprovalResponse, OkResponse, StartRunResponse
from .health import mount_health
from .settings import cors_origins
from .principal import Principal, require_scope
from .memory import get_store
from .models import ProviderConfig, get_provider
from .models.base import Message
from .models.registry import install_model, list_models, model_status, uninstall_model
from .prompts import build_system_prompt
from .runs import get_registry
from .tools import ALL_TOOL_SPECS


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Touch the memory store so the DB is created eagerly.
    get_store()
    # PROMPT 10 v2 §A / P3-05: the tenant-budget hook on the router's
    # PricingEngine (no-op when qcompass-router isn't installed).
    from .auth import install_budget_hook

    install_budget_hook()
    yield


def build_app() -> FastAPI:
    app = FastAPI(
        title="UCGLE-F1 Agent Orchestrator",
        version="0.1.0",
        lifespan=_lifespan,
        # One error envelope on every route (P3-06); 422 is listed so
        # FastAPI documents our envelope instead of its own validation body.
        responses={
            422: {"model": ErrorEnvelope, "description": "Invalid input."},
            "4XX": {"model": ErrorEnvelope, "description": "Client error."},
            "5XX": {"model": ErrorEnvelope, "description": "Server error."},
        },
    )
    # P3-06: CORS allowlist from QCOMPASS_CORS_ORIGINS (see settings.py).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-QCompass-Tenant"],
    )
    app.add_middleware(BodySizeLimitMiddleware)
    install_error_handlers(app)
    mount_health(app)
    app.include_router(mcp_server.build_router())
    _mount_rest(app)
    _mount_chat(app)
    _mount_approvals(app)
    _mount_models(app)
    # PROMPT 8 v2 §A: qcompass HTTP / WS surface + scan persistence.
    # Soft-imports the route modules so a stale build still starts.
    try:
        from . import contract_routes, qcompass_routes
        qcompass_routes.mount_qcompass_routes(app)
        qcompass_routes.mount_scan_routes(app)
        contract_routes.mount_contract_routes(app)
    except ImportError:  # pragma: no cover — needs the backend's qcompass extra
        import logging

        logging.getLogger(__name__).warning(
            "qcompass routes not mounted: install ucgle_f1[qcompass]", exc_info=True,
        )
    # PROMPT 10 v2 §B: Prometheus /metrics endpoint.
    try:
        from . import observability
        observability.mount_metrics_route(app)
    except Exception:  # pragma: no cover — observability is best-effort
        pass
    return app


# ─── REST mirrors of the frontend service layer ───────────────────────


def _mount_rest(app: FastAPI) -> None:
    from .mcp_server import _dispatch

    @app.get("/api/benchmarks", response_model=BenchmarkIndex)
    def benchmarks() -> dict:
        return _dispatch("list_benchmarks", {})

    # SEC-H1: every route takes the Principal and passes its tenant down
    # explicitly; nothing relies on an ambient tenant.
    read = Depends(require_scope("read"))
    run = Depends(require_scope("run"))

    @app.get("/api/runs/{run_id}", response_model=RunResult)
    def runs(run_id: str, principal: Principal = read) -> dict:
        try:
            return _dispatch("get_run", {"run_id": run_id}, tenant=principal.tenant_id)
        except ServiceError as e:
            raise HTTPException(404, detail=e.to_dict()) from e

    @app.get("/api/runs/{run_id}/audit", response_model=AuditReport)
    def audit(run_id: str, principal: Principal = read) -> dict:
        return _dispatch("get_audit", {"run_id": run_id}, tenant=principal.tenant_id)

    @app.post("/api/runs", response_model=StartRunResponse)
    async def start(cfg: dict, principal: Principal = run) -> dict:
        # Delegate to start_run with the approval_token extracted from
        # a header-populated field; the frontend passes it in the body.
        from .tools.simulator import start_run
        try:
            config = RunConfig.model_validate(cfg["config"])
        except ValidationError as e:  # W1-PARAMS: a refused config is 422, not 500
            raise invalid_input(e, "config") from e
        try:
            out = await start_run(
                config, approval_token=cfg.get("approval_token", ""), tenant=principal.tenant_id,
            )
            return {"runId": out.run_id}
        except ServiceError as e:
            raise HTTPException(status_for(e.code), detail=e.to_dict()) from e

    @app.get(
        "/api/runs/{run_id}/stream",
        response_class=EventSourceResponse,
        responses=SSE_RESPONSES,
    )
    async def stream(run_id: str, principal: Principal = read) -> EventSourceResponse:
        tenant = principal.tenant_id
        if await asyncio.to_thread(lambda: get_registry().get(run_id, tenant=tenant)) is None:
            raise HTTPException(404, f"run {run_id} not found")
        async def gen() -> AsyncIterator[dict]:
            try:
                async for ev in get_registry().stream(run_id, tenant=tenant):
                    yield {"event": ev.type, "data": ev.model_dump_json()}
            except ServiceError as e:  # SF1: a bounded stream ends with an error event
                yield {"event": "error", "data": json.dumps(e.to_dict())}
        return EventSourceResponse(gen())


class IssueReq(BaseModel):
    scopes: list[str]
    ttl_seconds: int | None = 3600


def _mount_approvals(app: FastAPI) -> None:

    @app.post("/api/approvals", response_model=ApprovalResponse)
    def issue(req: IssueReq, principal: Principal = Depends(require_scope("run"))) -> dict:
        # SF4: the token belongs to the caller's tenant and verifies only there.
        tok = get_store().issue_approval(req.scopes, req.ttl_seconds, tenant=principal.tenant_id)
        # The store keeps scopes comma-joined; the API returns the list.
        scopes = [sc for sc in tok.scopes.split(",") if sc]
        return {"tokenId": tok.tokenId, "scopes": scopes,
                "expiresAt": tok.expiresAt.isoformat() if tok.expiresAt else None}


def _mount_models(app: FastAPI) -> None:

    read = Depends(require_scope("read"))
    admin = Depends(require_scope("admin"))

    @app.get("/api/models", response_model=list[ModelDescriptor], dependencies=[read])
    def _list() -> list[dict]:
        return [m.model_dump() for m in list_models()]

    @app.get("/api/models/{mid}/status", response_model=ModelStatus, dependencies=[read])
    def _status(mid: str) -> dict:
        return model_status(mid).model_dump()

    @app.post(
        "/api/models/{mid}/install",
        response_class=EventSourceResponse,
        responses=SSE_RESPONSES,
        dependencies=[admin],
    )
    async def _install(mid: str) -> EventSourceResponse:
        async def gen() -> AsyncIterator[dict]:
            async for ev in install_model(mid):
                yield {"event": ev.type, "data": ev.model_dump_json()}
        return EventSourceResponse(gen())

    @app.delete("/api/models/{mid}", response_model=OkResponse, dependencies=[admin])
    def _uninstall(mid: str) -> dict:
        uninstall_model(mid)
        return {"ok": True}


# ─── Unified /v1/chat endpoint ────────────────────────────────────────


class ChatRequest(BaseModel):
    conversationId: str
    messages: list[ChatMessage]
    modelId: str
    runContext: dict[str, Any] | None = None
    provider: str = "anthropic"
    temperature: float = 0.0
    seed: int = 0


def _mount_chat(app: FastAPI) -> None:

    @app.post(
        "/v1/chat",
        response_class=EventSourceResponse,
        responses=SSE_RESPONSES,
    )
    async def chat(
        req: ChatRequest, principal: Principal = Depends(require_scope("run")),
    ) -> EventSourceResponse:
        cfg = ProviderConfig(
            model_id=req.modelId, provider=req.provider,  # type: ignore[arg-type]
            temperature=req.temperature, seed=req.seed,
        )
        provider = get_provider(cfg)

        # Compose system prompt from live tool specs.
        system = Message(role="system", content=build_system_prompt(ALL_TOOL_SPECS))
        convo = [system] + [Message(role=m.role, content=m.content) for m in req.messages]  # type: ignore[arg-type]

        tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema,
                },
            }
            for t in ALL_TOOL_SPECS
        ]

        async def event_stream() -> AsyncIterator[dict]:
            from .mcp_server import _dispatch

            buffered_tokens: list[str] = []
            async for ev in provider.stream(convo, tool_schemas):
                if ev.type == "token" and ev.delta:
                    buffered_tokens.append(ev.delta)
                    yield _sse(TokenEvent(delta=ev.delta))
                elif ev.type == "tool_call" and ev.tool_call:
                    call = ToolCall(
                        id=ev.tool_call.get("id") or "call_local",
                        name=ev.tool_call["name"],
                        arguments=ev.tool_call["arguments"] or {},
                    )
                    yield _sse(ToolCallEvent(call=call))
                    try:
                        out = _dispatch(call.name, call.arguments, tenant=principal.tenant_id)
                        result = ToolResult(id=call.id, ok=True, output=out)
                    except ServiceError as e:
                        result = ToolResult(
                            id=call.id, ok=False, output=e.to_dict(),
                        )
                    except Exception as e:  # noqa: BLE001
                        result = ToolResult(
                            id=call.id, ok=False,
                            output={"code": "UPSTREAM_FAILURE", "message": str(e)},
                        )
                    get_store().record_tool_call(
                        conversation_id=req.conversationId,
                        tool=call.name,
                        request=call.arguments,
                        response={"ok": result.ok, "output": result.output},
                        ok=result.ok,
                        tenant=principal.tenant_id,
                    )
                    yield _sse(ToolResultEvent(result=result))
                elif ev.type == "finish":
                    msg = ChatMessage(
                        id=f"m_{datetime.now(UTC).timestamp()}",
                        role="assistant",
                        content="".join(buffered_tokens),
                        createdAt=datetime.now(UTC),
                        modelId=req.modelId,
                    )
                    yield _sse(MessageCompleteEvent(message=msg))
                    return
                elif ev.type == "error":
                    yield {"event": "error", "data": json.dumps({"message": ev.error})}
                    return

        return EventSourceResponse(event_stream())


def _sse(event: AssistantEvent) -> dict[str, Any]:
    return {"event": event.type, "data": event.model_dump_json()}


def _status(e: ServiceError) -> int:
    """Kept for callers/tests; delegates to the single table (R20)."""
    return status_for(e.code)


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "ucgle_f1.m8_agent.server:build_app",
        host=args.host, port=args.port,
        factory=True, reload=args.reload,
    )


_ = asyncio  # keep import for tests that monkeypatch it
