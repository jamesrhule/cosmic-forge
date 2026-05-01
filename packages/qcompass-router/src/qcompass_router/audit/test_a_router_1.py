"""A-router-1: budget=0 always routes to local; never to cloud."""

from __future__ import annotations

from qcompass_router import Router, RouterRequest


def test_budget_zero_picks_local(stub_router: Router) -> None:
    decision = stub_router.decide(RouterRequest(budget_usd=0.0))
    assert decision.provider in {"local_aer", "local_lightning"}
    assert decision.cost_estimate_usd == 0.0


def test_budget_zero_never_cloud(stub_router: Router) -> None:
    """Even with cloud SDKs available, budget=0 must not pick them."""
    for _ in range(20):
        decision = stub_router.decide(RouterRequest(budget_usd=0.0))
        assert decision.provider not in {"ibm", "braket", "ionq", "azure"}
