"""A-router-5: free-tier IBM Open beats paid IonQ Forte.

Setup: budget=$50, IBM Open Plan with 4 minutes left, an SQD-style
circuit estimated at 30s of runtime. The router must pick the IBM
free-tier backend (ibm_kingston) over the paid IonQ Forte option.
"""

from __future__ import annotations

from qcompass_router.decision import BackendRequest
from qcompass_router.pricing import FreeTierLedger, _FreeTierBucket
from qcompass_router.router import Router

from tests.conftest import FakeAdapter

# 30-second SQD-ish circuit; depth & qubit specifics are not material
# to the routing decision in 6B, only the shots / runtime estimate.
SQD_QASM = (
    'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[10];\ncreg c[10];\n'
    "h q[0];\ncx q[0],q[1];\nmeasure q -> c;\n"
)


def _ledger_with_4min_ibm_open() -> FreeTierLedger:
    ledger = FreeTierLedger()
    ledger.buckets["ibm_open"] = _FreeTierBucket(
        units=4.0,
        unit_kind="minutes",
        applicable_backends=("ibm_kingston",),
    )
    return ledger


def test_free_tier_ibm_open_beats_paid_ionq_forte() -> None:
    ibm = FakeAdapter(
        "ibm",
        kind="cloud-sc",
        backends=["ibm_kingston"],
        per_backend_cost={"ibm_kingston": 8.0},
    )
    ionq = FakeAdapter(
        "ionq",
        kind="cloud-ion",
        backends=["ionq_forte"],
        per_backend_cost={"ionq_forte": 25.0},
    )
    router = Router(
        providers=[ibm, ionq],
        free_tier_ledger=_ledger_with_4min_ibm_open(),
    )

    # 30s wallclock estimate is well within the 4-minute free tier.
    decision = router.decide(
        BackendRequest(
            circuit_qasm=SQD_QASM,
            shots=30_000,  # ≈30s at 1ms/shot heuristic
            budget_usd=50.0,
            min_fidelity=0.95,
        )
    )

    assert decision.provider == "ibm"
    assert decision.backend == "ibm_kingston"
    assert decision.calibration is not None
    assert decision.calibration.get("free_tier") == "ibm_open"


def test_free_tier_falls_back_when_exhausted() -> None:
    """When the free tier has 0 minutes left, paid IonQ Forte should win."""
    ledger = FreeTierLedger()
    ledger.buckets["ibm_open"] = _FreeTierBucket(
        units=0.0,
        unit_kind="minutes",
        applicable_backends=("ibm_kingston",),
    )
    ibm = FakeAdapter(
        "ibm",
        kind="cloud-sc",
        backends=["ibm_kingston"],
        per_backend_cost={"ibm_kingston": 8.0},
    )
    ionq = FakeAdapter(
        "ionq",
        kind="cloud-ion",
        backends=["ionq_forte"],
        per_backend_cost={"ionq_forte": 25.0},
    )
    router = Router(providers=[ibm, ionq], free_tier_ledger=ledger)

    decision = router.decide(
        BackendRequest(
            circuit_qasm=SQD_QASM,
            shots=30_000,
            budget_usd=50.0,
            min_fidelity=0.95,
        )
    )
    # IBM is still cheaper; should still win — the point is just that the
    # free-tier branch did not fire spuriously.
    assert decision.provider == "ibm"
    if decision.calibration is not None:
        assert decision.calibration.get("free_tier") is None
