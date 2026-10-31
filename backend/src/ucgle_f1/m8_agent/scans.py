"""Scan persistence (PROMPT 8 v2 §B).

Mirrors the existing :mod:`runs` registry but stores parameter
scans (e.g. ξ-θ heatmaps, multi-fixture sweeps) in SQLite. The
frontend's Research view consumes the persisted records via the
``/api/scans`` HTTP endpoints registered in :mod:`qcompass_routes`.

Storage:
  ${UCGLE_F1_STATE_DIR:-~/.ucgle_f1}/scans.sqlite

Schema:
  scans(scan_id, domain, kind, axes_json, payload_json,
        provenance_json, created_at)

The payload is opaque JSON — typically the existing
``ScanResult`` shape from ``src/types/domain.ts`` (xAxis / yAxis /
eta_B_grid / planckBand) — the registry does not interpret it.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


_DEFAULT_DB_ENV = "UCGLE_F1_STATE_DIR"


def _default_db_path() -> Path:
    root = Path(os.environ.get(_DEFAULT_DB_ENV, str(Path.home() / ".ucgle_f1")))
    return root / "scans.sqlite"


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


class ScanRegistry:
    """SQLite-backed persistence for parameter scans."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _default_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scans (
                    scan_id          TEXT PRIMARY KEY,
                    domain           TEXT NOT NULL,
                    kind             TEXT NOT NULL,
                    axes_json        TEXT NOT NULL,
                    payload_json     TEXT NOT NULL,
                    provenance_json  TEXT NOT NULL,
                    created_at       TEXT NOT NULL
                )
                """
            )
            conn.commit()

    # ── public API ─────────────────────────────────────────────────

    def submit(
        self,
        *,
        domain: str,
        kind: str,
        axes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> ScanRecord:
        """Persist a new scan and return its record."""
        record = ScanRecord(
            scan_id=f"scan_{secrets.token_hex(6)}",
            domain=domain, kind=kind,
            axes=axes or {}, payload=payload or {},
            provenance=provenance or {},
        )
        self._insert(record)
        return record

    def get(self, scan_id: str) -> ScanRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM scans WHERE scan_id = ?", (scan_id,),
            ).fetchone()
        return _row_to_record(row) if row else None

    def list_all(
        self, *, domain: str | None = None, limit: int = 100,
    ) -> list[ScanRecord]:
        sql = "SELECT * FROM scans"
        params: list[Any] = []
        if domain is not None:
            sql += " WHERE domain = ?"
            params.append(domain)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_record(r) for r in rows]

    def delete(self, scan_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM scans WHERE scan_id = ?", (scan_id,),
            )
            conn.commit()
        return cur.rowcount > 0

    # ── internals ──────────────────────────────────────────────────

    def _insert(self, record: ScanRecord) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO scans
                  (scan_id, domain, kind, axes_json, payload_json,
                   provenance_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.scan_id, record.domain, record.kind,
                    json.dumps(record.axes, separators=(",", ":")),
                    json.dumps(record.payload, separators=(",", ":")),
                    json.dumps(record.provenance, separators=(",", ":")),
                    record.created_at.isoformat(),
                ),
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn


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
    """Drop the singleton — primarily for tests that swap ``UCGLE_F1_STATE_DIR``."""
    global _REGISTRY
    with _REGISTRY_LOCK:
        _REGISTRY = None


def _row_to_record(row: sqlite3.Row | dict[str, Any]) -> ScanRecord:
    if isinstance(row, sqlite3.Row):
        row = dict(row)
    return ScanRecord(
        scan_id=row["scan_id"],
        domain=row["domain"],
        kind=row["kind"],
        axes=json.loads(row["axes_json"] or "{}"),
        payload=json.loads(row["payload_json"] or "{}"),
        provenance=json.loads(row["provenance_json"] or "{}"),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


__all__ = [
    "ScanRecord",
    "ScanRegistry",
    "asdict",
    "get_scan_registry",
    "reset_scan_registry",
]
