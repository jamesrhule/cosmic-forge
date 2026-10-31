"""budget=0, require_real_hardware=False → local_aer."""

from __future__ import annotations

from qcompass_router.decision import BackendRequest
from qcompass_router.router import Router


def test_zero_budget_routes_to_local_aer(small_qasm, fake_adapter_factory):
    aer = fake_adapter_factory("local_aer", kind="local", cost=0.0)
    lightning = fake_adapter_factory("local_lightning", kind="local", cost=0.0)
    ibm = fake_adapter_factory("ibm", kind="cloud-sc", cost=10.0)
    router = Router(providers=[aer, lightning, ibm])

    decision = router.decide(
        BackendRequest(circuit_qasm=small_qasm, shots=1024, budget_usd=0.0)
    )

    assert decision.provider == "local_aer"
    assert decision.cost_estimate_usd == 0.0
    assert decision.queue_time_s_estimate == 0.0
    assert decision.fidelity_estimate == 1.0


def test_zero_budget_large_circuit_prefers_lightning(large_qasm, fake_adapter_factory):
    aer = fake_adapter_factory("local_aer", kind="local")
    lightning = fake_adapter_factory("local_lightning", kind="local")
    router = Router(providers=[aer, lightning])

    decision = router.decide(
        BackendRequest(circuit_qasm=large_qasm, shots=1024, budget_usd=0.0)
    )

    assert decision.provider == "local_lightning"


def test_zero_budget_falls_back_to_aer_when_lightning_missing(
    large_qasm, fake_adapter_factory
):
    aer = fake_adapter_factory("local_aer", kind="local")
    router = Router(providers=[aer])

    decision = router.decide(
        BackendRequest(circuit_qasm=large_qasm, shots=1024, budget_usd=0.0)
    )

    assert decision.provider == "local_aer"
