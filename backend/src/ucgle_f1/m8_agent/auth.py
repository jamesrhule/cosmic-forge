"""Bearer-token auth + tenancy for the qcompass surface (PROMPT 10 v2 §A).

Wired into :mod:`server.build_app` so every ``/api/qcompass/*`` and
``/v1/chat`` route requires:
  - ``Authorization: Bearer <token>`` header
  - ``X-QCompass-Tenant: <tenant_id>`` header

Tokens are stored alongside the agent memory (:mod:`memory.store`)
in a new ``tokens`` table; tenant budgets ride a parallel
``tenant_budgets`` table (created lazily). The router's
:class:`qcompass_router.PricingEngine` consults
:func:`tenant_budget_remaining` before every estimate when the
caller has set the active-tenant context via
:func:`set_active_tenant`.

The legacy ``/api/runs`` + ``/api/benchmarks`` + ``/api/models``
paths stay unauthenticated by design — the v2 spec only mandates
auth on ``/api/qcompass/*`` and ``/v1/chat``.
"""

from __future__ import annotations

import contextvars
import hashlib
import os
import re
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import Engine, text

from ..db import get_engine

_TOKEN_PREFIX = "qcompass-tok"


# ── Context variable for the active tenant ──────────────────────────


_ACTIVE_TENANT: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "qcompass_active_tenant", default=None,
)


def set_active_tenant(tenant_id: Optional[str]) -> contextvars.Token:
    """Bind the active tenant id to the calling context."""
    return _ACTIVE_TENANT.set(tenant_id)


def reset_active_tenant(token: contextvars.Token) -> None:
    _ACTIVE_TENANT.reset(token)


def active_tenant() -> Optional[str]:
    """Return the currently-active tenant id, or None if unbound."""
    return _ACTIVE_TENANT.get()


# ── Records + errors ───────────────────────────────────────────────


@dataclass(frozen=True)
class Token:
    token_id: str
    tenant_id: str
    scopes: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime | None
    label: str = ""


@dataclass(frozen=True)
class TenantBudget:
    tenant_id: str
    monthly_budget_usd: float
    spent_usd: float
    period_start: datetime
    notes: str = ""

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.monthly_budget_usd - self.spent_usd)


class AuthError(Exception):
    """Raised by :func:`require_auth` on any auth failure."""

    code: str = "AUTH_REQUIRED"

    def __init__(self, message: str, *, code: str = "AUTH_REQUIRED") -> None:
        super().__init__(message)
        self.code = code


# ── Store ──────────────────────────────────────────────────────────


