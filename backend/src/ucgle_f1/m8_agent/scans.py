"""Scan persistence (PROMPT 8 v2 §B; Postgres since P3-01).

Parameter scans (ξ-θ heatmaps, multi-fixture sweeps) for the frontend's
Research view, served by the ``/api/qcompass/scans`` routes in
:mod:`qcompass_routes`.

Table ``public.scans`` (``supabase/migrations/20261031160000_*``):
``scan_id, tenant_id → public.tenants, domain, kind, axes, payload,
provenance, created_at``, with tenant RLS. The payload is opaque JSON —
typically the ``ScanResult`` shape from ``src/types/domain.ts`` — and is not
interpreted here.

Tenants are named by slug (or UUID); with ``tenant_id`` given, every read
and delete is scoped to that tenant, so another tenant's scan is "not found".
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.expression import bindparam

from ..db import get_engine


@dataclass
class ScanRecord:
    """One persisted scan."""

    scan_id: str
    domain: str
    kind: str
    axes: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tenant_id: str = ""

    def to_envelope(self) -> dict[str, Any]:
        """Serialise as the frontend ``ScanResult`` envelope."""
        return {
            "scanId": self.scan_id,
            "domain": self.domain,
            "kind": self.kind,
            "axes": self.axes,
            "payload": self.payload,
            "provenance": self.provenance,
            "createdAt": self.created_at.isoformat(),
        }


_SELECT = (
    "select s.scan_id, s.domain, s.kind, s.axes, s.payload, s.provenance, s.created_at, t.slug "
    "from public.scans s join public.tenants t on t.id = s.tenant_id"
)


class ScanRegistry:
    """Postgres-backed persistence for parameter scans."""

    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def _tenant_uuid(self, tenant_id: str, *, create: bool) -> str | None:
        from .auth import AuthStore

        store = AuthStore(self._engine)
        if create:
            return store.ensure_tenant(tenant_id)
        found = store.resolve_tenant(tenant_id)
        return found[0] if found else None

    # ── public API ─────────────────────────────────────────────────

    def submit(
        self,
        *,
        tenant_id: str,
        domain: str,
        kind: str,
        axes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> ScanRecord:
        """Persist a new scan for ``tenant_id`` and return its record."""
        if not tenant_id:
            msg = "tenant_id is required"
            raise ValueError(msg)
        record = ScanRecord(
            scan_id=f"scan_{secrets.token_hex(6)}",
            tenant_id=tenant_id,
            domain=domain, kind=kind,
            axes=axes or {}, payload=payload or {},
            provenance=provenance or {},
        )
        tenant_uuid = self._tenant_uuid(tenant_id, create=True)
        stmt = text(
            "insert into public.scans "
            "(scan_id, tenant_id, domain, kind, axes, payload, provenance, created_at) "
            "values (:id, cast(:t as uuid), :d, :k, :a, :p, :pr, :c)"
        ).bindparams(
            bindparam("a", type_=JSONB), bindparam("p", type_=JSONB), bindparam("pr", type_=JSONB),
        )
        with self._engine.begin() as conn:
            conn.execute(stmt, {
                "id": record.scan_id, "t": tenant_uuid, "d": domain, "k": kind,
                "a": record.axes, "p": record.payload, "pr": record.provenance,
                "c": record.created_at,
            })
        return record

    def get(self, scan_id: str, *, tenant_id: str | None = None) -> ScanRecord | None:
        """The scan, or None. With ``tenant_id``, another tenant's scan is None."""
        sql, params = _SELECT + " where s.scan_id = :id", {"id": scan_id}
        if tenant_id is not None:
            tenant_uuid = self._tenant_uuid(tenant_id, create=False)
            if tenant_uuid is None:
                return None
            sql += " and s.tenant_id = cast(:t as uuid)"
            params["t"] = tenant_uuid
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).first()
        return _row_to_record(row) if row else None

    def list_all(
        self, *, domain: str | None = None, limit: int = 100,
        tenant_id: str | None = None,
    ) -> list[ScanRecord]:
        clauses: list[str] = []
        params: dict[str, Any] = {"limit": max(0, min(limit, 1000))}
        if domain is not None:
            clauses.append("s.domain = :d")
            params["d"] = domain
        if tenant_id is not None:
            tenant_uuid = self._tenant_uuid(tenant_id, create=False)
            if tenant_uuid is None:
                return []
            clauses.append("s.tenant_id = cast(:t as uuid)")
            params["t"] = tenant_uuid
        sql = _SELECT
        if clauses:
            sql += " where " + " and ".join(clauses)
        sql += " order by s.created_at desc limit :limit"
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).all()
        return [_row_to_record(r) for r in rows]

    def delete(self, scan_id: str, *, tenant_id: str | None = None) -> bool:
        sql, params = "delete from public.scans where scan_id = :id", {"id": scan_id}
        if tenant_id is not None:
            tenant_uuid = self._tenant_uuid(tenant_id, create=False)
            if tenant_uuid is None:
                return False
            sql += " and tenant_id = cast(:t as uuid)"
            params["t"] = tenant_uuid
        with self._engine.begin() as conn:
            res = conn.execute(text(sql), params)
        return res.rowcount > 0

    def ping(self) -> None:
        """Raise if the database is unreachable (``/readyz``)."""
        with self._engine.connect() as conn:
            conn.execute(text("select 1"))


_REGISTRY: ScanRegistry | None = None
_REGISTRY_LOCK = threading.Lock()


def get_scan_registry() -> ScanRegistry:
    """Return the process-wide :class:`ScanRegistry` singleton."""
    global _REGISTRY
    with _REGISTRY_LOCK:
        if _REGISTRY is None:
            _REGISTRY = ScanRegistry()
        return _REGISTRY


def reset_scan_registry() -> None:
    """Drop the singleton (tests that switch ``DATABASE_URL``)."""
    global _REGISTRY
    with _REGISTRY_LOCK:
        _REGISTRY = None


def _row_to_record(row: Any) -> ScanRecord:
    return ScanRecord(
        scan_id=row[0], domain=row[1], kind=row[2],
        axes=row[3] or {}, payload=row[4] or {}, provenance=row[5] or {},
        created_at=row[6], tenant_id=row[7],
    )


__all__ = [
    "ScanRecord",
    "ScanRegistry",
    "asdict",
    "get_scan_registry",
    "reset_scan_registry",
]
