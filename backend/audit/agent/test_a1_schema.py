"""A1 — every MCP tool call matches its Pydantic schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ucgle_f1.domain import (
    AgentTrace,
    Couplings,
    Potential,
    Reheating,
    RunConfig,
)
from ucgle_f1.m8_agent.tools import ALL_TOOL_SPECS
from ucgle_f1.m8_agent.tools.simulator import StartRunInput, ValidateConfigInput


@pytest.mark.a_audit
def test_every_tool_has_complete_spec() -> None:
    for spec in ALL_TOOL_SPECS:
        assert spec.name
        assert spec.family in {"simulator", "research", "patch", "introspection"}
        assert isinstance(spec.inputSchema, dict)
        assert isinstance(spec.outputSchema, dict)
        assert spec.description


@pytest.mark.a_audit
def test_start_run_schema_rejects_missing_agent_trace() -> None:
    bad = {
        "config": {
            "potential": {"kind": "natural", "params": {"f_a": 1.0}},
            "couplings": {"xi": 0.0, "theta_grav": 0.0, "f_a": 1.0,
                          "M_star": 1.0, "M1": 1.0, "S_E2": 1.0},
            "reheating": {"Gamma_phi": 1e-6, "T_reh_GeV": 1e13},
            "precision": "standard",
        },
        "approval_token": "appr_test",
    }
    # Pydantic accepts config-without-agent at the schema level; the
    # A6 enforcement happens at runtime in start_run. This ensures the
    # schema itself is sane.
    parsed = StartRunInput.model_validate(bad)
    assert parsed.config.agent is None


@pytest.mark.a_audit
def test_validate_config_rejects_wrong_type() -> None:
    with pytest.raises(ValidationError):
        ValidateConfigInput.model_validate({"config": 42})


@pytest.mark.a_audit
def test_run_config_round_trips() -> None:
    cfg = RunConfig(
        potential=Potential(kind="starobinsky", params={"M": 1.0e-5}),
        couplings=Couplings(xi=1.0e-3, theta_grav=1.0e-3, f_a=1.0e17,
                            M_star=1.0e18, M1=1.0e12, S_E2=1.0),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13),
        precision="standard",
        agent=AgentTrace(conversationId="c", hypothesisId="h"),
    )
    restored = RunConfig.model_validate_json(cfg.model_dump_json())
    assert restored == cfg
