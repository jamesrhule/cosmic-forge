"""Paid request picks the cheapest viable backend.

With Heron < Forte under mocked stub pricing, budget=$50 selects Heron.
"""

from __future__ import annotations

from qcompass_router.decision import BackendRequest
from qcompass_router.router import Router


def test_paid_request_picks_cheapest(small_qasm, fake_adapter_factory):
    # Two cloud-sc adapters; one with a "Heron" backend cheaper than the
    # IonQ Forte alternative on a separate cloud-ion adapter.
    ibm = fake_adapter_factory(
        "ibm",
        kind="cloud-sc",
        backends=["ibm_heron"],
        per_backend_cost={"ibm_heron": 5.0},
    )
    ionq = fake_adapter_factory(
        "ionq",
        kind="cloud-ion",
        backends=["ionq_forte"],
        per_backend_cost={"ionq_forte": 25.0},
    )
    router = Router(providers=[ibm, ionq])

    decision = router.decide(
        BackendRequest(
            circuit_qasm=small_qasm,
            shots=1024,
            budget_usd=50.0,
            min_fidelity=0.95,
        )
    )

    assert decision.provider == "ibm"
    assert decision.backend == "ibm_heron"
    assert decision.cost_estimate_usd == 5.0


def test_paid_request_respects_min_fidelity(small_qasm, fake_adapter_factory):
    """A cheap adapter below the fidelity floor must be skipped."""
    # Custom adapter whose `kind` maps to a low fidelity prior.
    cheap_low_fid = fake_adapter_factory(
        "cheapo",
        kind="cloud-other",
        backends=["cheap_be"],
        per_backend_cost={"cheap_be": 1.0},
    )
    expensive_high_fid = fake_adapter_factory(
        "ionq",
        kind="cloud-ion",
        backends=["ionq_aria"],
        per_backend_cost={"ionq_aria": 20.0},
    )
    router = Router(providers=[cheap_low_fid, expensive_high_fid])

    # Demand fidelity above the cloud-other prior (0.97) → only ion (0.99) qualifies.
    decision = router.decide(
        BackendRequest(
            circuit_qasm=small_qasm,
            shots=1024,
            budget_usd=50.0,
            min_fidelity=0.98,
        )
    )

    assert decision.provider == "ionq"
