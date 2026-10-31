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
        transforms_applied=records,
        calibration={"drift_score": 0.0, "stale": False, "threshold": 3.0},
        reason="test",
    )


# test_transform_records_carry_into_decision was removed by P0-02: covered
# by qcompass_router/audit/test_a_router_6.py::test_transforms_propagate_to_decision
# (router-produced records, order, TransformRecord type) and
# tests/test_p002_unification.py::test_transform_records_measure_depth_and_runtime.


def test_round_trip_into_provenance_record() -> None:
    manifest = pytest.importorskip("qcompass_core.manifest")
    ProvenanceRecord = getattr(manifest, "ProvenanceRecord", None)
    if ProvenanceRecord is None:
        pytest.skip("qcompass_core.manifest.ProvenanceRecord not available")

    # qcompass_core.ProvenanceRecord has no provider/backend fields and
    # requires classical_reference_hash (P0-02 corrected test): the
    # routing target travels inside error_mitigation_config.
    decision = _build_decision_with_transforms()
    record = ProvenanceRecord(
        classical_reference_hash="sha256:a-router-6",
        error_mitigation_config={
            "provider": decision.provider,
            "backend": decision.backend,
            "transforms": [r.model_dump() for r in decision.transforms_applied],
            "calibration": decision.calibration,
        },
    )
    assert record.error_mitigation_config["transforms"][0]["name"] == "cutting"
    restored = ProvenanceRecord.model_validate(record.model_dump())
    assert restored.error_mitigation_config == record.error_mitigation_config
    assert [
        TransformRecord.model_validate(t).name
        for t in restored.error_mitigation_config["transforms"]
    ] == ["cutting", "obp"]
    assert restored.error_mitigation_config["provider"] == "ibm"
    assert restored.error_mitigation_config["backend"] == "ibm_heron"
