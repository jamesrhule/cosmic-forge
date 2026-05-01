"""preferred_providers excludes adapters not on the list.

When the user specifies preferred_providers=["ionq"], the router
MUST exclude IBM, Braket, etc., even if one of them would
otherwise be cheaper. This is the user's escape hatch when they
want hardware diversity over raw cost.
"""

from __future__ import annotations

from qcompass_router import (
    BraketAdapter,
    IBMAdapter,
    IonQAdapter,
    Router,
    RouterRequest,
)


class _IBMAvailable(IBMAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


class _BraketAvailable(BraketAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


class _IonQAvailable(IonQAdapter):
    def is_available(self) -> bool:  # type: ignore[override]
        return True


def test_preferred_filter_excludes_ibm_even_when_cheaper() -> None:
    router = Router(
        providers=[_IBMAvailable(), _BraketAvailable(), _IonQAvailable()],
    )
    req = RouterRequest(
        shots=512,
        budget_usd=200.0,
        min_fidelity=0.99,
        preferred_providers=["ionq"],
        require_real_hardware=True,
    )
    decision = router.decide(req)
    # ionq native + braket_ionq_* are both on Braket; the preferred
    # filter excludes Braket entirely, so only the native ionq path
    # remains.
    assert decision.provider == "ionq"


def test_preferred_filter_with_no_match_raises() -> None:
    from qcompass_router import BudgetExceeded

    router = Router(providers=[_IBMAvailable()])
    req = RouterRequest(
        shots=512,
        budget_usd=200.0,
        preferred_providers=["pasqal"],
        require_real_hardware=True,
    )
    try:
        router.decide(req)
    except BudgetExceeded as exc:
        assert exc.code == "NO_CANDIDATE_BACKEND"
        return
    raise AssertionError("expected BudgetExceeded(NO_CANDIDATE_BACKEND)")
