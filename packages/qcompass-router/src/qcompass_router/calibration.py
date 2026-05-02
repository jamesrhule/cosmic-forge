"""Calibration drift cache.

Persists a per-(provider, backend, day) snapshot of three QPU
metrics — two-qubit error, readout error, and a single T1/T2
proxy — and refuses submissions when today's value drifts >3σ
from the 7-day median.

PROMPT 6 v2 layers a second table, ``devices``, with the spec's
canonical schema:

    devices(provider, backend, recorded_at, two_q_error,
            readout_error, t1_us, t2_us)

The v2 API exposes :class:`DeviceCalibration` snapshots, a
``record_device`` writer, and a ``drift_score()`` helper that
returns the relative deviation
``|latest - 7d_median| / 7d_median`` per metric (the formula the
v2 spec mandates).

The v1 ``calibration`` table + :class:`CalibrationSnapshot` API
stay byte-stable so existing audit tests + downstream callers keep
working unchanged.

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


@dataclass(frozen=True)
class DeviceCalibration:
    """One QDMI FoMaC snapshot with split T1 / T2 (PROMPT 6 v2)."""

    provider: str
    backend: str
    recorded_at: datetime
    two_q_error: float
    readout_error: float
    t1_us: float
    t2_us: float


_DRIFT_SIGMA = 3.0
_WINDOW_DAYS = 7
_V2_METRICS = ("two_q_error", "readout_error", "t1_us", "t2_us")


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
            # PROMPT 6 v2 §"calibration cache" — split T1 / T2 columns
            # and use a high-resolution recorded_at primary key (the
            # cache may store multiple snapshots per device per day).
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    provider        TEXT NOT NULL,
                    backend         TEXT NOT NULL,
                    recorded_at     TEXT NOT NULL,
                    two_q_error     REAL NOT NULL,
                    readout_error   REAL NOT NULL,
                    t1_us           REAL NOT NULL,
                    t2_us           REAL NOT NULL,
                    PRIMARY KEY (provider, backend, recorded_at)
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

    # ── PROMPT 6 v2: device API ─────────────────────────────────

    def record_device(self, snap: DeviceCalibration) -> None:
        """Insert / update a v2 device-calibration snapshot."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO devices
                  (provider, backend, recorded_at, two_q_error,
                   readout_error, t1_us, t2_us)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, backend, recorded_at) DO UPDATE SET
                  two_q_error = excluded.two_q_error,
                  readout_error = excluded.readout_error,
                  t1_us = excluded.t1_us,
                  t2_us = excluded.t2_us
                """,
                (
                    snap.provider, snap.backend,
                    snap.recorded_at.isoformat(),
                    snap.two_q_error, snap.readout_error,
                    snap.t1_us, snap.t2_us,
                ),
            )
            conn.commit()

    def device_history(
        self,
        provider: str,
        backend: str,
        *,
        anchor: datetime | None = None,
        window_days: int = _WINDOW_DAYS,
    ) -> list[DeviceCalibration]:
        """Return v2 device snapshots for the trailing window.

        ``anchor`` defaults to now. ``window_days`` defaults to 7
        (the canonical PROMPT 6 v2 horizon).
        """
        anchor = anchor or datetime.utcnow()
        start = anchor - timedelta(days=window_days)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT provider, backend, recorded_at, two_q_error,
                       readout_error, t1_us, t2_us
                FROM devices
                WHERE provider = ? AND backend = ?
                  AND recorded_at >= ? AND recorded_at < ?
                ORDER BY recorded_at
                """,
                (provider, backend, start.isoformat(), anchor.isoformat()),
            ).fetchall()
        return [_row_to_device(row) for row in rows]

    def latest_device(
        self, provider: str, backend: str,
    ) -> DeviceCalibration | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT provider, backend, recorded_at, two_q_error,
                       readout_error, t1_us, t2_us
                FROM devices
                WHERE provider = ? AND backend = ?
                ORDER BY recorded_at DESC LIMIT 1
                """,
                (provider, backend),
            ).fetchone()
        return _row_to_device(row) if row else None

    def drift_score(
        self,
        provider: str,
        backend: str,
        *,
        anchor: datetime | None = None,
    ) -> dict[str, float]:
        """Return per-metric ``|latest - 7d_median| / |7d_median|``.

        PROMPT 6 v2 §"calibration cache" pins this exact relative
        formula. Metrics with no 7-day history (or a zero median)
        return 0.0 — neutral, will not trigger the >3σ refusal gate.
        """
        anchor = anchor or datetime.utcnow()
        latest = self.latest_device(provider, backend)
        history = self.device_history(
            provider, backend, anchor=anchor, window_days=_WINDOW_DAYS,
        )
        scores: dict[str, float] = {}
        if latest is None or not history:
            return {m: 0.0 for m in _V2_METRICS}
        for metric in _V2_METRICS:
            values = [getattr(s, metric) for s in history]
            med = median(values)
            obs = getattr(latest, metric)
            if med == 0.0:
                scores[metric] = 0.0
            else:
                scores[metric] = abs(obs - med) / abs(med)
        return scores

    def check_device_drift(
        self,
        provider: str,
        backend: str,
        *,
        anchor: datetime | None = None,
        sigma_floor: float = _DRIFT_SIGMA,
    ) -> None:
        """v2 drift gate: same >3σ refusal but using the v2 ``devices``
        table and the relative-to-median ``drift_score`` formula.

        Raises :class:`CalibrationDrift` (code ``CALIBRATION_DRIFT``)
        when any metric drifts beyond ``sigma_floor`` × MAD-derived σ.
        """
        anchor = anchor or datetime.utcnow()
        history = self.device_history(
            provider, backend, anchor=anchor, window_days=_WINDOW_DAYS,
        )
        if len(history) < 3:
            return
        latest = self.latest_device(provider, backend)
        if latest is None:
            return
        for metric in _V2_METRICS:
            values = [getattr(s, metric) for s in history]
            med = median(values)
            sigma = _stdev_from_median(values, med)
            obs = getattr(latest, metric)
            if sigma == 0.0:
                if abs(obs - med) <= 1e-9:
                    continue
                msg = (
                    f"{provider}/{backend} {metric}={obs:.6g} drifts "
                    f"from a perfectly stable 7-day median ({med:.6g})."
                )
                raise CalibrationDrift(
                    msg, provider=provider, backend=backend,
                    metric=metric, observed=obs,
                    median_7d=med, sigma_7d=0.0,
                )
            if abs(obs - med) > sigma_floor * sigma:
                msg = (
                    f"{provider}/{backend} {metric}={obs:.6g} drifts "
                    f">{sigma_floor}σ from 7-day median "
                    f"({med:.6g} ± {sigma:.6g})."
                )
                raise CalibrationDrift(
                    msg, provider=provider, backend=backend,
                    metric=metric, observed=obs,
                    median_7d=med, sigma_7d=sigma,
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


def _row_to_device(row: sqlite3.Row) -> DeviceCalibration:
    return DeviceCalibration(
        provider=row["provider"],
        backend=row["backend"],
        recorded_at=datetime.fromisoformat(row["recorded_at"]),
        two_q_error=float(row["two_q_error"]),
        readout_error=float(row["readout_error"]),
        t1_us=float(row["t1_us"]),
        t2_us=float(row["t2_us"]),
    )


def load_calibration_seed(
    cache: "CalibrationCache",
    name: str = "ibm_kingston",
) -> int:
    """Populate the v2 ``devices`` table from a bundled YAML.

    Reads ``fixtures/calibration_seed/<name>.yaml`` and inserts each
    snapshot via :meth:`CalibrationCache.record_device`. Returns the
    number of rows inserted.

    YAML schema::

        provider: ibm
        backend: ibm_kingston
        snapshots:
          - recorded_at: 2026-04-25T00:00:00
            two_q_error: 0.010
            readout_error: 0.020
            t1_us: 110.0
            t2_us: 95.0
          ...
    """
    import importlib.resources as resources
    import yaml

    text = (
        resources.files("qcompass_router.fixtures.calibration_seed")
        .joinpath(f"{name}.yaml")
        .read_text()
    )
    payload = yaml.safe_load(text) or {}
    provider = str(payload.get("provider") or "")
    backend = str(payload.get("backend") or "")
    if not provider or not backend:
        msg = (
            f"calibration seed {name!r} missing 'provider' or 'backend'."
        )
        raise ValueError(msg)
    inserted = 0
    for snap in payload.get("snapshots") or []:
        cache.record_device(DeviceCalibration(
            provider=provider, backend=backend,
            recorded_at=datetime.fromisoformat(str(snap["recorded_at"])),
            two_q_error=float(snap["two_q_error"]),
            readout_error=float(snap["readout_error"]),
            t1_us=float(snap["t1_us"]),
            t2_us=float(snap["t2_us"]),
        ))
        inserted += 1
    return inserted
