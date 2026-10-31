"""One error envelope for every route (P3-06).

Every non-2xx response, from a raised ``ServiceError``, an ``HTTPException``,
a request-validation failure, an oversized body or an unexpected exception,
has the same shape::

    {"detail": {"code": "<MACHINE_CODE>", "message": "<text>", "errors": [...]?}}

``code``/``message`` are the ``ServiceError`` shape in ``ucgle_f1.domain``
(mirrored by the frontend). The outer ``detail`` key keeps FastAPI's
convention, which the A8 audit and existing clients already read.

``HTTP_STATUS_FOR_CODE`` is the single code→status table; route modules
import it instead of keeping their own copies (R20).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from sqlalchemy.exc import OperationalError

from ..db.engine import DatabaseNotConfigured
from ..domain import ServiceError

log = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """``ServiceError`` shape: a machine-readable code and a message."""

    code: str = Field(description="Machine-readable error code, e.g. NOT_FOUND.")
    message: str = Field(description="Human-readable explanation.")
    errors: list[dict[str, Any]] | None = Field(
        default=None, description="Field-level problems for INVALID_INPUT."
    )


class ErrorEnvelope(BaseModel):
    """Body of every non-2xx response."""

    detail: ErrorDetail


HTTP_STATUS_FOR_CODE: dict[str, int] = {
    # ServiceError codes (domain.ServiceErrorCode)
    "NOT_FOUND": 404,
    "INVALID_INPUT": 422,
    "APPROVAL_REQUIRED": 403,
    "AUDIT_VIOLATION": 409,
    "CONFLICT": 409,
    "UPSTREAM_FAILURE": 502,
    "STREAM_ABORTED": 499,
    "NOT_IMPLEMENTED": 501,
    # Auth / tenancy (m8_agent.auth.AuthError)
    "AUTH_REQUIRED": 401,
    "AUTH_MALFORMED": 400,
    "AUTH_INVALID": 401,
    "AUTH_EXPIRED": 401,
    "TENANT_REQUIRED": 400,
    "TENANT_MISMATCH": 403,
    "FORBIDDEN": 403,
    # Limits and budgets
    "BUDGET_EXCEEDED": 402,
    # Plan limits at enqueue (P3-05, ucgle_f1.plans)
    "PLAN_RUNS_PER_MONTH_EXCEEDED": 429,
    "PLAN_CONCURRENT_JOBS_EXCEEDED": 429,
    "PLAN_GPU_REQUIRED": 402,
    "PLAN_TIMELINE_BYTES_EXCEEDED": 402,
    "PAYLOAD_TOO_LARGE": 413,
    "RATE_LIMITED": 429,
    # Generic
    "BAD_REQUEST": 400,
    "METHOD_NOT_ALLOWED": 405,
    "UNAVAILABLE": 503,
    "INTERNAL": 500,
}

_CODE_FOR_STATUS: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "AUTH_REQUIRED",
    402: "BUDGET_EXCEEDED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "AUDIT_VIOLATION",
    413: "PAYLOAD_TOO_LARGE",
    422: "INVALID_INPUT",
    429: "RATE_LIMITED",
    501: "NOT_IMPLEMENTED",
    502: "UPSTREAM_FAILURE",
    503: "UNAVAILABLE",
}


def status_for(code: str) -> int:
    return HTTP_STATUS_FOR_CODE.get(code, 500)


def invalid_input(exc: Exception, what: str) -> HTTPException:
    """422 INVALID_INPUT for a payload a model refused, naming each problem
    (W1-PARAMS: e.g. ambiguous or missing potential parameters)."""
    if isinstance(exc, ValidationError):
        errors = exc.errors(include_url=False, include_context=False, include_input=False)
        parts = []
        for e in errors:
            msg = str(e["msg"]).removeprefix("Value error, ")
            loc = ".".join(str(x) for x in e["loc"])
            parts.append(f"{loc}: {msg}" if loc else msg)
        return HTTPException(422, detail={
            "code": "INVALID_INPUT", "message": f"invalid {what}: " + "; ".join(parts),
            "errors": jsonable_encoder(errors),
        })
    return HTTPException(422, detail={"code": "INVALID_INPUT", "message": f"invalid {what}: {exc}"})


def error_response(
    status: int, code: str, message: str, errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorEnvelope(detail=ErrorDetail(code=code, message=message, errors=errors))
    return JSONResponse(
        status_code=status,
        content=body.model_dump(exclude_none=True),
        headers=headers,
    )


def _from_http_exception(exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    headers = getattr(exc, "headers", None)
    if isinstance(detail, dict) and "code" in detail:
        return error_response(
            exc.status_code,
            str(detail["code"]),
            str(detail.get("message", "")),
            detail.get("errors"),
            headers=headers,
        )
    code = _CODE_FOR_STATUS.get(exc.status_code, "INTERNAL" if exc.status_code >= 500 else "BAD_REQUEST")
    return error_response(exc.status_code, code, str(detail), headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    """Route every error path through :class:`ErrorEnvelope`."""

    @app.exception_handler(StarletteHTTPException)
    async def _http(_req: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _from_http_exception(exc)

    @app.exception_handler(RequestValidationError)
    async def _validation(_req: Request, exc: RequestValidationError) -> JSONResponse:
        errors = jsonable_encoder(exc.errors())
        return error_response(422, "INVALID_INPUT", "request validation failed", errors)

    @app.exception_handler(ServiceError)
    async def _service(_req: Request, exc: ServiceError) -> JSONResponse:
        return error_response(status_for(exc.code), exc.code, str(exc))

    @app.exception_handler(DatabaseNotConfigured)
    async def _no_db(_req: Request, exc: DatabaseNotConfigured) -> JSONResponse:
        # R9: a missing secret degrades to 503 naming it; never a crash.
        return error_response(503, "UNAVAILABLE", str(exc))

    @app.exception_handler(OperationalError)
    async def _db_down(req: Request, exc: OperationalError) -> JSONResponse:
        log.warning("database unavailable on %s %s: %s", req.method, req.url.path, exc.__class__.__name__)
        return error_response(503, "UNAVAILABLE", "database unavailable")

    @app.exception_handler(Exception)
    async def _unexpected(req: Request, exc: Exception) -> JSONResponse:
        # Never echo internals to the client; the log keeps the traceback.
        log.exception("unhandled error on %s %s", req.method, req.url.path)
        return error_response(500, "INTERNAL", "internal server error")


# ── Request size limit ──────────────────────────────────────────


DEFAULT_MAX_BODY_BYTES = 1_048_576  # 1 MiB


def max_body_bytes() -> int:
    raw = os.environ.get("QCOMPASS_MAX_BODY_BYTES", "")
    try:
        value = int(raw) if raw else DEFAULT_MAX_BODY_BYTES
    except ValueError:
        value = DEFAULT_MAX_BODY_BYTES
    return max(1, value)


class BodySizeLimitMiddleware:
    """Reject HTTP request bodies above ``QCOMPASS_MAX_BODY_BYTES`` with 413.

    A declared ``Content-Length`` over the limit is rejected up front. A body
    without one (chunked) is read here, up to the limit, before the app sees
    it, then replayed, so a client cannot bypass the limit by omitting the
    header. WebSocket and lifespan scopes pass through.
    """

    def __init__(self, app: ASGIApp, limit: int | None = None) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = self.limit if self.limit is not None else max_body_bytes()
        declared: int | None = None
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = None
        if declared is not None:
            if declared > limit:
                await self._reject(scope, receive, send, limit)
                return
            await self.app(scope, receive, send)
            return

        # No Content-Length: buffer up to the limit, then replay.
        chunks: list[bytes] = []
        size = 0
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > limit:
                await self._reject(scope, receive, send, limit)
                return
            chunks.append(body)
            more = message.get("more_body", False)
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send, limit: int) -> None:
        response = error_response(
            413, "PAYLOAD_TOO_LARGE", f"request body exceeds {limit} bytes",
        )
        await response(scope, receive, send)


__all__ = [
    "BodySizeLimitMiddleware",
    "ErrorDetail",
    "ErrorEnvelope",
    "HTTP_STATUS_FOR_CODE",
    "error_response",
    "install_error_handlers",
    "max_body_bytes",
    "status_for",
]
