"""preferred_providers must restrict the candidate pool even when other
providers are cheaper.
"""

from __future__ import annotations

import pytest

from qcompass_router.decision import BackendRequest
from qcompass_router.router import BudgetExceeded, Router


def test_preferred_excludes_ibm_even_when_cheaper(small_qasm, fake_adapter_factory):
    ibm = fake_adapter_factory(
        "ibm",
        kind="cloud-sc",
        backends=["ibm_heron"],
        per_backend_cost={"ibm_heron": 1.0},
    )
    ionq = fake_adapter_factory(
        "ionq",
        kind="cloud-ion",
        backends=["ionq_aria"],
        per_backend_cost={"ionq_aria": 25.0},
    )
    router = Router(providers=[ibm, ionq])

    decision = router.decide(
        BackendRequest(
            circuit_qasm=small_qasm,
            shots=1024,
            budget_usd=50.0,
            preferred_providers=["ionq"],
            min_fidelity=0.95,
        )
    )

    assert decision.provider == "ionq"
    assert decision.cost_estimate_usd == 25.0


def test_preferred_with_no_match_raises(small_qasm, fake_adapter_factory):
    ibm = fake_adapter_factory(
        "ibm",
        kind="cloud-sc",
        backends=["ibm_heron"],
        per_backend_cost={"ibm_heron": 1.0},
    )
    router = Router(providers=[ibm])

    with pytest.raises(BudgetExceeded):
        router.decide(
            BackendRequest(
                circuit_qasm=small_qasm,
                shots=1024,
                budget_usd=50.0,
                preferred_providers=["ionq"],
            )
        )
