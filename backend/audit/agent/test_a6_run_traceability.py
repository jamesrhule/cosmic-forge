"""A6 — every agent-initiated run carries (conversationId, hypothesisId).

``start_run`` rejects configs missing either field with
``AUDIT_VIOLATION``. The memory store's ``run_link`` table
persists the mapping so downstream analyses stay traceable.
"""

from __future__ import annotations

import pytest

from ucgle_f1.domain import (
    AgentTrace,
    Couplings,
    Potential,
    Reheating,
    RunConfig,
    ServiceError,
)
from ucgle_f1.m8_agent.memory import get_store
from ucgle_f1.m8_agent.tools.simulator import start_run


def _cfg(agent: AgentTrace | None) -> RunConfig:
    return RunConfig(
        potential=Potential(kind="starobinsky", params={"M": 1.0e-5}),
        couplings=Couplings(xi=1.0e-3, theta_grav=1.0e-3, f_a=1.0e17,
                            M_star=1.0e18, M1=1.0e12, S_E2=1.0),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13),
        precision="fast",
        agent=agent,
    )


@pytest.mark.a_audit
async def test_start_run_requires_agent_trace() -> None:
    store = get_store()
    tok = store.issue_approval(["start_run"], ttl_seconds=60)
    with pytest.raises(ServiceError) as exc:
        await start_run(_cfg(agent=None), approval_token=tok.tokenId)
    assert exc.value.code == "AUDIT_VIOLATION"


@pytest.mark.a_audit
async def test_start_run_links_run_to_conversation() -> None:
    store = get_store()
    tok = store.issue_approval(["start_run"], ttl_seconds=60)
    cfg = _cfg(AgentTrace(conversationId="conv_a6", hypothesisId="hyp_a6"))
    out = await start_run(cfg, approval_token=tok.tokenId)
    link = store.run_link(out.run_id)
    assert link is not None
    assert link.conversationId == "conv_a6"
    assert link.hypothesisId == "hyp_a6"


@pytest.mark.a_audit
async def test_start_run_rejects_without_approval() -> None:
    cfg = _cfg(AgentTrace(conversationId="c", hypothesisId="h"))
    with pytest.raises(ServiceError) as exc:
        await start_run(cfg, approval_token="appr_not_real")
    assert exc.value.code == "APPROVAL_REQUIRED"
