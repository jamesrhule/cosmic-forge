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

The JWKS is cached per URL for ``_JWKS_TTL_S``. Refreshes are single-flight
(one outbound fetch per URL at a time; other callers serve the cached set or
wait for that fetch), a failed refresh is not retried for
``_JWKS_RETRY_MIN_S``, and while the endpoint fails the last good set keeps
being served for at most ``_JWKS_STALE_IF_ERROR_S`` past its TTL
(stale-if-error), so an outage or a flood of tokens never turns into one
outbound request per API request (Gate 1, c7). Stale-if-error covers
network errors, timeouts and 5xx answers only: a 4xx from the JWKS endpoint
(401, 403, 404: the project or its keys are gone) drops the cached set at
once. The leader's fetch as a whole is bounded by ``_JWKS_FETCH_DEADLINE_S``
(round 3B).
"""

from __future__ import annotations

import json
import logging
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
# An unknown `kid` (Supabase rotated its signing key) forces one refetch,
# at most once per this interval per URL, so forged kids can't make the API
# hammer the JWKS endpoint (Gate 1 review nit).
_JWKS_REFETCH_MIN_S = 30.0
# After a failed fetch, no new fetch for this URL within this interval.
_JWKS_RETRY_MIN_S = 30.0
# Stale-if-error bound: a key set past its TTL is served while refreshes
# fail, but never more than this long past the TTL. Bounded, so a key
# Supabase revoked stops verifying within TTL + this bound even if its JWKS
# endpoint stays down.
_JWKS_STALE_IF_ERROR_S = 3600.0
# A caller with no usable key set waits at most this long for another
# caller's in-flight fetch.
_JWKS_FETCH_WAIT_S = 10.0
# The whole outbound fetch (connect, request, headers and body) gets this
# long, what one phase alone used to get: httpx's timeout bounds each phase
# and each read separately, so an endpoint that drips its body could hold
# the single flight indefinitely (round 3B). Below _JWKS_FETCH_WAIT_S, so
# the callers waiting for the leader see its outcome.
_JWKS_FETCH_DEADLINE_S = 5.0
# A key set is a few kB; refuse to buffer more than this.
_JWKS_MAX_BYTES = 1 << 20

log = logging.getLogger(__name__)


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
    deadline = time.monotonic() + _JWKS_FETCH_DEADLINE_S
    body = bytearray()
    with httpx.Client(timeout=_JWKS_FETCH_DEADLINE_S) as client, client.stream("GET", url) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_bytes():
            body += chunk
            if len(body) > _JWKS_MAX_BYTES:
                msg = f"JWKS response larger than {_JWKS_MAX_BYTES} bytes"
                raise ValueError(msg)
            if time.monotonic() > deadline:  # this thread stops reading too
                msg = f"JWKS fetch exceeded {_JWKS_FETCH_DEADLINE_S:g}s"
                raise TimeoutError(msg)
    return json.loads(bytes(body))


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
_last_forced: dict[str, float] = {}
_last_failed: dict[str, float] = {}
_inflight: dict[str, threading.Event] = {}
_lock = threading.Lock()


class _JwksUnavailableError(Exception):
    """No usable key set: the endpoint failed and nothing cached may be served."""


def set_jwks_fetcher(fn: JwksFetcher | None) -> None:
    global _jwks_fetcher
    _jwks_fetcher = fn or _default_jwks_fetcher
    with _lock:
        _jwks_cache.clear()
        _last_forced.clear()
        _last_failed.clear()
        _inflight.clear()


def set_roles_fetcher(fn: RolesFetcher | None) -> None:
    global _roles_fetcher
    _roles_fetcher = fn or _default_roles_fetcher


def _supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not url:
        raise _blocked("SUPABASE_URL")
    return url


_Entry = tuple[float, dict[str, Any]]


def _servable(hit: _Entry | None, now: float) -> bool:
    """Within the TTL, or past it by less than the stale-if-error bound."""
    return hit is not None and now - hit[0] < _JWKS_TTL_S + _JWKS_STALE_IF_ERROR_S


@dataclass(frozen=True)
class _Fetch:
    """The single in-flight fetch for a URL, as one caller sees it."""

    pending: threading.Event
    leader: bool  # this caller fetches; the others wait for its result
    hit: _Entry | None  # the cache entry when the caller looked
    now: float


def _claim(url: str, force: bool) -> dict[str, Any] | _Fetch:
    """Answer from the cache, or lead or join the single in-flight fetch."""
    with _lock:
        now = time.monotonic()
        hit = _jwks_cache.get(url)
        if force:
            if hit and now - _last_forced.get(url, -_JWKS_REFETCH_MIN_S) < _JWKS_REFETCH_MIN_S:
                return hit[1]  # rate-limited: keep the cached set
        elif hit and now - hit[0] < _JWKS_TTL_S:
            return hit[1]
        stale = hit[1] if hit is not None and not force and _servable(hit, now) else None
        failed_at = _last_failed.get(url)
        if failed_at is not None and now - failed_at < _JWKS_RETRY_MIN_S:
            # Backing off after a failure: no outbound fetch.
            if stale is not None:
                return stale
            raise _JwksUnavailableError(url)
        pending = _inflight.get(url)
        if pending is not None:
            # Single flight: another caller is already fetching this URL.
            return stale if stale is not None else _Fetch(pending, False, hit, now)
        pending = _inflight[url] = threading.Event()
        if force:
            _last_forced[url] = now
        return _Fetch(pending, True, hit, now)


def _await_fetch(url: str, fetch: _Fetch) -> dict[str, Any]:
    """Wait for another caller's fetch and use its result; never fetch again."""
    fetch.pending.wait(_JWKS_FETCH_WAIT_S)
    with _lock:
        fresh = _jwks_cache.get(url)
    if fresh is not None and fresh is not fetch.hit:
        return fresh[1]
    raise _JwksUnavailableError(url)


