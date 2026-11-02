"""P1-04: mpmath (dps 30) vs scipy quadrature cross-check in M4."""

from __future__ import annotations

import numpy as np
import pytest

from ucgle_f1.m4_anomaly.anomaly import QUAD_FLAG_THRESHOLD, quad_cross_check


def test_agrees_on_a_smooth_integrand() -> None:
    lk = np.linspace(-3.0, 3.0, 64)
    rel, flag = quad_cross_check(lk, np.exp(-lk**2))
    assert rel < QUAD_FLAG_THRESHOLD and not flag


def test_exact_for_piecewise_linear_data() -> None:
    # Both quadratures integrate the same interpolant: a triangle of area 1.
    rel, flag = quad_cross_check(np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0, 0.0]))
    assert rel == pytest.approx(0.0, abs=1e-14) and not flag


def test_pipeline_reports_the_cross_check() -> None:
    from ucgle_f1.domain import AgentTrace, Couplings, Potential, Reheating, RunConfig
    from ucgle_f1.m7_infer.pipeline import RunPipeline

    cfg = RunConfig(
        potential=Potential(kind="starobinsky", params={"M": 1.0e-5}),
        couplings=Couplings(xi=1e-3, theta_grav=1e-3, f_a=1e17, M_star=1e18, M1=1e12, S_E2=1.0),
        reheating=Reheating(Gamma_phi=1e-6, T_reh_GeV=1e13), precision="fast",
        agent=AgentTrace(conversationId="c", hypothesisId="h"),
    )
    an = RunPipeline(seed=0).run(cfg).anomaly
    assert np.isfinite(an.quad_rel_disagreement)
    assert an.quad_flag == (an.quad_rel_disagreement > QUAD_FLAG_THRESHOLD)
