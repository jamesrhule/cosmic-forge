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
import os
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional


_DB_ENV = "UCGLE_F1_STATE_DIR"
_TOKEN_PREFIX = "qcompass-tok"


def _default_db_path() -> Path:
    root = Path(os.environ.get(_DB_ENV, str(Path.home() / ".ucgle_f1")))
    return root / "auth.db"


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
    """SQLite-backed token + tenant-budget store.

    Owns two tables:
      tokens(token_id, tenant_id, scopes_csv, issued_at,
             expires_at, label)
      tenant_budgets(tenant_id, monthly_budget_usd, spent_usd,
                     period_start, notes)
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _default_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tokens (
                    token_id     TEXT PRIMARY KEY,
                    tenant_id    TEXT NOT NULL,
                    scopes_csv   TEXT NOT NULL,
                    issued_at    TEXT NOT NULL,
                    expires_at   TEXT,
                    label        TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tenant_budgets (
                    tenant_id           TEXT PRIMARY KEY,
                    monthly_budget_usd  REAL NOT NULL,
                    spent_usd           REAL NOT NULL DEFAULT 0.0,
                    period_start        TEXT NOT NULL,
                    notes               TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.commit()

    # ── tokens ─────────────────────────────────────────────────

    def issue(
        self,
        tenant_id: str,
        scopes: Iterable[str],
        *,
        ttl_seconds: int | None = 3600,
        label: str = "",
    ) -> Token:
        """Mint a fresh bearer token bound to ``tenant_id``."""
        if not tenant_id:
            msg = "tenant_id is required when issuing a token."
            raise ValueError(msg)
        scope_list = tuple(s.strip() for s in scopes if s.strip())
        token_id = f"{_TOKEN_PREFIX}_{secrets.token_urlsafe(24)}"
        now = datetime.now(UTC)
        expires = (
            now + timedelta(seconds=ttl_seconds)
            if ttl_seconds is not None else None
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tokens
                  (token_id, tenant_id, scopes_csv, issued_at,
                   expires_at, label)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    token_id, tenant_id, ",".join(scope_list),
                    now.isoformat(),
                    expires.isoformat() if expires else None,
                    label,
                ),
            )
            conn.commit()
        return Token(
            token_id=token_id, tenant_id=tenant_id,
            scopes=scope_list, issued_at=now,
            expires_at=expires, label=label,
        )

    def lookup(self, token_id: str) -> Token | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tokens WHERE token_id = ?", (token_id,),
            ).fetchone()
        return _row_to_token(row) if row else None

    def revoke(self, token_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM tokens WHERE token_id = ?", (token_id,),
            )
            conn.commit()
        return cur.rowcount > 0

    # ── tenant budgets ────────────────────────────────────────

    def upsert_budget(
        self, tenant_id: str, monthly_budget_usd: float, *, notes: str = "",
    ) -> TenantBudget:
        period_start = _month_start(datetime.now(UTC))
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tenant_budgets
                  (tenant_id, monthly_budget_usd, spent_usd,
                   period_start, notes)
                VALUES (?, ?, 0.0, ?, ?)
                ON CONFLICT(tenant_id) DO UPDATE SET
                  monthly_budget_usd = excluded.monthly_budget_usd,
                  notes = excluded.notes
                """,
                (
                    tenant_id, float(monthly_budget_usd),
                    period_start.isoformat(), notes,
                ),
            )
            conn.commit()
        return self.get_budget(tenant_id)  # type: ignore[return-value]

    def get_budget(self, tenant_id: str) -> TenantBudget | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tenant_budgets WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
        if row is None:
            return None
        return TenantBudget(
            tenant_id=row["tenant_id"],
            monthly_budget_usd=float(row["monthly_budget_usd"]),
            spent_usd=float(row["spent_usd"]),
            period_start=datetime.fromisoformat(row["period_start"]),
            notes=str(row["notes"] or ""),
        )

    def record_spend(
        self, tenant_id: str, amount_usd: float,
    ) -> TenantBudget:
        """Increment ``spent_usd`` for ``tenant_id`` (atomic)."""
        if amount_usd < 0:
            msg = f"amount_usd must be ≥ 0; got {amount_usd}"
            raise ValueError(msg)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE tenant_budgets
                SET spent_usd = spent_usd + ?
                WHERE tenant_id = ?
                """,
                (float(amount_usd), tenant_id),
            )
            conn.commit()
        b = self.get_budget(tenant_id)
        if b is None:
            msg = f"unknown tenant: {tenant_id!r}"
            raise AuthError(msg, code="UNKNOWN_TENANT")
        return b

    def reset_period(self, tenant_id: str) -> None:
        """Reset spent_usd + period_start to the start of this month."""
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE tenant_budgets
                SET spent_usd = 0.0, period_start = ?
                WHERE tenant_id = ?
                """,
                (_month_start(datetime.now(UTC)).isoformat(), tenant_id),
            )
            conn.commit()

    # ── internals ─────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn


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


def _row_to_token(row: sqlite3.Row) -> Token:
    issued = datetime.fromisoformat(row["issued_at"])
    expires_raw = row["expires_at"]
    expires = (
        datetime.fromisoformat(expires_raw) if expires_raw else None
    )
    return Token(
        token_id=row["token_id"],
        tenant_id=row["tenant_id"],
        scopes=tuple(
            s for s in str(row["scopes_csv"] or "").split(",") if s
        ),
        issued_at=issued, expires_at=expires,
        label=str(row["label"] or ""),
    )


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


__all__ = [
    "AuthError",
    "AuthStore",
    "Token",
    "TenantBudget",
    "active_tenant",
    "gate_spend",
    "get_auth_store",
    "parse_bearer",
    "require_auth",
    "reset_active_tenant",
    "reset_auth_store",
    "set_active_tenant",
    "tenant_budget_remaining",
]
