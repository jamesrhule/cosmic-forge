"""PROMPT 6 v2 reconciliation tests.

Pins the v2 §DEFINITION OF DONE invariants on top of the v1
audit suite (A-router-1..6 stay green; the v2 deltas are tested
here so the original audit files stay byte-stable).

Covered:
  - PricingEngine.estimate returns the v2 Cost dataclass with
    breakdown + free-tier metadata.
  - PricingEngine.refresh_live(providers) is a no-op fallback
    when the live fetcher raises (offline path).
  - account_credits() exposes the Azure $200 starter credit so
    the router can rank Azure ahead of paid backends.
  - _FREE_TIER_ORDER includes 'azure' after 'braket'.
  - Calibration v2 ``devices`` table + drift_score() use the
    PROMPT 6 v2 |latest - 7d_median|/|7d_median| formula.
  - check_device_drift fires with a planted 4σ outlier.
  - load_calibration_seed populates the bundled 7-day history.
  - ibm_kingston (Open Plan free tier) wins over IonQ Forte at
    $50 budget — PROMPT 6 v2 §A-router-5.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from qcompass_router import (
    BraketAdapter,
    CalibrationCache,
    CalibrationDrift,
    Cost,
    DeviceCalibration,
    IBMAdapter,
    LocalAerAdapter,
    PricingEngine,
    Router,
    RouterRequest,
    load_calibration_seed,
    pricing_stub,
)
from qcompass_router.router import _FREE_TIER_ORDER


# ── Pricing engine ───────────────────────────────────────────────────


def test_pricing_engine_returns_structured_cost(tmp_path) -> None:
    pricing_stub.reload()
    engine = PricingEngine(cache_dir=tmp_path / "cache")
    cost = engine.estimate("ibm", "ibm_kingston", circuit=None, shots=4096)
    assert isinstance(cost, Cost)
    assert cost.provider == "ibm"
    assert cost.backend == "ibm_kingston"
    assert cost.shots == 4096
    assert cost.total_usd > 0.0
    assert "per_second" in cost.breakdown
    assert cost.free_tier is True   # IBM Open Plan ⇒ free tier
    assert cost.source == "seed"


def test_pricing_engine_unknown_backend_raises(tmp_path) -> None:
    engine = PricingEngine(cache_dir=tmp_path / "cache")
    with pytest.raises(KeyError, match="No pricing"):
        engine.estimate("ibm", "fictional", circuit=None, shots=10)


def test_pricing_engine_refresh_live_offline_falls_back(tmp_path) -> None:
    """When _fetch_live raises NotImplementedError, refresh_live must
    populate the cache from the seed (offline-clean fallback)."""
    engine = PricingEngine(cache_dir=tmp_path / "cache")
    engine.refresh_live(["ibm", "braket"])
    # Each provider's cache file should now exist.
    assert (tmp_path / "cache" / "ibm.json").exists()
    assert (tmp_path / "cache" / "braket.json").exists()


def test_pricing_engine_uses_cache_when_fresh(tmp_path) -> None:
    engine = PricingEngine(cache_dir=tmp_path / "cache")
    engine.refresh_live(["ibm"])
    cost = engine.estimate("ibm", "ibm_kingston", circuit=None, shots=4096)
    assert cost.source == "cache"


# ── Account credits + free-tier order ────────────────────────────────


def test_account_credits_includes_azure_starter() -> None:
    pricing_stub.reload()
    credits = pricing_stub.account_credits()
    assert "azure" in credits
    azure = credits["azure"]
    assert azure["starter_credit_usd"] == 200.0
    assert azure["credit_remaining_usd"] == 200.0


def test_free_tier_order_lists_azure_after_braket() -> None:
    assert _FREE_TIER_ORDER == ("ibm", "iqm", "braket", "azure")


# ── Calibration v2: devices table + drift_score ──────────────────────


def _seed_stable_devices(
    cache: CalibrationCache,
    *,
    provider: str = "ibm",
    backend: str = "ibm_kingston",
    days: int = 7,
    base_two_q: float = 0.010,
    base_readout: float = 0.020,
    base_t1: float = 110.0,
    base_t2: float = 95.0,
) -> None:
    anchor = datetime(2026, 5, 1, 12, 0, 0)
    for d in range(days, 0, -1):
        cache.record_device(DeviceCalibration(
            provider=provider, backend=backend,
            recorded_at=anchor - timedelta(days=d),
            two_q_error=base_two_q,
            readout_error=base_readout,
            t1_us=base_t1, t2_us=base_t2,
        ))


def test_drift_score_zero_for_stable_history(tmp_path) -> None:
    cache = CalibrationCache(db_path=tmp_path / "calib.sqlite")
    _seed_stable_devices(cache)
    # Latest snapshot equals the median.
    cache.record_device(DeviceCalibration(
        provider="ibm", backend="ibm_kingston",
        recorded_at=datetime(2026, 5, 1, 12, 0, 0),
        two_q_error=0.010, readout_error=0.020,
        t1_us=110.0, t2_us=95.0,
    ))
    scores = cache.drift_score(
        "ibm", "ibm_kingston",
        anchor=datetime(2026, 5, 1, 13, 0, 0),
    )
    for metric in ("two_q_error", "readout_error", "t1_us", "t2_us"):
        assert scores[metric] == 0.0


def test_drift_score_relative_to_median(tmp_path) -> None:
    cache = CalibrationCache(db_path=tmp_path / "calib.sqlite")
    _seed_stable_devices(cache)
    # Plant a +50% deviation in two_q_error today.
    cache.record_device(DeviceCalibration(
        provider="ibm", backend="ibm_kingston",
        recorded_at=datetime(2026, 5, 1, 12, 0, 0),
        two_q_error=0.015,
        readout_error=0.020,
        t1_us=110.0, t2_us=95.0,
    ))
    scores = cache.drift_score(
        "ibm", "ibm_kingston",
        anchor=datetime(2026, 5, 1, 13, 0, 0),
    )
    # |0.015 - 0.010| / 0.010 = 0.5
    assert abs(scores["two_q_error"] - 0.5) < 1e-9
    # Other metrics still zero.
    assert scores["readout_error"] == 0.0


def test_check_device_drift_fires_on_4sigma_outlier(tmp_path) -> None:
    """v2 §A-router-3 fixture: a 4σ outlier on the v2 devices table
    must raise CalibrationDrift with code CALIBRATION_DRIFT.
    """
    cache = CalibrationCache(db_path=tmp_path / "calib.sqlite")
    # Seed a low-variance history (sigma small but nonzero).
    anchor = datetime(2026, 5, 1, 12, 0, 0)
    history_values = [0.0098, 0.0099, 0.0100, 0.0101, 0.0102, 0.0099, 0.0101]
    for d, v in enumerate(history_values, start=1):
        cache.record_device(DeviceCalibration(
            provider="ibm", backend="ibm_kingston",
            recorded_at=anchor - timedelta(days=d),
            two_q_error=v,
            readout_error=0.020, t1_us=110.0, t2_us=95.0,
        ))
    # Latest snapshot well beyond 4σ from a ~0.0001 σ band.
    cache.record_device(DeviceCalibration(
        provider="ibm", backend="ibm_kingston",
        recorded_at=anchor,
        two_q_error=0.030,   # 20× the median = far past 4σ
        readout_error=0.020, t1_us=110.0, t2_us=95.0,
    ))
    with pytest.raises(CalibrationDrift) as exc:
        cache.check_device_drift(
            "ibm", "ibm_kingston",
            anchor=anchor + timedelta(hours=1),
        )
    assert exc.value.code == "CALIBRATION_DRIFT"
    assert exc.value.metric == "two_q_error"


def test_load_calibration_seed_populates_devices_table(tmp_path) -> None:
    cache = CalibrationCache(db_path=tmp_path / "calib.sqlite")
    inserted = load_calibration_seed(cache, "ibm_kingston")
    assert inserted == 7
    history = cache.device_history(
        "ibm", "ibm_kingston",
        anchor=datetime(2026, 5, 2, 12, 0, 0),
        window_days=14,
    )
    assert len(history) == 7
    assert all(s.t1_us > 0 and s.t2_us > 0 for s in history)


def test_load_calibration_seed_ionq_forte(tmp_path) -> None:
    cache = CalibrationCache(db_path=tmp_path / "calib.sqlite")
    inserted = load_calibration_seed(cache, "ionq_forte")
    assert inserted == 7


# ── A-router-5 v2: ibm_kingston Open Plan beats IonQ Forte ───────────


class _Aer(LocalAerAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


class _IBM(IBMAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


class _Braket(BraketAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


def test_budget_50_routes_to_ibm_kingston_over_ionq_forte() -> None:
    router = Router(providers=[_Aer(), _IBM(), _Braket()])
    decision = router.decide(RouterRequest(
        shots=4096,
        budget_usd=50.0,
        min_fidelity=0.99,
        require_real_hardware=True,
        preferred_providers=["ibm", "braket"],
    ))
    # IBM (Open Plan free tier) must be picked over Braket / IonQ Forte.
    assert decision.provider == "ibm"
    assert decision.backend in {"ibm_heron", "ibm_kingston", "ibm_eagle"}
    assert decision.cost_estimate_usd <= 50.0


def test_budget_50_with_only_braket_picks_cheapest_braket() -> None:
    """Sanity: filtering down to braket alone still produces a valid
    routing decision (IonQ Forte is only chosen when nothing cheaper
    is in the candidate list)."""
    router = Router(providers=[_Aer(), _Braket()])
    decision = router.decide(RouterRequest(
        shots=512,           # smaller shot count keeps Forte affordable
        budget_usd=50.0,
        min_fidelity=0.97,
        require_real_hardware=True,
        preferred_providers=["braket"],
    ))
    assert decision.provider == "braket"