class AuthStore:
    """Postgres-backed API keys, tenant membership and budgets (P3-01, P3-04).

    Tables (``supabase/migrations``): ``public.api_keys`` (SHA-256 hashes),
    ``public.tenants`` / ``public.tenant_members`` (main's tenancy schema)
    and ``public.tenant_budgets``.

    Tenants are addressed by **slug** everywhere outside this class: the
    ``X-QCompass-Tenant`` header, ``Token.tenant_id`` and artifact paths.
    A tenant UUID is also accepted wherever a tenant is named.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def ping(self) -> None:
        """Raise if the database is unreachable (``/readyz``)."""
        with self._engine.connect() as conn:
            conn.execute(text("select 1"))

    # ── tenants ───────────────────────────────────────────────

    def ensure_tenant(self, tenant: str, *, name: str | None = None) -> str:
        """Return the tenant UUID for ``tenant`` (slug or UUID), creating it by slug if missing."""
        found = self.resolve_tenant(tenant)
        if found is not None:
            return found[0]
        with self._engine.begin() as conn:
            # The conflict update matches only a tenant this service may use:
            # never a user-owned 'dev' (round 2, c1).
            row = conn.execute(
                text(
                    "insert into public.tenants (name, slug) values (:name, :slug) "
                    "on conflict (slug) do update set slug = excluded.slug "
                    f"where not ({_USER_OWNED_DEV.format(t='tenants')}) returning id"
                ),
                {"name": name or tenant, "slug": tenant},
            ).first()
        if row is None:
            msg = (
                f"tenant slug {tenant!r} belongs to a user, not to this service: "
                "BLOCKED-ON-JAMES:rename-user-owned-dev-tenant"
            )
            raise AuthError(msg, code="TENANT_RESERVED")
        return str(row[0])

    def resolve_tenant(self, tenant: str) -> tuple[str, str] | None:
        """(uuid, slug) for a tenant slug or UUID, or None.

        A user-owned tenant with the slug ``dev`` is never the service's
        development tenant: it resolves to None by slug (round 2, c1).
        """
        # An id match wins over a slug match, deterministically. Slugs that
        # cast to uuid are forbidden by tenants_slug_not_uuid_check
        # (20261102100000); the ORDER BY still decides if one predates it.
        user_owned_dev = _USER_OWNED_DEV.format(t="t")
        sql = (
            f"select t.id::text, t.slug, ({user_owned_dev}) from public.tenants t "
            "where t.slug = :t"
        )
        if _looks_like_uuid(tenant):
            sql = (
                f"select t.id::text, t.slug, ({user_owned_dev}) from public.tenants t "
                "where t.id = cast(:t as uuid) or t.slug = cast(:t as text) "
                "order by (t.id = cast(:t as uuid)) desc limit 1"
            )
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"t": tenant}).first()
        if row is None or (row[2] and row[1] == tenant):  # a user-owned 'dev', named by slug
            return None
        return (row[0], row[1])

    # ── API keys ──────────────────────────────────────────────

    def issue(
        self,
        tenant_id: str,
        scopes: Iterable[str],
        *,
        ttl_seconds: int | None = 3600,
        label: str = "",
    ) -> Token:
        """Mint an API key bound to ``tenant_id`` (slug or UUID).

        The returned :class:`Token` carries the plaintext key in
        ``token_id``; only its SHA-256 hash is stored. See
        :meth:`_key_tenant` for which tenant a key may be bound to.
        """
        if not tenant_id:
            msg = "tenant_id is required when issuing a token."
            raise ValueError(msg)
        tenant_uuid = self._key_tenant(tenant_id)
        slug = self.resolve_tenant(tenant_uuid)[1]  # type: ignore[index]
        scope_list = tuple(s.strip() for s in scopes if s.strip())
        token_id = f"{_TOKEN_PREFIX}_{secrets.token_urlsafe(24)}"
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "insert into public.api_keys "
                    "(key_hash, key_prefix, tenant_id, scopes, label, issued_at, expires_at) "
                    "values (:h, :p, cast(:t as uuid), :s, :l, :i, :e)"
                ),
                {"h": _hash_key(token_id), "p": token_id[:16], "t": tenant_uuid,
                 "s": list(scope_list), "l": label, "i": now, "e": expires},
            )
        return Token(
            token_id=token_id, tenant_id=slug, scopes=scope_list,
            issued_at=now, expires_at=expires, label=label,
        )

    def _key_tenant(self, tenant: str) -> str:
        """The UUID of the tenant a new API key is bound to (round 3B).

        Named by UUID: that tenant, which must exist. Named by slug: the
        tenant with that slug, created when missing, but never one that a
        user created or joined (``created_by`` set, or any member). Any
        owner can rename their own tenant to a slug nobody uses yet, so a
        slug alone never shows that a tenant is the customer's; adopting it
        would bind the customer's key to the squatter's tenant. Such a slug
        is refused with ``TENANT_RESERVED``; an operator who means that
        tenant names it by UUID.
        """
        if _looks_like_uuid(tenant):
            found = self.resolve_tenant(tenant)
            if found is None or found[0] != tenant.lower():
                msg = f"no tenant with id {tenant!r}"
                raise AuthError(msg, code="UNKNOWN_TENANT")
            return found[0]
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    "insert into public.tenants (name, slug) values (:name, :slug) "
                    "on conflict (slug) do update set slug = excluded.slug "
                    f"where not ({_USER_OWNED.format(t='tenants')}) returning id"
                ),
                {"name": tenant, "slug": tenant},
            ).first()
        if row is None:
            msg = (
                f"tenant slug {tenant!r} belongs to a tenant a user created or joined, "
                "not to this service; name the tenant by its UUID to issue a key for it"
            )
            raise AuthError(msg, code="TENANT_RESERVED")
        return str(row[0])

    def lookup(self, token_id: str) -> Token | None:
        """Resolve a plaintext API key (by its hash); None if unknown or revoked."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "select t.slug, k.scopes, k.issued_at, k.expires_at, k.label "
                    "from public.api_keys k join public.tenants t on t.id = k.tenant_id "
                    "where k.key_hash = :h and k.revoked_at is null"
                ),
                {"h": _hash_key(token_id)},
            ).first()
        if row is None:
            return None
        return Token(
            token_id=token_id, tenant_id=row[0], scopes=tuple(row[1] or ()),
            issued_at=row[2], expires_at=row[3], label=row[4] or "",
        )

    def revoke(self, token_id: str) -> bool:
        with self._engine.begin() as conn:
            res = conn.execute(
                text(
                    "update public.api_keys set revoked_at = now() "
                    "where key_hash = :h and revoked_at is null"
                ),
                {"h": _hash_key(token_id)},
            )
        return res.rowcount > 0

    # ── tenant membership (Supabase users) ────────────────────

    def add_member(self, tenant_id: str, user_id: str, role: str) -> None:
        """Add ``user_id`` (an ``auth.users`` id) to a tenant with ``role``."""
        if role not in ROLE_SCOPES:
            msg = f"role must be one of {sorted(ROLE_SCOPES)}; got {role!r}"
            raise ValueError(msg)
        tenant_uuid = self.ensure_tenant(tenant_id)
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "insert into public.tenant_members (tenant_id, user_id, role) "
                    "values (cast(:t as uuid), cast(:u as uuid), cast(:r as public.tenant_role)) "
                    "on conflict (tenant_id, user_id) do update set role = excluded.role"
                ),
                {"t": tenant_uuid, "u": user_id, "r": role},
            )

    def membership(self, tenant_id: str, user_id: str) -> tuple[str, frozenset[str]] | None:
        """(role, scopes) of ``user_id`` in a tenant (slug or UUID), or None."""
        if not _looks_like_uuid(user_id):
            return None
        found = self.resolve_tenant(tenant_id)
        if found is None:
            return None
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "select role::text from public.tenant_members "
                    "where tenant_id = cast(:t as uuid) and user_id = cast(:u as uuid)"
                ),
                {"t": found[0], "u": user_id},
            ).first()
        if row is None:
            return None
        return row[0], ROLE_SCOPES[row[0]]

    def memberships(self, user_id: str) -> list[tuple[str, str]]:
        """[(tenant slug, role)] for every tenant ``user_id`` belongs to."""
        if not _looks_like_uuid(user_id):
            return []
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "select t.slug, m.role::text from public.tenant_members m "
                    "join public.tenants t on t.id = m.tenant_id "
                    "where m.user_id = cast(:u as uuid) order by t.slug"
                ),
                {"u": user_id},
            ).all()
        return [(r[0], r[1]) for r in rows]

    # ── tenant budgets ────────────────────────────────────────

    def upsert_budget(
        self, tenant_id: str, monthly_budget_usd: float, *, notes: str = "",
    ) -> TenantBudget:
        tenant_uuid = self.ensure_tenant(tenant_id)
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "insert into public.tenant_budgets "
                    "(tenant_id, monthly_budget_usd, spent_usd, period_start, notes) "
                    "values (cast(:t as uuid), :b, 0, :p, :n) "
                    "on conflict (tenant_id) do update set "
                    "monthly_budget_usd = excluded.monthly_budget_usd, notes = excluded.notes"
                ),
                {"t": tenant_uuid, "b": float(monthly_budget_usd),
                 "p": _month_start(datetime.now(UTC)), "n": notes},
            )
        return self.get_budget(tenant_id)  # type: ignore[return-value]

    def get_budget(self, tenant_id: str) -> TenantBudget | None:
        found = self.resolve_tenant(tenant_id)
        if found is None:
            return None
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "select monthly_budget_usd, spent_usd, period_start, notes "
                    "from public.tenant_budgets where tenant_id = cast(:t as uuid)"
                ),
                {"t": found[0]},
            ).first()
        if row is None:
            return None
        return TenantBudget(
            tenant_id=found[1], monthly_budget_usd=float(row[0]), spent_usd=float(row[1]),
            period_start=row[2], notes=row[3] or "",
        )

    def record_spend(self, tenant_id: str, amount_usd: float) -> TenantBudget:
        """Increment ``spent_usd`` for a tenant (atomic in one UPDATE)."""
        if amount_usd < 0:
            msg = f"amount_usd must be ≥ 0; got {amount_usd}"
            raise ValueError(msg)
        found = self.resolve_tenant(tenant_id)
        if found is not None:
            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        "update public.tenant_budgets set spent_usd = spent_usd + :a "
                        "where tenant_id = cast(:t as uuid)"
                    ),
                    {"a": float(amount_usd), "t": found[0]},
                )
        b = self.get_budget(tenant_id)
        if b is None:
            msg = f"unknown tenant: {tenant_id!r}"
            raise AuthError(msg, code="UNKNOWN_TENANT")
        return b

    def reset_period(self, tenant_id: str) -> None:
        """Reset spent_usd + period_start to the start of this month."""
        found = self.resolve_tenant(tenant_id)
        if found is None:
            return
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "update public.tenant_budgets set spent_usd = 0, period_start = :p "
                    "where tenant_id = cast(:t as uuid)"
                ),
                {"p": _month_start(datetime.now(UTC)), "t": found[0]},
            )


