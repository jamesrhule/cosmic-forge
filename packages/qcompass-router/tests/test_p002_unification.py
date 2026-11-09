"""P0-02 router unification: capabilities ported from the router branch
(6B) into the agent-lineage router, plus the 6A compatibility surface.

Offline only: live pricing is exercised through an injected stub client
(R8 — no test calls a provider).
"""

from __future__ import annotations

import importlib.util
import ssl
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from qcompass_router import pricing_stub, ssl_pin
from qcompass_router.budget import BudgetExceeded
from qcompass_router.calibration import (
    CalibrationCache,
    CalibrationDrift,
    FoMaC,
    load_calibration_seed,
)
from qcompass_router.decision import RouterRequest
from qcompass_router.pricing import FreeTierLedger, PricingEngine, _FreeTierBucket
from qcompass_router.providers import (
    AzureAdapter,
    AzureQuantumAdapter,
    IBMAdapter,
    IBMRuntimeAdapter,
    IonQAdapter,
    IonQNativeAdapter,
    QueRaAdapter,
    QueraAdapter,
)
from qcompass_router.providers.base import BackendInfo, JobHandle
from qcompass_router.router import DEFAULT_AUTO_TRANSFORMS, Router
from qcompass_router.transforms import apply_transforms
from tests.conftest import FakeAdapter

if TYPE_CHECKING:
    from sqlalchemy import Engine

PKG_ROOT = Path(__file__).resolve().parents[1]

SMALL_QASM = (
    'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\n'
    "h q[0];\ncx q[0],q[1];\nmeasure q -> c;\n"
)


def _deep_qasm(gates: int) -> str:
    body = "\n".join("cx q[0],q[1];" for _ in range(gates))
    return f'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\n{body}\n'


def _fomac(two_q: float, recorded_at: datetime | None = None) -> FoMaC:
    return FoMaC(
        two_q_error=two_q, readout_error=0.02, t1_us=200.0, t2_us=150.0,
        recorded_at=recorded_at,
    )


# ── One pricing seed ────────────────────────────────────────────────


def test_single_pricing_seed_carries_free_tiers_and_depth_caps() -> None:
    assert not (PKG_ROOT / "fixtures" / "pricing_seed.yaml").exists()
    pricing_stub.reload()
    tiers = pricing_stub.free_tiers()
    assert set(tiers) == {"ibm_open", "iqm_starter", "aws_braket", "azure_credit"}
    caps = pricing_stub.device_typical_depth_max()
    assert caps["ibm_heron"] == 200
    assert caps["local_aer"] == 1_000_000
    ledger = FreeTierLedger.from_seed()
    assert ledger.buckets["ibm_open"].unit_kind == "minutes"
    assert ledger.buckets["iqm_starter"].unit_kind == "credits"
    assert ledger.buckets["aws_braket"].unit_kind == "hours"
    assert ledger.buckets["azure_credit"].unit_kind == "usd"
    # Every seed entry flagged free-tier is listed by a ledger tier, so
    # the ledger is the authority for every shipped backend.
    for entry in pricing_stub.list_entries():
        if entry.is_free_tier:
            assert ledger.lists(entry.backend), entry.key


def test_pricing_stub_lookup_fallbacks() -> None:
    # 6A keys: "<provider>_<backend>" and provider-only for an unpinned backend.
    assert pricing_stub.lookup("braket", "ionq_aria").key == "braket_ionq_aria"
    assert pricing_stub.lookup("local_aer", "").key == "local_aer"
    assert pricing_stub.lookup("ibm", "").provider == "ibm"
    # A backend key never borrows another provider's price.
    assert pricing_stub.lookup("ionq", "local_aer") is None
    assert pricing_stub.lookup("ibm", "fictional") is None


def test_estimate_entry_covers_azure_shapes() -> None:
    hqc, breakdown = pricing_stub.estimate_entry(
        {"hqc_per_circuit": 5, "hqc_overage_usd": 13.5}, 100,
    )
    assert hqc == pytest.approx(67.5)
    assert breakdown == {"per_circuit": pytest.approx(67.5)}
    floored, breakdown = pricing_stub.estimate_entry(
        {"per_1q_shot_usd": 0.00022, "min_program_usd": 1.0}, 100,
    )
    assert floored == 1.0
    assert "min_program_floor" in breakdown


# ── 6A compatibility surface ────────────────────────────────────────


