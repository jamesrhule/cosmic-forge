"""A-router-3: calibration drift > 3σ raises CALIBRATION_DRIFT."""

from __future__ import annotations

from datetime import date

import pytest

from qcompass_router import (
    CalibrationCache,
    CalibrationDrift,
    CalibrationSnapshot,
    Router,
    RouterRequest,
)
from qcompass_router.audit.conftest import seed_history


def test_drift_above_3sigma_raises(
    stub_router: Router, calibration_cache: CalibrationCache,
) -> None:
    """Seed 7 days of stable history then plant a 10x outlier today.

    PROMPT 6 v2 added ibm_kingston (Open Plan) which now wins the
    free-tier tie-break on fidelity. We seed BOTH ibm_heron and
    ibm_kingston so whichever the router picks fires the drift
    gate.
    """
    provider = "ibm"
    for backend in ("ibm_heron", "ibm_kingston"):
        seed_history(
            calibration_cache, provider=provider, backend=backend,
            days=7, base_two_q=0.01, base_readout=0.02, base_t1_t2=100.0,
        )
        # Today's snapshot: 10x worse two-qubit error.
        calibration_cache.record(CalibrationSnapshot(
            provider=provider, backend=backend, day=date.today(),
            two_qubit_error=0.10,
            readout_error=0.02,
            t1_t2_us=100.0,
        ))

    router = Router(
        providers=stub_router.providers, calibration=calibration_cache,
    )
    with pytest.raises(CalibrationDrift) as exc:
        router.decide(RouterRequest(
            shots=512, budget_usd=50.0, min_fidelity=0.99,
            require_real_hardware=True,
        ))
    assert exc.value.code == "CALIBRATION_DRIFT"
    assert exc.value.metric == "two_qubit_error"
    assert exc.value.observed == 0.10
    assert exc.value.median_7d == 0.01


def test_no_drift_when_history_empty(
    stub_router: Router, calibration_cache: CalibrationCache,
) -> None:
    """First-week behaviour: no history → no drift gate fires."""
    router = Router(
        providers=stub_router.providers, calibration=calibration_cache,
    )
    decision = router.decide(RouterRequest(
        shots=512, budget_usd=50.0, min_fidelity=0.99,
        require_real_hardware=True,
    ))
    assert decision is not None
