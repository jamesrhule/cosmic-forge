"""budget>0 selects the cheapest backend that meets the fidelity floor.

PROMPT 6A spec: with $50 of budget and IBM Heron pricing cheaper
than IonQ Forte (per the static seed), the router selects Heron.
We force require_real_hardware=True so the local-zero-cost
backends are excluded from the candidate pool.

Pricing seed values for `shots=4096`:
  - ibm_heron: per_second_usd=$1.60, ~6.4s @ 4096 shots → $10.24.
  - braket_ionq_forte: per_task=$0.30 + per_shot=$0.080 × 4096 → $327.98.
  - braket_ionq_aria: per_task=$0.30 + per_shot=$0.030 × 4096 → $123.18.

Heron wins under a $50 cap; Aria/Forte exceed it. The test pins
the expected provider/backend rather than the dollar amount so a
seed update doesn't break it.
"""

from __future__ import annotations

import pytest

from qcompass_router import (
    BraketAdapter,
    IBMAdapter,
    Router,
    RouterRequest,
)


class _IBMAvailable(IBMAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


class _BraketAvailable(BraketAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


def test_budget_50_selects_ibm_open_plan_over_forte() -> None:
    """v1 asserted ibm_heron specifically. PROMPT 6 v2 added
    ibm_kingston (Open Plan, fidelity 0.992) to the seed; both are
    free-tier, so the higher-fidelity Kingston wins on tie-break.
    The audit invariant — IBM Open Plan beats Braket — holds; we
    relax the backend assertion to accept either Open Plan device.
    """
    router = Router(providers=[_IBMAvailable(), _BraketAvailable()])
    req = RouterRequest(
        shots=4096,
        budget_usd=50.0,
        min_fidelity=0.99,
        require_real_hardware=True,
    )
    decision = router.decide(req)
    assert decision.provider == "ibm"
    assert decision.backend in {"ibm_heron", "ibm_kingston"}
    assert decision.cost_estimate_usd <= req.budget_usd
    assert decision.fidelity_estimate >= req.min_fidelity


def test_no_candidate_when_fidelity_floor_too_high() -> None:
    """min_fidelity=0.9999 rules out everything in the seed."""
    from qcompass_router import BudgetExceeded

    router = Router(providers=[_IBMAvailable(), _BraketAvailable()])
    req = RouterRequest(
        shots=4096,
        budget_usd=1000.0,
        min_fidelity=0.9999,
        require_real_hardware=True,
    )
    with pytest.raises(BudgetExceeded) as exc:
        router.decide(req)
    assert exc.value.code == "NO_CANDIDATE_BACKEND"
