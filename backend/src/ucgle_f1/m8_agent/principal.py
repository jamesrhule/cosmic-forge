"""Who is calling, for which tenant, with which scopes (P3-04).

One dependency for every protected route, HTTP or WebSocket:

- **API key** (``Bearer qcompass-tok_…``): looked up by SHA-256 hash; bound to
  one tenant, which must equal ``X-QCompass-Tenant`` when that header is sent.
- **Supabase access token** (any other bearer): signature-verified against the
  project JWKS (``supabase_auth``); ``X-QCompass-Tenant`` is required and must
  be a ``tenant_members`` row for the user. A tenant the user doesn't belong
  to answers 404, so tenant existence never leaks.
- **Dev anonymous**: only when ``QCOMPASS_ENV=dev`` **and**
  ``QCOMPASS_DEV_ALLOW_ANONYMOUS=1``, and only when no credential is sent.
  Production builds ignore the flag.

Scopes: ``read`` < ``run`` < ``qpu``, ``admin`` (``auth.ROLE_SCOPES``).
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Literal

from fastapi import Header, HTTPException, WebSocket

from .api_errors import status_for
from .auth import (
    _TOKEN_PREFIX,
    SCOPES,
    AuthError,
    get_auth_store,
    normalize_scopes,
    require_auth,
    set_active_tenant,
)
from .settings import is_dev
from .supabase_auth import verify_supabase_token

Scope = Literal["read", "run", "qpu", "admin"]
DEV_TENANT = "dev"


@dataclass(frozen=True)
class Principal:
    kind: Literal["api_key", "supabase", "dev"]
    subject: str
    tenant_id: str
    scopes: frozenset[str]


def dev_anonymous_allowed() -> bool:
    return is_dev() and os.environ.get("QCOMPASS_DEV_ALLOW_ANONYMOUS") == "1"


def _http(exc: AuthError) -> HTTPException:
    return HTTPException(status_for(exc.code), detail={"code": exc.code, "message": str(exc)})


def authenticate(authorization: str | None, tenant_header: str | None) -> Principal:
    """Resolve the caller or raise ``HTTPException`` (401/400/403/404/503)."""
    if not authorization:
        if dev_anonymous_allowed():
            return Principal("dev", "anonymous", tenant_header or DEV_TENANT, frozenset(SCOPES))
        raise HTTPException(401, detail={"code": "AUTH_REQUIRED", "message": "Authorization header missing"})
    scheme, _, credential = authorization.strip().partition(" ")
    if scheme.lower() != "bearer" or not credential:
        raise HTTPException(400, detail={"code": "AUTH_MALFORMED", "message": "expected 'Bearer <token>'"})

    if credential.startswith(f"{_TOKEN_PREFIX}_"):
        try:
            token = require_auth(
                get_auth_store(), authorization=authorization,
                tenant_header=tenant_header or None,
            )
        except AuthError as exc:
            if exc.code == "TENANT_REQUIRED":
                # An API key names its tenant; the header is optional.
                token = get_auth_store().lookup(credential)
                if token is None:
                    raise _http(AuthError("Unknown bearer token", code="AUTH_INVALID")) from exc
                return Principal("api_key", token.token_id[:16], token.tenant_id, normalize_scopes(token.scopes))
            raise _http(exc) from exc
        return Principal("api_key", token.token_id[:16], token.tenant_id, normalize_scopes(token.scopes))

    claims = verify_supabase_token(credential)
    if not tenant_header:
        raise HTTPException(400, detail={"code": "TENANT_REQUIRED", "message": "X-QCompass-Tenant header missing"})
    member = get_auth_store().membership(tenant_header, str(claims["sub"]))
    if member is None:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": f"no tenant {tenant_header!r}"})
    _role, scopes = member
    return Principal("supabase", str(claims["sub"]), tenant_header, scopes)


def require_scope(scope: Scope):
    """FastAPI dependency factory: authenticate and require ``scope``."""

    # Async on purpose (SEC-H1): FastAPI runs a sync dependency in a
    # threadpool with a *copied* context, so a ContextVar set there never
    # reaches the endpoint. Run the blocking lookup in a thread, then bind
    # the tenant in the request's own context. Routes still pass
    # ``principal.tenant_id`` explicitly; the binding is defence in depth
    # for code that reads ``active_tenant()`` (the budget hook).
    async def _dep(
        authorization: str | None = Header(default=None),
        x_qcompass_tenant: str | None = Header(default=None),
    ) -> Principal:
        principal = await asyncio.to_thread(authenticate, authorization, x_qcompass_tenant)
        if scope not in principal.scopes:
            raise HTTPException(
                403, detail={"code": "FORBIDDEN", "message": f"scope {scope!r} required"},
            )
        set_active_tenant(principal.tenant_id)
        return principal

    _dep.__name__ = f"require_{scope}"
    return _dep


async def authenticate_websocket(websocket: WebSocket, scope: Scope) -> Principal | None:
    """Same check for a WebSocket handshake. Closes with 1008 and returns None on failure."""
    try:
        principal = await asyncio.to_thread(
            authenticate,
            websocket.headers.get("authorization"), websocket.headers.get("x-qcompass-tenant"),
        )
    except HTTPException:
        await websocket.close(code=1008)
        return None
    if scope not in principal.scopes:
        await websocket.close(code=1008)
        return None
    set_active_tenant(principal.tenant_id)
    return principal


class TenantNotBound(RuntimeError):
    """Tenant-scoped code ran with no tenant (SEC-H1).

    Outside ``QCOMPASS_ENV=dev`` there is no default tenant: every caller
    passes ``Principal.tenant_id`` (or the worker's job tenant). Reaching
    this is a programming error, so it fails closed instead of filing the
    work under a shared tenant.
    """


def resolve_tenant_slug(tenant: str | None) -> str:
    """The tenant to act for: ``tenant``, else the bound one, else ``dev`` in dev only."""
    from .auth import active_tenant

    slug = tenant or active_tenant()
    if slug:
        return slug
    if is_dev():
        return DEV_TENANT
    raise TenantNotBound("no tenant bound; pass the principal's tenant_id")


__all__ = [
    "DEV_TENANT",
    "TenantNotBound",
    "Principal",
    "authenticate",
    "authenticate_websocket",
    "dev_anonymous_allowed",
    "require_scope",
    "resolve_tenant_slug",
]
