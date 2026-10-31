"""SQLite leaderboard store."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


def _default_db_path() -> Path:
    env = os.environ.get("QCOMPASS_BENCH_DB")
    if env:
        return Path(env)
    return Path.home() / ".qcompass" / "bench" / "leaderboard.sqlite"


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


class LeaderboardStore:
    """Append-only SQLite store for bench runs."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _default_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain            TEXT NOT NULL,
                    fixture           TEXT NOT NULL,
                    package_version   TEXT NOT NULL,
                    started_at        TEXT NOT NULL,
                    wall_seconds      REAL NOT NULL,
                    classical_energy  REAL,
                    quantum_energy    REAL,
                    provenance_hash   TEXT NOT NULL,
                    ok                INTEGER NOT NULL,
                    notes             TEXT NOT NULL DEFAULT ''
                )
                """,
            )
            conn.commit()

    def record(self, entry: BenchEntry) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO runs (
                    domain, fixture, package_version, started_at,
                    wall_seconds, classical_energy, quantum_energy,
                    provenance_hash, ok, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.domain,
                    entry.fixture,
                    entry.package_version,
                    entry.started_at.isoformat(),
                    entry.wall_seconds,
                    entry.classical_energy,
                    entry.quantum_energy,
                    entry.provenance_hash,
                    1 if entry.ok else 0,
                    entry.notes,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid or 0)

    def recent(
        self, *, since: timedelta | None = None,
    ) -> list[BenchEntry]:
        cutoff: datetime | None
        cutoff = (datetime.utcnow() - since) if since else None
        with self._connect() as conn:
            if cutoff is not None:
                rows = conn.execute(
                    "SELECT * FROM runs WHERE started_at >= ? "
                    "ORDER BY started_at DESC",
                    (cutoff.isoformat(),),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM runs ORDER BY started_at DESC",
                ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def all(self) -> list[BenchEntry]:
        return self.recent(since=None)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn


def _row_to_entry(row: sqlite3.Row) -> BenchEntry:
    return BenchEntry(
        domain=row["domain"],
        fixture=row["fixture"],
        package_version=row["package_version"],
        started_at=datetime.fromisoformat(row["started_at"]),
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
