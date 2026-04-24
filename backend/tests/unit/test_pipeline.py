"""End-to-end smoke test for the M1→M6 pipeline."""

from __future__ import annotations

import numpy as np

from ucgle_f1.domain import AgentTrace, Couplings, Potential, Reheating, RunConfig
from ucgle_f1.m7_infer.audit import run_audit
from ucgle_f1.m7_infer.pipeline import RunPipeline, build_run_result


def _cfg() -> RunConfig:
    return RunConfig(
        potential=Potential(kind="starobinsky", params={"M": 1.0e-5}),
        couplings=Couplings(xi=1.0e-3, theta_grav=1.0e-3, f_a=1.0e17,
                            M_star=1.0e18, M1=1.0e12, S_E2=1.0),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13),
        precision="fast",
        agent=AgentTrace(conversationId="c", hypothesisId="h"),
    )


def test_full_pipeline_runs() -> None:
    pr = RunPipeline(seed=0).run(_cfg())
    assert np.isfinite(pr.eta_B)
    # All 6 modules recorded timings.
    for m in ("M1", "M2", "M3", "M4", "M5", "M6"):
        assert m in pr.module_seconds


def test_build_run_result_and_audit() -> None:
    cfg = _cfg()
    pr = RunPipeline(seed=0).run(cfg)
    result = build_run_result("run_test", cfg, pr, audit_runner=run_audit)
    assert result.audit.summary.total == 15
    # At least half the S-checks should PASS on the seed smoke
    # configuration. Full V2 recovery requires precision='high'.
    assert result.audit.summary.passed >= 7
