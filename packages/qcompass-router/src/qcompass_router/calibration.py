"""Calibration drift cache.

Persists a per-(provider, backend, day) snapshot of three QPU
metrics — two-qubit error, readout error, and a single T1/T2
proxy — and refuses submissions when today's value drifts >3σ
from the 7-day median.

Persistence: SQLite at ``~/.cache/qcompass/calibration.sqlite``
(override with the ``QCOMPASS_CALIBRATION_DB`` env var, primarily
for tests).
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Iterable


_CALIBRATION_DB_ENV = "QCOMPASS_CALIBRATION_DB"


def _default_db_path() -> Path:
    env = os.environ.get(_CALIBRATION_DB_ENV)
    if env:
        return Path(env)
    return Path.home() / ".cache" / "qcompass" / "calibration.sqlite"


class CalibrationDrift(Exception):
    """Raised when today's calibration drifts >3σ from the 7-day median.

    Carries the ``CALIBRATION_DRIFT`` code so the agent + frontend
    can branch on it without parsing the message text.
    """

    code: str = "CALIBRATION_DRIFT"

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        backend: str,
        metric: str,
        observed: float,
        median_7d: float,
        sigma_7d: float,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.backend = backend
        self.metric = metric
        self.observed = observed
        self.median_7d = median_7d
        self.sigma_7d = sigma_7d


@dataclass(frozen=True)
class CalibrationSnapshot:
    """One day's calibration record."""

    provider: str
    backend: str
    day: date
    two_qubit_error: float
    readout_error: float
    t1_t2_us: float


_DRIFT_SIGMA = 3.0
_WINDOW_DAYS = 7


class CalibrationCache:
    """SQLite-backed per-day calibration cache + drift gate."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _default_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calibration (
                    provider          TEXT NOT NULL,
                    backend           TEXT NOT NULL,
                    day               TEXT NOT NULL,
                    two_qubit_error   REAL NOT NULL,
                    readout_error     REAL NOT NULL,
                    t1_t2_us          REAL NOT NULL,
                    recorded_at       TEXT NOT NULL,
                    PRIMARY KEY (provider, backend, day)
                )
                """
            )
            conn.commit()

    # ── Recording ────────────────────────────────────────────────

    def record(self, snap: CalibrationSnapshot) -> None:
        """Insert / update one day's snapshot."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO calibration
                  (provider, backend, day, two_qubit_error,
                   readout_error, t1_t2_us, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, backend, day) DO UPDATE SET
                  two_qubit_error = excluded.two_qubit_error,
                  readout_error = excluded.readout_error,
                  t1_t2_us = excluded.t1_t2_us,
                  recorded_at = excluded.recorded_at
                """,
                (
                    snap.provider,
                    snap.backend,
                    snap.day.isoformat(),
                    snap.two_qubit_error,
                    snap.readout_error,
                    snap.t1_t2_us,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    # ── Drift gate ───────────────────────────────────────────────

    def check_drift(
        self,
        provider: str,
        backend: str,
        today: date | None = None,
    ) -> None:
        """Raise :class:`CalibrationDrift` if today's snapshot drifts.

        ``check_drift`` requires:
          - at least 3 historical snapshots in the trailing window
            (otherwise we can't compute a meaningful sigma; we pass
            silently — first-week behaviour).
          - today's snapshot already recorded.
        """
        today = today or date.today()
        history = list(
            self._history(provider, backend, today, _WINDOW_DAYS),
        )
        if len(history) < 3:
            return  # not enough history yet — pass silently.
        today_snap = self._snapshot(provider, backend, today)
        if today_snap is None:
            return  # no snapshot today — gate doesn't fire.

        for metric in ("two_qubit_error", "readout_error", "t1_t2_us"):
            values = [getattr(s, metric) for s in history]
            med = median(values)
            sigma = _stdev_from_median(values, med)
            observed = getattr(today_snap, metric)
            if sigma == 0.0:
                # Perfectly stable history → any deviation > 1e-6 is
                # treated as infinite-σ drift.
                if abs(observed - med) <= 1e-6:
                    continue
                msg = (
                    f"{provider}/{backend} {metric}={observed:.6g} "
                    f"deviates from a perfectly-stable 7-day median "
                    f"({med:.6g}); flagging as drift."
                )
                raise CalibrationDrift(
                    msg,
                    provider=provider,
                    backend=backend,
                    metric=metric,
                    observed=observed,
                    median_7d=med,
                    sigma_7d=0.0,
                )
            if abs(observed - med) > _DRIFT_SIGMA * sigma:
                msg = (
                    f"{provider}/{backend} {metric}={observed:.6g} "
                    f"drifts >{_DRIFT_SIGMA}σ from 7-day median "
                    f"({med:.6g} ± {sigma:.6g})."
                )
                raise CalibrationDrift(
                    msg,
                    provider=provider,
                    backend=backend,
                    metric=metric,
                    observed=observed,
                    median_7d=med,
                    sigma_7d=sigma,
                )

    # ── Internal queries ─────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _history(
        self, provider: str, backend: str, anchor: date, window: int,
    ) -> Iterable[CalibrationSnapshot]:
        start = anchor - timedelta(days=window)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT provider, backend, day, two_qubit_error,
                       readout_error, t1_t2_us
                FROM calibration
                WHERE provider = ? AND backend = ?
                  AND day >= ? AND day < ?
                ORDER BY day
                """,
                (provider, backend, start.isoformat(), anchor.isoformat()),
            ).fetchall()
        for row in rows:
            yield CalibrationSnapshot(
                provider=row["provider"],
                backend=row["backend"],
                day=date.fromisoformat(row["day"]),
                two_qubit_error=float(row["two_qubit_error"]),
                readout_error=float(row["readout_error"]),
                t1_t2_us=float(row["t1_t2_us"]),
            )

    def _snapshot(
        self, provider: str, backend: str, day: date,
    ) -> CalibrationSnapshot | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT provider, backend, day, two_qubit_error,
                       readout_error, t1_t2_us
                FROM calibration
                WHERE provider = ? AND backend = ? AND day = ?
                """,
                (provider, backend, day.isoformat()),
            ).fetchone()
        if row is None:
            return None
        return CalibrationSnapshot(
            provider=row["provider"],
            backend=row["backend"],
            day=date.fromisoformat(row["day"]),
            two_qubit_error=float(row["two_qubit_error"]),
            readout_error=float(row["readout_error"]),
            t1_t2_us=float(row["t1_t2_us"]),
        )


def _stdev_from_median(values: list[float], med: float) -> float:
    """Median absolute deviation × 1.4826 (robust σ estimate)."""
    if not values:
        return 0.0
    deviations = sorted(abs(v - med) for v in values)
    mad = deviations[len(deviations) // 2]
    return mad * 1.4826
