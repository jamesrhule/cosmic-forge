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

Router-branch 6B API (merged by P0-02) on the same ``devices`` table:
:class:`FoMaC` samples via :meth:`CalibrationCache.update`,
:meth:`~CalibrationCache.latest`, :meth:`~CalibrationCache.is_stale`,
:meth:`~CalibrationCache.has_history`, the optional QDMI pull
:meth:`~CalibrationCache.pull_qdmi`, and :func:`assert_no_drift` —
the router's per-backend gate (two-qubit-error relative drift above
:data:`DRIFT_THRESHOLD` raises ``CALIBRATION_DRIFT``).

Timestamps are timezone-aware UTC throughout: inputs are converted to
UTC (naive inputs are taken as UTC) and stored as ISO strings with a
``+00:00`` offset; rows read back are aware (legacy naive rows are
read as UTC).

Persistence (P3-01): Supabase Postgres tables
``public.router_calibration_daily`` (v1) and
``public.router_calibration_devices`` (v2 / FoMaC), created by
``supabase/migrations/20261031170000_qcompass_package_stores.sql``.
The cache takes a SQLAlchemy ``Engine`` (the API or worker injects its
pool); without one it uses ``DATABASE_URL`` via
:func:`qcompass_core.db.engine_from_env`, and a missing URL raises
``BLOCKED-ON-JAMES:DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import median
from typing import TYPE_CHECKING, Any

from qcompass_core.db import engine_from_env
from sqlalchemy import text

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy import Engine


def _utcnow() -> datetime:
    """Current time, timezone-aware UTC."""
    return datetime.now(UTC)


def _as_utc(ts: datetime) -> datetime:
    """Normalise ``ts`` to aware UTC; naive inputs are taken as UTC."""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


