"""A-router-3: synthetic 4σ drift in calibration cache → CalibrationDrift.

Seven days of two_q_error around 0.01 then a single 0.05 sample yields
drift = |0.05 - 0.01| / 0.01 = 4.0 → above the 3.0 threshold → router
must raise `CalibrationDrift("CALIBRATION_DRIFT")`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from qcompass_router.calibration import (
    CalibrationCache,
    CalibrationDrift,
    FoMaC,
    assert_no_drift,
)
from qcompass_router.decision import BackendRequest
from qcompass_router.router import Router

from tests.conftest import FakeAdapter

SMALL_QASM = (
    'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\n'
    "h q[0];\ncx q[0],q[1];\nmeasure q -> c;\n"
)


def _seed_history(cache: CalibrationCache, provider: str, backend: str) -> None:
    base = datetime.now(timezone.utc) - timedelta(days=6)
    for i in range(7):
        cache.update(
            provider,
            backend,
            FoMaC(
                two_q_error=0.01,
                readout_error=0.018,
                t1_us=260.0,
                t2_us=180.0,
                recorded_at=base + timedelta(days=i),
            ),
        )


def test_drift_score_assertion(calibration_cache: CalibrationCache) -> None:
    _seed_history(calibration_cache, "ibm", "ibm_torino")
    # Inject a 4σ sample.
    calibration_cache.update(
        "ibm",
        "ibm_torino",
        FoMaC(
            two_q_error=0.05,
            readout_error=0.018,
            t1_us=260.0,
            t2_us=180.0,
        ),
    )
    drift = calibration_cache.drift_score("ibm", "ibm_torino")
    assert drift >= 3.5  # |0.05-0.01|/0.01 = 4.0

    with pytest.raises(CalibrationDrift) as excinfo:
        assert_no_drift(calibration_cache, "ibm", "ibm_torino")
    assert excinfo.value.error_code == "CALIBRATION_DRIFT"
    assert str(excinfo.value) == "CALIBRATION_DRIFT"


def test_router_refuses_on_drift(calibration_cache: CalibrationCache) -> None:
    _seed_history(calibration_cache, "ibm", "ibm_heron")
    calibration_cache.update(
        "ibm",
        "ibm_heron",
        FoMaC(
            two_q_error=0.05,
            readout_error=0.018,
            t1_us=260.0,
            t2_us=180.0,
        ),
    )

    ibm = FakeAdapter("ibm", kind="cloud-sc", backends=["ibm_heron"])
    router = Router(providers=[ibm], calibration=calibration_cache)

    with pytest.raises(CalibrationDrift):
        router.decide(
            BackendRequest(
                circuit_qasm=SMALL_QASM,
                shots=1024,
                budget_usd=50.0,
            )
        )
