"""A-router-4: every RoutingDecision carries cost, queue, fidelity, all non-None.

Asserts the contract on the public fields the rest of the system depends on.
"""

from __future__ import annotations

from qcompass_router.decision import BackendRequest
from qcompass_router.router import Router

from tests.conftest import FakeAdapter

SMALL_QASM = (
    'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\n'
    "h q[0];\nmeasure q -> c;\n"
)


def test_decision_fields_non_none_zero_budget() -> None:
    aer = FakeAdapter("local_aer", kind="local")
    router = Router(providers=[aer])
    decision = router.decide(
        BackendRequest(circuit_qasm=SMALL_QASM, shots=1024, budget_usd=0.0)
    )
    assert decision.provider is not None
    assert decision.backend is not None
    assert decision.cost_estimate_usd is not None
    assert decision.queue_time_s_estimate is not None
    assert decision.fidelity_estimate is not None
    assert decision.transforms_applied is not None
    assert decision.transform_records is not None
    assert decision.reason is not None


def test_decision_fields_non_none_paid() -> None:
    ibm = FakeAdapter(
        "ibm",
        kind="cloud-sc",
        backends=["ibm_heron"],
        per_backend_cost={"ibm_heron": 5.0},
    )
    router = Router(providers=[ibm])
    decision = router.decide(
        BackendRequest(
            circuit_qasm=SMALL_QASM,
            shots=1024,
            budget_usd=50.0,
            min_fidelity=0.95,
        )
    )
    assert decision.provider == "ibm"
    assert decision.backend == "ibm_heron"
    assert decision.cost_estimate_usd is not None
    assert decision.queue_time_s_estimate is not None
    assert decision.fidelity_estimate is not None
