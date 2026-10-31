"""A-router-6: transform stack records propagate to the decision.

The router accepts ``transforms=[...]`` and returns a decision
whose ``transforms_applied`` mirrors the requested order. Each
record carries the requested parameters; downstream callers
(qfull-* plugins) copy the records into
``ProvenanceRecord.error_mitigation_config`` so audits can trace
the mitigation policy back from the artifact.
"""

from __future__ import annotations

from qcompass_router import Router, RouterRequest, TransformRecord


def test_transforms_propagate_to_decision(stub_router: Router) -> None:
    decision = stub_router.decide(
        RouterRequest(budget_usd=0.0),
        circuit=object(),
        transforms=["aqc_tensor", "obp"],
    )
    assert len(decision.transforms_applied) == 2
    names = [r.name for r in decision.transforms_applied]
    assert names == ["aqc_tensor", "obp"]
    for record in decision.transforms_applied:
        assert isinstance(record, TransformRecord)


def test_transform_parameters_recorded(stub_router: Router) -> None:
    params = {"aqc_tensor": {"bond_dim": 128, "target_fidelity": 0.995}}
    decision = stub_router.decide(
        RouterRequest(budget_usd=0.0),
        circuit=object(),
        transforms=["aqc_tensor"],
        transform_parameters=params,
    )
    rec = decision.transforms_applied[0]
    assert rec.parameters["bond_dim"] == 128
    assert rec.parameters["target_fidelity"] == 0.995


def test_no_transforms_yields_empty_list(stub_router: Router) -> None:
    decision = stub_router.decide(RouterRequest(budget_usd=0.0))
    assert decision.transforms_applied == []
