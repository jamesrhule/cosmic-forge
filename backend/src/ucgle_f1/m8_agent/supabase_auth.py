"""Supabase session verification for the compute API (correction 9, P3-04).

- The bearer token is a Supabase access token (JWT). Its signature is
  verified against the project's JWKS at
  ``{SUPABASE_URL}/auth/v1/.well-known/jwks.json``, with issuer
  ``{SUPABASE_URL}/auth/v1`` and audience ``authenticated``.
- Roles come from ``public.user_roles`` (the same table the frontend's
  ``hasRole`` reads), fetched over PostgREST *with the caller's own token*,
  so row-level security decides what the caller may read. The service-role
  key is never used for this.

Missing configuration never crashes and never falls back to an insecure
default (R9): the dependency answers 503 ``UNAVAILABLE`` with
``BLOCKED-ON-JAMES:<NAME>``.

Both network calls go through replaceable fetchers so tests run offline
(R8): ``set_jwks_fetcher`` and ``set_roles_fetcher``.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import Header, HTTPException

JwksFetcher = Callable[[str], dict[str, Any]]
RolesFetcher = Callable[[str, str, str, str], list[str]]

_JWKS_TTL_S = 600.0


@dataclass(frozen=True)
class SupabaseUser:
    user_id: str
    email: str | None
    roles: frozenset[str]
    claims: dict[str, Any]


def _blocked(name: str) -> HTTPException:
    return HTTPException(503, detail={"code": "UNAVAILABLE", "message": f"BLOCKED-ON-JAMES:{name}"})


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(401, detail={"code": "AUTH_INVALID", "message": message})


def _default_jwks_fetcher(url: str) -> dict[str, Any]:
    resp = httpx.get(url, timeout=5.0)
    resp.raise_for_status()
    return resp.json()


def _default_roles_fetcher(supabase_url: str, apikey: str, token: str, user_id: str) -> list[str]:
    resp = httpx.get(
        f"{supabase_url}/rest/v1/user_roles",
        params={"select": "role", "user_id": f"eq.{user_id}"},
        headers={"apikey": apikey, "Authorization": f"Bearer {token}"},
        timeout=5.0,
    )
    resp.raise_for_status()
    return [str(row["role"]) for row in resp.json() if isinstance(row, dict) and "role" in row]


_jwks_fetcher: JwksFetcher = _default_jwks_fetcher
_roles_fetcher: RolesFetcher = _default_roles_fetcher
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_lock = threading.Lock()


def set_jwks_fetcher(fn: JwksFetcher | None) -> None:
    global _jwks_fetcher
    _jwks_fetcher = fn or _default_jwks_fetcher
    with _lock:
        _jwks_cache.clear()


def set_roles_fetcher(fn: RolesFetcher | None) -> None:
    global _roles_fetcher
    _roles_fetcher = fn or _default_roles_fetcher


def _supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not url:
        raise _blocked("SUPABASE_URL")
    return url


def _jwks(url: str) -> dict[str, Any]:
    now = time.monotonic()
    with _lock:
        hit = _jwks_cache.get(url)
        if hit and now - hit[0] < _JWKS_TTL_S:
            return hit[1]
    data = _jwks_fetcher(url)
    with _lock:
        _jwks_cache[url] = (now, data)
    return data


def verify_supabase_token(token: str) -> dict[str, Any]:
    """Return the verified claims of a Supabase access token, or raise 401/503."""
    base = _supabase_url()
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise _unauthorized("malformed token") from exc
    kid = header.get("kid")
    alg = header.get("alg")
    if alg not in {"RS256", "ES256"}:
        # Asymmetric signing keys only: an HS256 token can't be checked
        # against the public JWKS, and `none` is never acceptable.
        raise _unauthorized(f"unsupported token algorithm {alg!r}")
    try:
        keys = _jwks(f"{base}/auth/v1/.well-known/jwks.json").get("keys", [])
    except Exception as exc:  # noqa: BLE001 - upstream failure is 503, not 500
        raise HTTPException(503, detail={"code": "UNAVAILABLE", "message": "auth keys unavailable"}) from exc
    match = next((k for k in keys if k.get("kid") == kid), None)
    if match is None:
        raise _unauthorized("unknown signing key")
    try:
        key = jwt.PyJWK(match).key
        return jwt.decode(
            token,
            key=key,
            algorithms=[alg],
            audience="authenticated",
            issuer=f"{base}/auth/v1",
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(401, detail={"code": "AUTH_EXPIRED", "message": "token expired"}) from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized("invalid token") from exc


def current_supabase_user(authorization: str | None) -> SupabaseUser:
    if not authorization:
        raise HTTPException(401, detail={"code": "AUTH_REQUIRED", "message": "bearer token required"})
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(400, detail={"code": "AUTH_MALFORMED", "message": "expected 'Bearer <token>'"})
    claims = verify_supabase_token(token)
    apikey = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
    if not apikey:
        raise _blocked("SUPABASE_PUBLISHABLE_KEY")
    try:
        roles = _roles_fetcher(_supabase_url(), apikey, token, str(claims["sub"]))
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - upstream failure is 503
        raise HTTPException(503, detail={"code": "UNAVAILABLE", "message": "role lookup unavailable"}) from exc
    return SupabaseUser(
        user_id=str(claims["sub"]),
        email=claims.get("email"),
        roles=frozenset(roles),
        claims=claims,
    )


def require_supabase_admin(authorization: str | None = Header(default=None)) -> SupabaseUser:
    """FastAPI dependency: a verified Supabase session holding the ``admin`` role."""
    user = current_supabase_user(authorization)
    if "admin" not in user.roles:
        raise HTTPException(403, detail={"code": "FORBIDDEN", "message": "admin role required"})
    return user


__all__ = [
    "SupabaseUser",
    "current_supabase_user",
    "require_supabase_admin",
    "set_jwks_fetcher",
    "set_roles_fetcher",
    "verify_supabase_token",
]
