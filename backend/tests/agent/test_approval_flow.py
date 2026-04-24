"""End-to-end approval + start_run + stream flow."""

from __future__ import annotations

import asyncio

import pytest

from ucgle_f1.domain import AgentTrace, Couplings, Potential, Reheating, RunConfig
from ucgle_f1.m8_agent.memory import get_store
from ucgle_f1.m8_agent.tools.simulator import get_run, start_run, stream_run


def _cfg() -> RunConfig:
    return RunConfig(
        potential=Potential(kind="starobinsky", params={"M": 1.0e-5}),
        couplings=Couplings(xi=1.0e-3, theta_grav=1.0e-3, f_a=1.0e17,
                            M_star=1.0e18, M1=1.0e12, S_E2=1.0),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13),
        precision="standard",
        agent=AgentTrace(conversationId="conv_e2e", hypothesisId="hyp_e2e"),
    )


@pytest.mark.asyncio
async def test_full_agent_run_flow() -> None:
    store = get_store()
    tok = store.issue_approval(["start_run"], ttl_seconds=120)
    out = await start_run(_cfg(), approval_token=tok.tokenId)
    run_id = out.run_id

    seen_statuses: list[str] = []
    async for ev in stream_run(run_id):
        if getattr(ev, "type", None) == "status":
            seen_statuses.append(ev.status)  # type: ignore[attr-defined]
        if getattr(ev, "type", None) == "result":
            break
        if getattr(ev, "status", None) in {"failed", "canceled"}:
            break
    # We expect at least "running" → "completed".
    assert "running" in seen_statuses
    r = get_run(run_id)
    assert r.status == "completed"
    assert r.audit.summary.total == 15
    _ = asyncio
