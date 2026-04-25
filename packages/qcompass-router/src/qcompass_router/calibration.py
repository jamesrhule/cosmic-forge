"""Calibration cache + drift detection.

A small SQLite store records per-device FoMaC samples. The router asks
the cache for a `drift_score` (|latest - 7d_median| / 7d_median over the
two-qubit error rate) and refuses to route when the score exceeds 3.0.

QDMI integration is optional: when `qdmi` is importable, `pull_qdmi`
fetches a fresh sample. Otherwise the caller is expected to feed samples
in via `update()` (e.g. from a provider's `Backend.properties()` poll).
"""

from __future__ import annotations

import sqlite3
import statistics
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DRIFT_THRESHOLD = 3.0


class CalibrationDrift(Exception):
    """Raised when calibration drift exceeds the configured threshold.

    Carries `error_code="CALIBRATION_DRIFT"` for downstream callers.
    """

    error_code: str = "CALIBRATION_DRIFT"

    def __init__(
        self,
        message: str = "CALIBRATION_DRIFT",
        *,
        provider: str | None = None,
        backend: str | None = None,
        drift: float | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.backend = backend
        self.drift = drift


@dataclass(frozen=True)
class FoMaC:
    """Figures of Merit and Calibration sample."""

    two_q_error: float
    readout_error: float
    t1_us: float
    t2_us: float
    recorded_at: datetime | None = None


_DDL = """
CREATE TABLE IF NOT EXISTS devices (
    provider TEXT NOT NULL,
    backend TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    two_q_error REAL,
    readout_error REAL,
    t1_us REAL,
    t2_us REAL
);
CREATE INDEX IF NOT EXISTS ix_devices_lookup ON devices(provider, backend, recorded_at);
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(ts: datetime | None) -> str:
    return (ts or _utcnow()).astimezone(timezone.utc).isoformat()


def _from_iso(s: str) -> datetime:
    # Handle both "...+00:00" and naive ISO inputs.
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return _utcnow()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class CalibrationCache:
    """SQLite-backed cache of recent FoMaC samples."""

    DEFAULT_DB: Path = Path.home() / ".cache/qcompass/calibration.sqlite"

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else self.DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(_DDL)
            conn.commit()

    # -- public API -----------------------------------------------------
    def update(
        self,
        provider: str,
        backend: str,
        fomac: FoMaC,
    ) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO devices(provider, backend, recorded_at, "
                "two_q_error, readout_error, t1_us, t2_us) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    provider,
                    backend,
                    _to_iso(fomac.recorded_at),
                    fomac.two_q_error,
                    fomac.readout_error,
                    fomac.t1_us,
                    fomac.t2_us,
                ),
            )
            conn.commit()

    def latest(self, provider: str, backend: str) -> FoMaC | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT recorded_at, two_q_error, readout_error, t1_us, t2_us "
                "FROM devices WHERE provider=? AND backend=? "
                "ORDER BY recorded_at DESC LIMIT 1",
                (provider, backend),
            ).fetchone()
        if row is None:
            return None
        return FoMaC(
            two_q_error=row[1],
            readout_error=row[2],
            t1_us=row[3],
            t2_us=row[4],
            recorded_at=_from_iso(row[0]),
        )

    def drift_score(self, provider: str, backend: str) -> float:
        """Ratio: |latest - 7d_median| / 7d_median over `two_q_error`.

        Returns 0.0 when there's no history (first sample) or the median
        is non-positive — the router treats these as "no signal" and
        proceeds.
        """
        latest = self.latest(provider, backend)
        if latest is None:
            return 0.0
        cutoff = _utcnow() - timedelta(days=7)
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT two_q_error FROM devices "
                "WHERE provider=? AND backend=? AND recorded_at>=?",
                (provider, backend, _to_iso(cutoff)),
            ).fetchall()
        values = [r[0] for r in rows if r[0] is not None]
        if len(values) < 2:
            return 0.0
        median = statistics.median(values)
        if median <= 0:
            return 0.0
        return abs(latest.two_q_error - median) / median

    def is_stale(
        self,
        provider: str,
        backend: str,
        max_age_h: int = 24,
    ) -> bool:
        """True iff the most recent sample is older than `max_age_h` hours
        OR no sample exists at all.
        """
        latest = self.latest(provider, backend)
        if latest is None or latest.recorded_at is None:
            return True
        age = _utcnow() - latest.recorded_at
        return age > timedelta(hours=max_age_h)

    def has_history(self, provider: str, backend: str) -> bool:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT 1 FROM devices WHERE provider=? AND backend=? LIMIT 1",
                (provider, backend),
            ).fetchone()
        return row is not None

    # -- optional QDMI / provider-properties hooks ----------------------
    def pull_qdmi(self, provider: str, backend: str) -> FoMaC | None:
        """Sample via QDMI if available; returns None otherwise.

        QDMI is soft-imported so the cache is usable without `extern/QDMI`
        being built.
        """
        try:
            import qdmi  # type: ignore
        except Exception:  # noqa: BLE001
            return None
        try:
            handle = qdmi.session().device(f"{provider}:{backend}")  # type: ignore[attr-defined]
            two_q = float(handle.two_qubit_error())
            readout = float(handle.readout_error())
            t1 = float(handle.t1_us())
            t2 = float(handle.t2_us())
        except Exception:  # noqa: BLE001
            return None
        sample = FoMaC(
            two_q_error=two_q,
            readout_error=readout,
            t1_us=t1,
            t2_us=t2,
            recorded_at=_utcnow(),
        )
        self.update(provider, backend, sample)
        return sample

    # -- internals ------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, isolation_level=None)


def assert_no_drift(
    cache: CalibrationCache,
    provider: str,
    backend: str,
    *,
    threshold: float = DRIFT_THRESHOLD,
) -> dict[str, Any]:
    """Raise `CalibrationDrift` when drift>threshold; return metadata otherwise."""
    drift = cache.drift_score(provider, backend)
    stale = cache.is_stale(provider, backend)
    if drift > threshold:
        raise CalibrationDrift(
            "CALIBRATION_DRIFT",
            provider=provider,
            backend=backend,
            drift=drift,
        )
    return {
        "provider": provider,
        "backend": backend,
        "drift_score": drift,
        "stale": stale,
        "threshold": threshold,
    }
