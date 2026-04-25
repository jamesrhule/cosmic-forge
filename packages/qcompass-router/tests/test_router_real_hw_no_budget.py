"""budget=0 with require_real_hardware=True must raise BudgetExceeded."""

from __future__ import annotations

import pytest

from qcompass_router.decision import BackendRequest
from qcompass_router.router import BudgetExceeded, Router


def test_real_hardware_with_zero_budget_raises(small_qasm, fake_adapter_factory):
    aer = fake_adapter_factory("local_aer", kind="local")
    ibm = fake_adapter_factory("ibm", kind="cloud-sc", cost=5.0)
    router = Router(providers=[aer, ibm])

    with pytest.raises(BudgetExceeded):
        router.decide(
            BackendRequest(
                circuit_qasm=small_qasm,
                shots=1024,
                budget_usd=0.0,
                require_real_hardware=True,
            )
        )