def _keys_gone(exc: BaseException) -> bool:
    """A 4xx from the JWKS endpoint: the project or its keys no longer exist."""
    return isinstance(exc, httpx.HTTPStatusError) and 400 <= exc.response.status_code < 500


def _fetch_within_deadline(url: str) -> dict[str, Any]:
    """``_jwks_fetcher(url)``, given up after ``_JWKS_FETCH_DEADLINE_S`` (a TimeoutError)."""
    fetcher = _jwks_fetcher
    out: dict[str, Any] = {}
    done = threading.Event()

    def run() -> None:
        try:
            out["data"] = fetcher(url)
        except BaseException as exc:  # noqa: BLE001 - re-raised in the leader
            out["error"] = exc
        finally:
            done.set()

    threading.Thread(target=run, name="jwks-fetch", daemon=True).start()
    if not done.wait(_JWKS_FETCH_DEADLINE_S):
        msg = f"JWKS fetch exceeded {_JWKS_FETCH_DEADLINE_S:g}s"
        raise TimeoutError(msg)
    if "error" in out:
        raise out["error"]
    return out["data"]  # type: ignore[no-any-return]


def _lead_fetch(url: str, fetch: _Fetch, force: bool) -> dict[str, Any]:
    """The one outbound fetch for ``url``; stale-if-error on failure, except a 4xx."""
    try:
        data = _fetch_within_deadline(url)
    except Exception as exc:
        with _lock:
            _last_failed[url] = time.monotonic()
            if _keys_gone(exc):
                _jwks_cache.pop(url, None)
        if _keys_gone(exc):
            log.warning("JWKS endpoint answered %s; dropped the cached key set",
                        exc.response.status_code)  # type: ignore[attr-defined]
            raise
        if not force and fetch.hit is not None and _servable(fetch.hit, fetch.now):
            log.warning("JWKS refresh failed; serving the cached key set", exc_info=True)
            return fetch.hit[1]
        raise
    else:
        with _lock:
            _jwks_cache[url] = (time.monotonic(), data)
            _last_failed.pop(url, None)
        return data
    finally:
        with _lock:
            if _inflight.get(url) is fetch.pending:
                del _inflight[url]
        fetch.pending.set()


def _jwks(url: str, *, force: bool = False) -> dict[str, Any]:
    """The key set for ``url``; raises when there is no usable one.

    ``force`` (an unknown ``kid``) asks for a fresh set and never settles for
    a stale one; it is rate-limited to one per ``_JWKS_REFETCH_MIN_S``.
    """
    claim = _claim(url, force)
    if not isinstance(claim, _Fetch):
        return claim
    if claim.leader:
        return _lead_fetch(url, claim, force)
    return _await_fetch(url, claim)


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
    jwks_url = f"{base}/auth/v1/.well-known/jwks.json"
    try:
        keys = _jwks(jwks_url).get("keys", [])
        match = next((k for k in keys if k.get("kid") == kid), None)
        if match is None:
            # Possibly a rotated key: one rate-limited refetch.
            keys = _jwks(jwks_url, force=True).get("keys", [])
            match = next((k for k in keys if k.get("kid") == kid), None)
    except Exception as exc:  # noqa: BLE001 - upstream failure is 503, not 500
        raise HTTPException(503, detail={"code": "UNAVAILABLE", "message": "auth keys unavailable"}) from exc
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
