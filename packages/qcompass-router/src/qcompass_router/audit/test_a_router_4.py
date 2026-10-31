"""A-router-4: every RoutingDecision carries the three required floats."""

from __future__ import annotations

from qcompass_router import Router, RouterRequest, RoutingDecision


def test_decision_carries_all_three_metrics(stub_router: Router) -> None:
    decision = stub_router.decide(RouterRequest(budget_usd=0.0))
    assert isinstance(decision, RoutingDecision)
    # The Pydantic model itself enforces the presence of the three
    # fields (no defaults). This test pins that the values are
    # real numbers, not None.
    assert isinstance(decision.cost_estimate_usd, float)
    assert isinstance(decision.queue_time_s_estimate, float)
    assert isinstance(decision.fidelity_estimate, float)
    assert decision.cost_estimate_usd >= 0.0
    assert decision.queue_time_s_estimate >= 0.0
    assert 0.0 <= decision.fidelity_estimate <= 1.0


def test_decision_carries_metrics_paid_path(stub_router: Router) -> None:
    decision = stub_router.decide(RouterRequest(
        shots=512, budget_usd=200.0, min_fidelity=0.95,
        require_real_hardware=True,
    ))
    assert decision.cost_estimate_usd > 0.0
    assert decision.fidelity_estimate >= 0.95


def test_required_fields_present_in_schema() -> None:
    schema = RoutingDecision.model_json_schema()
    required = set(schema.get("required", []))
    for field in ("cost_estimate_usd", "queue_time_s_estimate",
                  "fidelity_estimate", "provider", "backend", "reason"):
        assert field in required, (
            f"RoutingDecision MUST require {field}; got {required}"
        )
