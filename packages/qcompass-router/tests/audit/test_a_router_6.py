"""A-router-6: TransformRecord propagates into RoutingDecision and
ProvenanceRecord.error_mitigation_config.

The qcompass-core integration is guarded by `pytest.importorskip` —
when qcompass-core is not present in the environment (e.g. CI before
PROMPT 0 lands), the test cleanly SKIPS. The local-only assertions on
RoutingDecision still run.
"""

from __future__ import annotations

import pytest

from qcompass_router.decision import RoutingDecision
from qcompass_router.transforms import apply_transforms
from qcompass_router.transforms.record import TransformRecord


def _build_decision_with_transforms() -> RoutingDecision:
    _, records = apply_transforms("OPENQASM 2.0;", ["cutting", "obp"])
    return RoutingDecision(
        provider="ibm",
        backend="ibm_heron",
        cost_estimate_usd=5.0,
        queue_time_s_estimate=600.0,
        fidelity_estimate=0.97,
        transforms_applied=[r.name for r in records],
        transform_records=records,
        calibration={"drift_score": 0.0, "stale": False, "threshold": 3.0},
        reason="test",
    )


def test_transform_records_carry_into_decision() -> None:
    decision = _build_decision_with_transforms()
    assert isinstance(decision.transform_records, list)
    assert len(decision.transform_records) == 2
    names = [r.name for r in decision.transform_records]
    assert names == ["cutting", "obp"]
    # Both fields stay in sync.
    assert decision.transforms_applied == names
    for r in decision.transform_records:
        assert isinstance(r, TransformRecord)


def test_round_trip_into_provenance_record() -> None:
    manifest = pytest.importorskip("qcompass_core.manifest")
    ProvenanceRecord = getattr(manifest, "ProvenanceRecord", None)
    if ProvenanceRecord is None:
        pytest.skip("qcompass_core.manifest.ProvenanceRecord not available")

    decision = _build_decision_with_transforms()
    record = ProvenanceRecord(
        provider=decision.provider,
        backend=decision.backend,
        error_mitigation_config={
            "transforms": [r.model_dump() for r in decision.transform_records],
            "calibration": decision.calibration,
        },
    )
    assert record.error_mitigation_config["transforms"][0]["name"] == "cutting"