def test_6a_adapter_aliases_are_the_same_classes() -> None:
    assert AzureQuantumAdapter is AzureAdapter
    assert IBMRuntimeAdapter is IBMAdapter
    assert IonQNativeAdapter is IonQAdapter
    assert QueRaAdapter is QueraAdapter


def test_backend_info_priors_and_job_handle_default() -> None:
    info = BackendInfo(provider="x", name="b").with_priors("cloud-ion")
    assert info.kind == "cloud-ion"
    assert info.fidelity_estimate == 0.99
    assert info.queue_time_s_estimate == 900.0
    explicit = BackendInfo(
        provider="x", name="b", kind="cloud-sc",
        fidelity_estimate=0.5, queue_time_s_estimate=1.0,
    ).with_priors("cloud-ion")
    assert (explicit.kind, explicit.fidelity_estimate) == ("cloud-sc", 0.5)
    handle = JobHandle(provider="x", backend="b", job_id="j")
    assert datetime.fromisoformat(handle.submitted_at).tzinfo is not None


def test_6a_adapter_backends_are_router_candidates() -> None:
    adapter = FakeAdapter("ionq", kind="cloud-ion", backends=["ionq_aria"])
    infos = adapter.list_backend_infos()
    assert [i.name for i in infos] == ["ionq_aria"]
    assert infos[0].fidelity_estimate is None  # filled by the router


# ── Free tiers ──────────────────────────────────────────────────────


def _ibm_open_ledger(minutes: float) -> FreeTierLedger:
    ledger = FreeTierLedger()
    ledger.buckets["ibm_open"] = _FreeTierBucket(
        units=minutes, unit_kind="minutes", applicable_backends=("ibm_kingston",),
    )
    return ledger


def test_zero_budget_real_hardware_uses_covering_free_tier() -> None:
    ibm = FakeAdapter("ibm", kind="cloud-sc", backends=["ibm_kingston"], cost=8.0)
    router = Router(providers=[ibm], free_tier_ledger=_ibm_open_ledger(4.0))
    decision = router.decide(RouterRequest(
        circuit_qasm=SMALL_QASM, shots=1024, budget_usd=0.0,
        require_real_hardware=True,
    ))
    assert (decision.provider, decision.backend) == ("ibm", "ibm_kingston")
    assert decision.cost_estimate_usd == 0.0
    assert decision.calibration is not None
    assert decision.calibration["free_tier"] == "ibm_open"


def test_zero_budget_real_hardware_refused_when_tier_exhausted() -> None:
    ibm = FakeAdapter("ibm", kind="cloud-sc", backends=["ibm_kingston"])
    router = Router(providers=[ibm], free_tier_ledger=_ibm_open_ledger(0.0))
    with pytest.raises(BudgetExceeded) as exc:
        router.decide(RouterRequest(
            circuit_qasm=SMALL_QASM, shots=1024, budget_usd=0.0,
            require_real_hardware=True,
        ))
    assert exc.value.code == "BUDGET_EXCEEDED"
    assert "require_real_hardware" in str(exc.value)


def test_free_tier_beats_cheaper_paid_backend() -> None:
    ibm = FakeAdapter(
        "ibm", kind="cloud-sc", backends=["ibm_kingston"],
        per_backend_cost={"ibm_kingston": 20.0},
    )
    ionq = FakeAdapter(
        "ionq", kind="cloud-ion", backends=["ionq_forte"],
        per_backend_cost={"ionq_forte": 5.0},
    )
    req = RouterRequest(circuit_qasm=SMALL_QASM, shots=1024, budget_usd=50.0)
    covered = Router(providers=[ibm, ionq], free_tier_ledger=_ibm_open_ledger(4.0))
    assert covered.decide(req).backend == "ibm_kingston"
    exhausted = Router(providers=[ibm, ionq], free_tier_ledger=_ibm_open_ledger(0.0))
    decision = exhausted.decide(req)
    assert decision.backend == "ionq_forte"
    assert decision.calibration is None


# ── Auto transforms ─────────────────────────────────────────────────


def _local_router(**kwargs) -> Router:  # type: ignore[no-untyped-def]
    return Router(providers=[FakeAdapter("local_aer", kind="local")], **kwargs)


