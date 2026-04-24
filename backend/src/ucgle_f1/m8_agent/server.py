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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..domain import (
    AssistantEvent,
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
    yield


def build_app() -> FastAPI:
    app = FastAPI(
        title="UCGLE-F1 Agent Orchestrator",
        version="0.1.0",
        lifespan=_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # dev; tighten via Hydra config in prod
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(mcp_server.build_router())
    _mount_rest(app)
    _mount_chat(app)
    _mount_approvals(app)
    _mount_models(app)
    return app


# ─── REST mirrors of the frontend service layer ───────────────────────


def _mount_rest(app: FastAPI) -> None:
    from .mcp_server import _dispatch

    @app.get("/api/benchmarks")
    def benchmarks() -> dict:
        return _dispatch("list_benchmarks", {})

    @app.get("/api/runs/{run_id}")
    def runs(run_id: str) -> dict:
        try:
            return _dispatch("get_run", {"run_id": run_id})
        except ServiceError as e:
            raise HTTPException(404, detail=e.to_dict()) from e

    @app.get("/api/runs/{run_id}/audit")
    def audit(run_id: str) -> dict:
        return _dispatch("get_audit", {"run_id": run_id})

    @app.post("/api/runs")
    async def start(cfg: dict) -> dict:
        # Delegate to start_run with the approval_token extracted from
        # a header-populated field; the frontend passes it in the body.
        from .tools.simulator import start_run
        try:
            config = RunConfig.model_validate(cfg["config"])
            out = await start_run(config, approval_token=cfg.get("approval_token", ""))
            return {"runId": out.run_id}
        except ServiceError as e:
            raise HTTPException(_status(e), detail=e.to_dict()) from e

    @app.get("/api/runs/{run_id}/stream")
    async def stream(run_id: str) -> EventSourceResponse:
        async def gen() -> AsyncIterator[dict]:
            async for ev in get_registry().stream(run_id):
                yield {"event": ev.type, "data": ev.model_dump_json()}
        return EventSourceResponse(gen())


class IssueReq(BaseModel):
    scopes: list[str]
    ttl_seconds: int | None = 3600


def _mount_approvals(app: FastAPI) -> None:

    @app.post("/api/approvals")
    def issue(req: IssueReq) -> dict:
        tok = get_store().issue_approval(req.scopes, req.ttl_seconds)
        return {"tokenId": tok.tokenId, "scopes": tok.scopes,
                "expiresAt": tok.expiresAt.isoformat() if tok.expiresAt else None}


def _mount_models(app: FastAPI) -> None:

    @app.get("/api/models")
    def _list() -> list[dict]:
        return [m.model_dump() for m in list_models()]

    @app.get("/api/models/{mid}/status")
    def _status(mid: str) -> dict:
        return model_status(mid).model_dump()

    @app.post("/api/models/{mid}/install")
    async def _install(mid: str) -> EventSourceResponse:
        async def gen() -> AsyncIterator[dict]:
            async for ev in install_model(mid):
                yield {"event": ev.type, "data": ev.model_dump_json()}
        return EventSourceResponse(gen())

    @app.delete("/api/models/{mid}")
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

    @app.post("/v1/chat")
    async def chat(req: ChatRequest) -> EventSourceResponse:
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
                        out = _dispatch(call.name, call.arguments)
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
    return {
        "NOT_FOUND": 404, "INVALID_INPUT": 422,
        "APPROVAL_REQUIRED": 403, "AUDIT_VIOLATION": 409,
        "UPSTREAM_FAILURE": 502, "STREAM_ABORTED": 499,
        "NOT_IMPLEMENTED": 501,
    }.get(e.code, 500)


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