# ── Keys, scopes, roles ───────────────────────────────────────────


_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

# A tenant a user created or joined: it has a creator, or any member. The
# service's own tenants (ensure_tenant, issue) have neither until the
# service adds members. ``{t}`` is the tenants row alias.
_USER_OWNED = (
    "({t}.created_by is not null or exists "
    "(select 1 from public.tenant_members m where m.tenant_id = {t}.id))"
)
# A 'dev' tenant that a user created or joined is not the service's
# development tenant. Same rule as migrations 20261102100100 and
# 20261102120200 (public.qcompass_user_owned_dev).
_USER_OWNED_DEV = "{t}.slug = 'dev' and " + _USER_OWNED


def _looks_like_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value or ""))


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


SCOPES = frozenset({"read", "run", "qpu", "admin"})

# Roles are main's public.tenant_role enum.
ROLE_SCOPES: dict[str, frozenset[str]] = {
    "viewer": frozenset({"read"}),
    "member": frozenset({"read", "run"}),
    "admin": frozenset({"read", "run", "qpu", "admin"}),
    "owner": frozenset({"read", "run", "qpu", "admin"}),
}


def normalize_scopes(scopes: Iterable[str]) -> frozenset[str]:
    """Canonical scope names; the legacy ``qcompass:<scope>`` form maps to ``<scope>``."""
    out = set()
    for raw in scopes:
        name = raw.strip().split(":")[-1]
        if name in SCOPES:
            out.add(name)
    return frozenset(out)


