"""A-router-5: IBM Open Plan selected over IonQ Forte at $50 budget.

PROMPT 6 v2 §A-router-5 names ibm_kingston as the device the
router prefers when budget=$50; v1 named ibm_heron. Both ride the
IBM Open Plan free tier, both cost ~$6.40 per 4096-shot run; the
v2 free-tier sort key (cost, then -fidelity) breaks ties on
fidelity, so ibm_kingston (0.992) wins over ibm_heron (0.99). The
audit invariant — IBM Open Plan beats Forte at $50 — holds for
either device. We accept either backend so the audit doesn't pin
the tie-break direction.
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
    assert decision.backend in {"ibm_heron", "ibm_kingston"}
    assert decision.cost_estimate_usd <= 50.0


def test_budget_400_still_picks_ibm_when_cheaper(stub_router: Router) -> None:
    """IBM Open Plan device stays the cheapest at fidelity ≥ 0.99
    even with headroom."""
    decision = stub_router.decide(RouterRequest(
        shots=4096,
        budget_usd=400.0,
        min_fidelity=0.99,
        require_real_hardware=True,
    ))
    assert decision.provider == "ibm"
    assert decision.backend in {"ibm_heron", "ibm_kingston"}
