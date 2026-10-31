"""budget=0 with require_real_hardware=False routes to local_aer.

When qiskit-aer is unavailable the router falls back to
local_lightning; if neither is available it raises BudgetExceeded
with code NO_LOCAL_BACKEND. This test pins the preferred ordering
under the "no SDK installed" path by stubbing both local adapters
as available.
"""

from __future__ import annotations

import pytest

from qcompass_router import (
    BudgetExceeded,
    LocalAerAdapter,
    LocalLightningAdapter,
    Router,
    RouterRequest,
)


class _FakeAvailable(LocalAerAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


class _FakeLightningAvailable(LocalLightningAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


def test_budget_zero_picks_local_aer_when_available() -> None:
    router = Router(providers=[_FakeAvailable(), _FakeLightningAvailable()])
    decision = router.decide(RouterRequest(budget_usd=0.0))
    assert decision.provider == "local_aer"
    assert decision.backend == "aer_simulator"
    assert decision.cost_estimate_usd == 0.0
    assert decision.fidelity_estimate == 1.0


def test_budget_zero_falls_back_to_lightning() -> None:
    """If only local_lightning is available, the router picks it."""

    class _AerUnavailable(LocalAerAdapter):
        def is_available(self) -> bool:  # type: ignore[override]
            return False

    router = Router(providers=[_AerUnavailable(), _FakeLightningAvailable()])
    decision = router.decide(RouterRequest(budget_usd=0.0))
    assert decision.provider == "local_lightning"


def test_budget_zero_raises_when_no_local_available() -> None:
    """If neither local adapter is available, raise NO_LOCAL_BACKEND."""

    class _AerUnavailable(LocalAerAdapter):
        def is_available(self) -> bool:  # type: ignore[override]
            return False

    class _LightningUnavailable(LocalLightningAdapter):
        def is_available(self) -> bool:  # type: ignore[override]
            return False

    router = Router(providers=[_AerUnavailable(), _LightningUnavailable()])
    with pytest.raises(BudgetExceeded) as exc:
        router.decide(RouterRequest(budget_usd=0.0))
    assert exc.value.code == "NO_LOCAL_BACKEND"
