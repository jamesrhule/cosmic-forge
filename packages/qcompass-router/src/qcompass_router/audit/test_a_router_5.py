"""A-router-5: SQD on IBM Heron selected over IonQ Forte at $50 budget.

The static seed prices Heron at ~$6.40 / 4096-shot run and Forte
at ~$328 — Heron wins under a $50 cap. We pin the (provider,
backend) result rather than the exact dollar amount so a future
seed update doesn't break the test.
"""

from __future__ import annotations

from qcompass_router import Router, RouterRequest


def test_budget_50_picks_ibm_over_forte(stub_router: Router) -> None:
    decision = stub_router.decide(RouterRequest(
        shots=4096,
        budget_usd=50.0,
        min_fidelity=0.99,
        require_real_hardware=True,
    ))
    assert decision.provider == "ibm"
    assert decision.backend == "ibm_heron"
    assert decision.cost_estimate_usd <= 50.0


def test_budget_400_still_picks_heron_when_cheaper(stub_router: Router) -> None:
    """Heron stays the cheapest at fidelity ≥ 0.99 even with headroom."""
    decision = stub_router.decide(RouterRequest(
        shots=4096,
        budget_usd=400.0,
        min_fidelity=0.99,
        require_real_hardware=True,
    ))
    assert decision.provider == "ibm"
    assert decision.backend == "ibm_heron"