# ── Validation helpers ────────────────────────────────────────────


def parse_bearer(authorization_header: str | None) -> str:
    """Extract the bearer token id from an Authorization header."""
    if not authorization_header:
        raise AuthError("Authorization header missing", code="AUTH_REQUIRED")
    parts = authorization_header.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError(
            "Authorization header must be 'Bearer <token>'",
            code="AUTH_MALFORMED",
        )
    return parts[1]


def require_auth(
    store: AuthStore,
    *,
    authorization: str | None,
    tenant_header: str | None,
) -> Token:
    """Validate the bearer token + tenant header.

    Returns the resolved :class:`Token` on success. Raises
    :class:`AuthError` (with a code) on every failure path so the
    HTTP layer can map to a status code uniformly.
    """
    token_id = parse_bearer(authorization)
    token = store.lookup(token_id)
    if token is None:
        raise AuthError("Unknown bearer token", code="AUTH_INVALID")
    if token.expires_at is not None:
        # SQLite stores aware ISO; compare against now in UTC.
        expires = token.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires < datetime.now(UTC):
            raise AuthError("Token expired", code="AUTH_EXPIRED")
    if not tenant_header:
        raise AuthError(
            "X-QCompass-Tenant header missing",
            code="TENANT_REQUIRED",
        )
    if tenant_header != token.tenant_id:
        raise AuthError(
            f"Token tenant {token.tenant_id!r} does not match "
            f"X-QCompass-Tenant {tenant_header!r}",
            code="TENANT_MISMATCH",
        )
    return token