def test_auto_transforms_fire_above_device_depth_cap() -> None:
    threshold = min(
        v for k, v in pricing_stub.device_typical_depth_max().items()
        if k not in ("local_aer", "local_lightning")
    )
    deep = _deep_qasm(threshold + 1)
    decision = _local_router().decide(RouterRequest(circuit_qasm=deep, budget_usd=0.0))
    assert [r.name for r in decision.transforms_applied] == list(DEFAULT_AUTO_TRANSFORMS)
    assert decision.transforms_applied[0].depth_before == threshold + 1

    at_cap = _local_router().decide(
        RouterRequest(circuit_qasm=_deep_qasm(threshold), budget_usd=0.0),
    )
    assert at_cap.transforms_applied == []


def test_explicit_transforms_override_and_auto_can_be_disabled() -> None:
    deep = _deep_qasm(500)
    explicit = _local_router().decide(
        RouterRequest(circuit_qasm=deep, budget_usd=0.0), transforms=["mpf"],
    )
    assert [r.name for r in explicit.transforms_applied] == ["mpf"]
    disabled = _local_router(auto_transforms=()).decide(
        RouterRequest(circuit_qasm=deep, budget_usd=0.0),
    )
    assert disabled.transforms_applied == []


def test_transform_records_measure_depth_and_runtime() -> None:
    _, records = apply_transforms(SMALL_QASM, ["cutting", "obp"])
    assert [r.name for r in records] == ["cutting", "obp"]
    for record in records:
        assert record.depth_before == 3  # h, cx, measure
        assert record.runtime_ms >= 0.0
        module = {"cutting": "qiskit_addon_cutting", "obp": "qiskit_addon_obp"}[record.name]
        if importlib.util.find_spec(module) is None:
            assert record.notes == "SDK absent — pass-through."
            assert record.depth_after == record.depth_before


# ── Calibration: stale downgrade, drift gate, CSV seeds ─────────────


def test_stale_candidate_downgraded_when_fresh_alternative_exists(pg_engine: Engine) -> None:
    cache = CalibrationCache(pg_engine)
    cheap = FakeAdapter("cheapq", kind="cloud-ion", backends=["cheap_be"], cost=1.0)
    fresh = FakeAdapter("ionq", kind="cloud-ion", backends=["fresh_be"], cost=10.0)
    cache.update("cheapq", "cheap_be", _fomac(0.01, datetime.now(UTC) - timedelta(days=3)))
    cache.update("ionq", "fresh_be", _fomac(0.01))
    req = RouterRequest(circuit_qasm=SMALL_QASM, shots=1024, budget_usd=50.0)

    decision = Router(providers=[cheap, fresh], calibration=cache).decide(req)
    assert decision.backend == "fresh_be"
    assert decision.calibration is not None
    assert decision.calibration["stale"] is False

    # Without calibration the cheaper backend wins.
    assert Router(providers=[cheap, fresh]).decide(req).backend == "cheap_be"


def test_all_stale_keeps_cost_order(pg_engine: Engine) -> None:
    cache = CalibrationCache(pg_engine)
    cheap = FakeAdapter("cheapq", kind="cloud-ion", backends=["cheap_be"], cost=1.0)
    pricey = FakeAdapter("ionq", kind="cloud-ion", backends=["pricey_be"], cost=10.0)
    decision = Router(providers=[cheap, pricey], calibration=cache).decide(
        RouterRequest(circuit_qasm=SMALL_QASM, shots=1024, budget_usd=50.0),
    )
    assert decision.backend == "cheap_be"
    assert decision.calibration is not None
    assert decision.calibration["stale"] is True


def test_drift_gate_applies_to_the_chosen_backend_only(pg_engine: Engine) -> None:
    cache = CalibrationCache(pg_engine)
    base = datetime.now(UTC) - timedelta(days=6)
    for i in range(7):
        cache.update("ionq", "pricey_be", _fomac(0.01, base + timedelta(days=i)))
    cache.update("ionq", "pricey_be", _fomac(0.05))  # 4x drift
    cache.update("cheapq", "cheap_be", _fomac(0.01))
    cheap = FakeAdapter("cheapq", kind="cloud-ion", backends=["cheap_be"], cost=1.0)
    pricey = FakeAdapter("ionq", kind="cloud-ion", backends=["pricey_be"], cost=10.0)
    req = RouterRequest(circuit_qasm=SMALL_QASM, shots=1024, budget_usd=50.0)
    assert Router(providers=[cheap, pricey], calibration=cache).decide(req).backend == "cheap_be"
    with pytest.raises(CalibrationDrift):
        Router(providers=[pricey], calibration=cache).decide(req)