class CalibrationDrift(Exception):
    """Raised when calibration drifts beyond the gate.

    Carries the ``CALIBRATION_DRIFT`` code (as both ``code`` and the
    router-branch name ``error_code``) so the agent + frontend can
    branch on it without parsing the message text.
    """

    code: str = "CALIBRATION_DRIFT"
    error_code: str = "CALIBRATION_DRIFT"

    def __init__(
        self,
        message: str = "CALIBRATION_DRIFT",
        *,
        provider: str | None = None,
        backend: str | None = None,
        metric: str | None = None,
        observed: float | None = None,
        median_7d: float | None = None,
        sigma_7d: float | None = None,
        drift: float | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.backend = backend
        self.metric = metric
        self.observed = observed
        self.median_7d = median_7d
        self.sigma_7d = sigma_7d
        self.drift = drift


@dataclass(frozen=True)
class FoMaC:
    """Figures of Merit and Calibration sample (router-branch 6B).

    ``recorded_at`` defaults to "now" when the sample is stored.
    """

    two_q_error: float
    readout_error: float
    t1_us: float
    t2_us: float
    recorded_at: datetime | None = None


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
# Router gate: |latest - 7d median| / 7d median of two_q_error.
DRIFT_THRESHOLD = _DRIFT_SIGMA
_WINDOW_DAYS = 7
_V2_METRICS = ("two_q_error", "readout_error", "t1_us", "t2_us")


class CalibrationCache:
    """Postgres-backed per-day calibration cache + drift gate (P3-01)."""

    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine if engine is not None else engine_from_env()

    # ── Recording ────────────────────────────────────────────────

    def record(self, snap: CalibrationSnapshot) -> None:
        """Insert / update one day's snapshot."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO public.router_calibration_daily
                      (provider, backend, day, two_qubit_error,
                       readout_error, t1_t2_us, recorded_at)
                    VALUES (:provider, :backend, :day, :two_qubit_error,
                            :readout_error, :t1_t2_us, :recorded_at)
                    ON CONFLICT (provider, backend, day) DO UPDATE SET
                      two_qubit_error = excluded.two_qubit_error,
                      readout_error = excluded.readout_error,
                      t1_t2_us = excluded.t1_t2_us,
                      recorded_at = excluded.recorded_at
                    """,
                ),
                {
                    "provider": snap.provider,
                    "backend": snap.backend,
                    "day": snap.day,
                    "two_qubit_error": snap.two_qubit_error,
                    "readout_error": snap.readout_error,
                    "t1_t2_us": snap.t1_t2_us,
                    "recorded_at": _utcnow(),
                },
            )

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
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO public.router_calibration_devices
                      (provider, backend, recorded_at, two_q_error,
                       readout_error, t1_us, t2_us)
                    VALUES (:provider, :backend, :recorded_at, :two_q_error,
                            :readout_error, :t1_us, :t2_us)
                    ON CONFLICT (provider, backend, recorded_at) DO UPDATE SET
                      two_q_error = excluded.two_q_error,
                      readout_error = excluded.readout_error,
                      t1_us = excluded.t1_us,
                      t2_us = excluded.t2_us
                    """,
                ),
                {
                    "provider": snap.provider,
                    "backend": snap.backend,
                    "recorded_at": _as_utc(snap.recorded_at),
                    "two_q_error": snap.two_q_error,
                    "readout_error": snap.readout_error,
                    "t1_us": snap.t1_us,
                    "t2_us": snap.t2_us,
                },
            )

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
        anchor = _as_utc(anchor) if anchor else _utcnow()
        start = anchor - timedelta(days=window_days)
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT provider, backend, recorded_at, two_q_error,
                           readout_error, t1_us, t2_us
                    FROM public.router_calibration_devices
                    WHERE provider = :provider AND backend = :backend
                      AND recorded_at >= :start AND recorded_at < :anchor
                    ORDER BY recorded_at
                    """,
                ),
                {"provider": provider, "backend": backend, "start": start, "anchor": anchor},
            ).mappings().all()
        return [_row_to_device(row) for row in rows]

    def latest_device(
        self, provider: str, backend: str,
    ) -> DeviceCalibration | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT provider, backend, recorded_at, two_q_error,
                           readout_error, t1_us, t2_us
                    FROM public.router_calibration_devices
                    WHERE provider = :provider AND backend = :backend
                    ORDER BY recorded_at DESC LIMIT 1
                    """,
                ),
                {"provider": provider, "backend": backend},
            ).mappings().first()
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
        anchor = _as_utc(anchor) if anchor else _utcnow()
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
        anchor = _as_utc(anchor) if anchor else _utcnow()
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

    # ── Router-branch 6B API (FoMaC samples) ─────────────────────

    def update(self, provider: str, backend: str, fomac: FoMaC) -> None:
        """Store one FoMaC sample (``recorded_at`` defaults to now)."""
        self.record_device(DeviceCalibration(
            provider=provider,
            backend=backend,
            recorded_at=fomac.recorded_at or _utcnow(),
            two_q_error=fomac.two_q_error,
            readout_error=fomac.readout_error,
            t1_us=fomac.t1_us,
            t2_us=fomac.t2_us,
        ))

    def latest(self, provider: str, backend: str) -> FoMaC | None:
        """Most recent sample, with a timezone-aware UTC ``recorded_at``."""
        snap = self.latest_device(provider, backend)
        if snap is None:
            return None
        return FoMaC(
            two_q_error=snap.two_q_error,
            readout_error=snap.readout_error,
            t1_us=snap.t1_us,
            t2_us=snap.t2_us,
            recorded_at=snap.recorded_at,
        )

    def is_stale(
        self, provider: str, backend: str, max_age_h: int = 24,
    ) -> bool:
        """True iff no sample exists or the newest is older than ``max_age_h``."""
        snap = self.latest_device(provider, backend)
        if snap is None:
            return True
        return _utcnow() - snap.recorded_at > timedelta(hours=max_age_h)

    def has_history(self, provider: str, backend: str) -> bool:
        return self.latest_device(provider, backend) is not None

    def pull_qdmi(self, provider: str, backend: str) -> FoMaC | None:
        """Sample the device via QDMI when importable; None otherwise.

        QDMI is soft-imported so the cache works without ``extern/QDMI``
        being built. A successful pull is stored via :meth:`update`.
        """
        try:
            import qdmi  # type: ignore[import-not-found]
        except Exception:  # noqa: BLE001
            return None
        try:
            handle = qdmi.session().device(f"{provider}:{backend}")
            sample = FoMaC(
                two_q_error=float(handle.two_qubit_error()),
                readout_error=float(handle.readout_error()),
                t1_us=float(handle.t1_us()),
                t2_us=float(handle.t2_us()),
                recorded_at=_utcnow(),
            )
        except Exception:  # noqa: BLE001
            return None
        self.update(provider, backend, sample)
        return sample

    # ── Internal queries ─────────────────────────────────────────

    def _history(
        self, provider: str, backend: str, anchor: date, window: int,
    ) -> Iterable[CalibrationSnapshot]:
        start = anchor - timedelta(days=window)
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT provider, backend, day, two_qubit_error,
                           readout_error, t1_t2_us
                    FROM public.router_calibration_daily
                    WHERE provider = :provider AND backend = :backend
                      AND day >= :start AND day < :anchor
                    ORDER BY day
                    """,
                ),
                {"provider": provider, "backend": backend, "start": start, "anchor": anchor},
            ).mappings().all()
        for row in rows:
            yield _row_to_snapshot(row)

    def _snapshot(
        self, provider: str, backend: str, day: date,
    ) -> CalibrationSnapshot | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT provider, backend, day, two_qubit_error,
                           readout_error, t1_t2_us
                    FROM public.router_calibration_daily
                    WHERE provider = :provider AND backend = :backend AND day = :day
                    """,
                ),
                {"provider": provider, "backend": backend, "day": day},
            ).mappings().first()
        return _row_to_snapshot(row) if row is not None else None


def _stdev_from_median(values: list[float], med: float) -> float:
    """Median absolute deviation × 1.4826 (robust σ estimate)."""
    if not values:
        return 0.0
    deviations = sorted(abs(v - med) for v in values)
    mad = deviations[len(deviations) // 2]
    return mad * 1.4826


def _row_to_snapshot(row: Mapping[str, Any]) -> CalibrationSnapshot:
    return CalibrationSnapshot(
        provider=row["provider"],
        backend=row["backend"],
        day=row["day"],
        two_qubit_error=float(row["two_qubit_error"]),
        readout_error=float(row["readout_error"]),
        t1_t2_us=float(row["t1_t2_us"]),
    )


def _row_to_device(row: Mapping[str, Any]) -> DeviceCalibration:
    return DeviceCalibration(
        provider=row["provider"],
        backend=row["backend"],
        recorded_at=_as_utc(row["recorded_at"]),
        two_q_error=float(row["two_q_error"]),
        readout_error=float(row["readout_error"]),
        t1_us=float(row["t1_us"]),
        t2_us=float(row["t2_us"]),
    )


def assert_no_drift(
    cache: CalibrationCache,
    provider: str,
    backend: str,
    *,
    threshold: float = DRIFT_THRESHOLD,
) -> dict[str, Any]:
    """Router gate: raise :class:`CalibrationDrift` when the two-qubit
    error's relative drift (:meth:`CalibrationCache.drift_score`)
    exceeds ``threshold``; otherwise return the calibration metadata
    the router attaches to its decision.
    """
    drift = cache.drift_score(provider, backend)["two_q_error"]
    if drift > threshold:
        latest = cache.latest_device(provider, backend)
        raise CalibrationDrift(
            "CALIBRATION_DRIFT",
            provider=provider,
            backend=backend,
            metric="two_q_error",
            observed=latest.two_q_error if latest else None,
            drift=drift,
        )
    return {
        "provider": provider,
        "backend": backend,
        "drift_score": drift,
        "stale": cache.is_stale(provider, backend),
        "threshold": threshold,
    }


def _read_seed_text(filename: str) -> str | None:
    from importlib import resources

    ref = resources.files("qcompass_router.fixtures.calibration_seed").joinpath(
        filename,
    )
    if not ref.is_file():
        return None
    return ref.read_text()


def _csv_seed_rows(name: str, text: str) -> tuple[str, str, list[dict[str, Any]]]:
    import csv
    import io

    provider = name.split("_", 1)[0]
    rows = list(csv.DictReader(io.StringIO(text)))
    return provider, name, rows


def _yaml_seed_rows(name: str, text: str) -> tuple[str, str, list[dict[str, Any]]]:
    import yaml

    payload = yaml.safe_load(text) or {}
    provider = str(payload.get("provider") or "")
    backend = str(payload.get("backend") or "")
    if not provider or not backend:
        msg = (
            f"calibration seed {name!r} missing 'provider' or 'backend'."
        )
        raise ValueError(msg)
    return provider, backend, list(payload.get("snapshots") or [])


def load_calibration_seed(
    cache: CalibrationCache,
    name: str = "ibm_kingston",
) -> int:
    """Populate the v2 ``devices`` table from a bundled seed.

    Seeds live in ``qcompass_router/fixtures/calibration_seed/``:

    - ``<name>.yaml`` — ``provider`` / ``backend`` / ``snapshots``
      (schema below);
    - ``<name>.csv`` — the router-branch CSV seeds (``ibm_torino``,
      ``ionq_forte``, ``iqm_garnet``) with header
      ``recorded_at,two_q_error,readout_error,t1_us,t2_us``; the
      provider is the file stem up to the first ``_`` and the backend
      is the stem.

    ``name`` may carry the extension to pick a format; without one the
    YAML seed wins and the CSV seed is the fallback. Inserts each
    snapshot via :meth:`CalibrationCache.record_device` and returns the
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
    stem, dot, ext = name.partition(".")
    candidates = [ext] if dot else ["yaml", "csv"]
    for fmt in candidates:
        text = _read_seed_text(f"{stem}.{fmt}")
        if text is None:
            continue
        reader = _csv_seed_rows if fmt == "csv" else _yaml_seed_rows
        provider, backend, rows = reader(stem, text)
        break
    else:
        msg = f"no calibration seed named {name!r}"
        raise FileNotFoundError(msg)
    inserted = 0
    for snap in rows:
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
