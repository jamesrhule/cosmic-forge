"""Leaderboard store (P3-01: Supabase Postgres, was SQLite).

Rows live in ``public.bench_runs``, created by
``supabase/migrations/20261031170000_qcompass_package_stores.sql``. The store
takes a SQLAlchemy ``Engine`` (the worker injects its pool); without one it
uses ``DATABASE_URL`` via :func:`qcompass_core.db.engine_from_env`, and a
missing URL raises ``BLOCKED-ON-JAMES:DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from qcompass_core.db import engine_from_env
from sqlalchemy import text

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy import Engine


@dataclass(frozen=True)
class BenchEntry:
    """One leaderboard row."""

    domain: str
    fixture: str
    package_version: str
    started_at: datetime
    wall_seconds: float
    classical_energy: float | None
    quantum_energy: float | None
    provenance_hash: str
    ok: bool
    notes: str = ""


_COLUMNS = (
    "domain, fixture, package_version, started_at, wall_seconds, "
    "classical_energy, quantum_energy, provenance_hash, ok, notes"
)


class LeaderboardStore:
    """Append-only Postgres store for bench runs."""

    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine if engine is not None else engine_from_env()

    def record(self, entry: BenchEntry) -> int:
        started_at = entry.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        with self._engine.begin() as conn:
            new_id = conn.execute(
                text(
                    f"INSERT INTO public.bench_runs ({_COLUMNS}) VALUES ("
                    ":domain, :fixture, :package_version, :started_at, :wall_seconds, "
                    ":classical_energy, :quantum_energy, :provenance_hash, :ok, :notes"
                    ") RETURNING id",
                ),
                {
                    "domain": entry.domain,
                    "fixture": entry.fixture,
                    "package_version": entry.package_version,
                    "started_at": started_at,
                    "wall_seconds": entry.wall_seconds,
                    "classical_energy": entry.classical_energy,
                    "quantum_energy": entry.quantum_energy,
                    "provenance_hash": entry.provenance_hash,
                    "ok": entry.ok,
                    "notes": entry.notes,
                },
            ).scalar_one()
        return int(new_id)

    def recent(
        self, *, since: timedelta | None = None,
    ) -> list[BenchEntry]:
        cutoff = (datetime.now(UTC) - since) if since else None
        with self._engine.connect() as conn:
            if cutoff is not None:
                rows = conn.execute(
                    text(
                        f"SELECT {_COLUMNS} FROM public.bench_runs "
                        "WHERE started_at >= :cutoff ORDER BY started_at DESC, id DESC",
                    ),
                    {"cutoff": cutoff},
                ).mappings().all()
            else:
                rows = conn.execute(
                    text(
                        f"SELECT {_COLUMNS} FROM public.bench_runs "
                        "ORDER BY started_at DESC, id DESC",
                    ),
                ).mappings().all()
        return [_row_to_entry(row) for row in rows]

    def all(self) -> list[BenchEntry]:
        return self.recent(since=None)


def _row_to_entry(row: Mapping[str, Any]) -> BenchEntry:
    return BenchEntry(
        domain=row["domain"],
        fixture=row["fixture"],
        package_version=row["package_version"],
        started_at=row["started_at"].astimezone(UTC),
        wall_seconds=float(row["wall_seconds"]),
        classical_energy=(
            None if row["classical_energy"] is None
            else float(row["classical_energy"])
        ),
        quantum_energy=(
            None if row["quantum_energy"] is None
            else float(row["quantum_energy"])
        ),
        provenance_hash=row["provenance_hash"],
        ok=bool(row["ok"]),
        notes=row["notes"],
    )