@pytest.mark.parametrize(
    ("name", "provider", "backend"),
    [
        ("ibm_torino", "ibm", "ibm_torino"),
        ("iqm_garnet", "iqm", "iqm_garnet"),
        ("ionq_forte.csv", "ionq", "ionq_forte"),
    ],
)
def test_csv_calibration_seeds_load(pg_engine: Engine, name: str, provider: str, backend: str) -> None:
    cache = CalibrationCache(pg_engine)
    assert load_calibration_seed(cache, name) == 7
    latest = cache.latest(provider, backend)
    assert latest is not None
    assert latest.recorded_at == datetime(2026, 4, 24, tzinfo=UTC)
    assert cache.has_history(provider, backend)


def test_yaml_seed_wins_without_extension(pg_engine: Engine) -> None:
    cache = CalibrationCache(pg_engine)
    load_calibration_seed(cache, "ionq_forte")
    assert cache.has_history("braket", "ionq_forte_1")
    assert not cache.has_history("ionq", "ionq_forte")
    with pytest.raises(FileNotFoundError):
        load_calibration_seed(cache, "no_such_device")


def test_pull_qdmi_without_qdmi_is_none(pg_engine: Engine) -> None:
    if importlib.util.find_spec("qdmi") is not None:
        pytest.skip("qdmi installed; the soft-import path is not reachable")
    cache = CalibrationCache(pg_engine)
    assert cache.pull_qdmi("ibm", "ibm_torino") is None
    assert not cache.has_history("ibm", "ibm_torino")


# ── Live pricing (stubbed client only) ──────────────────────────────


def _client_returning(status: int, body: dict) -> MagicMock:  # type: ignore[type-arg]
    resp = MagicMock()
    resp.status_code = status
    resp.content = b"{}"
    resp.json = lambda: body
    client = MagicMock()
    client.get = MagicMock(return_value=resp)
    return client


def test_live_refresh_overrides_seed_rates(tmp_path: Path) -> None:
    engine = PricingEngine(
        cache_dir=tmp_path / "cache",
        client_factory=lambda: _client_returning(200, {"per_second_usd": 3.2}),
    )
    engine.refresh_live(["ibm"])
    cost = engine.estimate("ibm", "ibm_kingston", None, 1024)
    assert cost.live is True
    assert cost.source == "live"
    assert cost.usd == pytest.approx(3.2)
    assert cost.pricing_basis == "per_second"
    assert cost.cache_age_s >= 0


def test_live_refresh_non_2xx_writes_nothing(tmp_path: Path) -> None:
    engine = PricingEngine(
        cache_dir=tmp_path / "cache",
        client_factory=lambda: _client_returning(503, {}),
    )
    engine.refresh_live(["ibm", "braket"])
    assert list((tmp_path / "cache").glob("*.json")) == []
    assert engine.estimate("ibm", "ibm_kingston", None, 1024).source == "seed"


def test_refresh_without_opt_in_stays_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QCOMPASS_PRICING_LIVE", raising=False)
    engine = PricingEngine(cache_dir=tmp_path / "cache")
    engine._client = MagicMock(side_effect=AssertionError("network used"))  # type: ignore[method-assign]
    engine.refresh_live(["ibm"])
    cost = engine.estimate("ibm", "ibm_kingston", None, 1024)
    assert cost.source == "cache"
    assert cost.live is False


def test_router_reports_live_pricing(tmp_path: Path) -> None:
    class _IBM(IBMAdapter):
        def is_available(self) -> bool:  # type: ignore[override]
            return True

    engine = PricingEngine(
        cache_dir=tmp_path / "cache",
        client_factory=lambda: _client_returning(200, {"per_second_usd": 1.0}),
    )
    engine.refresh_live(["ibm"])
    decision = Router(providers=[_IBM()], pricing=engine).decide(RouterRequest(
        circuit_qasm=SMALL_QASM, shots=1024, budget_usd=50.0, min_fidelity=0.95,
    ))
    assert decision.provider == "ibm"
    assert decision.calibration is not None
    assert decision.calibration["free_tier"] == "ibm_open"
    assert decision.calibration["live_pricing"] is True


def test_ssl_pin_context_pins_given_bundle() -> None:
    certifi = pytest.importorskip("certifi")
    ctx = ssl_pin.pinned_context(certifi.where())
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True
    with pytest.raises(ValueError):
        ssl_pin.pinned_context(False)
