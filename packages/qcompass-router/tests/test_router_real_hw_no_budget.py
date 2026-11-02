"""budget=0 + require_real_hardware=True must raise BudgetExceeded."""

from __future__ import annotations

import pytest

from qcompass_router import BudgetExceeded, Router, RouterRequest


def test_real_hardware_at_zero_budget_raises() -> None:
    router = Router()
    req = RouterRequest(budget_usd=0.0, require_real_hardware=True)
    with pytest.raises(BudgetExceeded) as exc:
        router.decide(req)
    assert exc.value.code == "BUDGET_EXCEEDED"
    assert "require_real_hardware" in str(exc.value)
