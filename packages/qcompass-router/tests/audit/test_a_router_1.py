"""A-router-1: budget=0 always routes to local_aer; never to cloud.

Carry-over from PROMPT 6A; re-asserted under the Phase-6B router so we
catch regressions in the upgraded `decide()` pipeline.
"""

from __future__ import annotations

from qcompass_router.decision import BackendRequest
from qcompass_router.router import Router

from tests.conftest import FakeAdapter

SMALL_QASM = (
    'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\n'
    "h q[0];\ncx q[0],q[1];\nmeasure q -> c;\n"
)


def test_zero_budget_never_routes_to_cloud() -> None:
    aer = FakeAdapter("local_aer", kind="local")
    lightning = FakeAdapter("local_lightning", kind="local")
    ibm = FakeAdapter("ibm", kind="cloud-sc", cost=0.0)
    ionq = FakeAdapter("ionq", kind="cloud-ion", cost=0.0)
    router = Router(providers=[ibm, ionq, aer, lightning])

    decision = router.decide(
        BackendRequest(circuit_qasm=SMALL_QASM, shots=1024, budget_usd=0.0)
    )

    assert decision.provider in {"local_aer", "local_lightning"}
    assert decision.cost_estimate_usd == 0.0