def tenant_budget_remaining(
    store: AuthStore, tenant_id: str | None,
) -> float:
    """Return the tenant's remaining budget for the current month.

    Returns ``+inf`` when the tenant has no budget record (no gating)
    or when ``tenant_id`` is None (unauthenticated path).
    """
    if not tenant_id:
        return float("inf")
    budget = store.get_budget(tenant_id)
    if budget is None:
        return float("inf")
    return budget.remaining_usd


def gate_spend(
    store: AuthStore,
    tenant_id: str | None,
    amount_usd: float,
) -> None:
    """Raise :class:`AuthError` when the tenant cannot afford ``amount_usd``."""
    if not tenant_id:
        return
    remaining = tenant_budget_remaining(store, tenant_id)
    if amount_usd > remaining:
        raise AuthError(
            f"Tenant {tenant_id!r} budget exceeded: requested "
            f"${amount_usd:.4f}, remaining ${remaining:.4f}.",
            code="BUDGET_EXCEEDED",
        )


def install_budget_hook() -> bool:
    """Register the per-tenant spend gate with qcompass-router's PricingEngine.

    Every router estimate for a non-free backend then calls
    :func:`gate_spend` for the active tenant and raises ``BUDGET_EXCEEDED``
    (402) when the estimate exceeds the remaining budget (P3-05). The API
    and the worker both call this at start-up. Returns False when
    qcompass-router isn't installed.
    """
    try:
        import qcompass_router as _qr  # type: ignore[import-not-found]
    except ImportError:
        return False

    def _budget_gate(tenant_id: str | None, amount_usd: float) -> None:
        gate_spend(get_auth_store(), tenant_id or active_tenant(), amount_usd)

    _qr.set_tenant_budget_hook(_budget_gate)
    return True


# ── Singletons ───────────────────────────────────────────────────


_STORE: AuthStore | None = None
_STORE_LOCK = threading.Lock()


def get_auth_store() -> AuthStore:
    """Return the process-wide :class:`AuthStore` singleton."""
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = AuthStore()
        return _STORE


def reset_auth_store() -> None:
    """Drop the singleton — primarily for tests that swap UCGLE_F1_STATE_DIR."""
    global _STORE
    with _STORE_LOCK:
        _STORE = None


# ── helpers ──────────────────────────────────────────────────────



def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


__all__ = [
    "AuthError",
    "AuthStore",
    "Token",
    "TenantBudget",
    "active_tenant",
    "gate_spend",
    "install_budget_hook",
    "get_auth_store",
    "parse_bearer",
    "require_auth",
    "reset_active_tenant",
    "reset_auth_store",
    "set_active_tenant",
    "tenant_budget_remaining",
]
