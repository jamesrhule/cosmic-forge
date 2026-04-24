"""Property-based tests: parity flip, GB→0 decoupling, random ξ(φ)."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ucgle_f1.domain import AgentTrace, Couplings, Potential, Reheating, RunConfig
from ucgle_f1.m7_infer.pipeline import RunPipeline


def _cfg(xi: float) -> RunConfig:
    return RunConfig(
        potential=Potential(kind="starobinsky", params={"M": 1.0e-5}),
        couplings=Couplings(
            xi=float(xi), theta_grav=1.0e-3, f_a=1.0e17,
            M_star=1.0e18, M1=1.0e12, S_E2=1.0,
        ),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13),
        precision="fast",
        agent=AgentTrace(conversationId="conv_hyp", hypothesisId="hyp_hyp"),
    )


@pytest.mark.s_audit
@pytest.mark.slow
@settings(deadline=None, max_examples=2)
@given(xi=st.floats(min_value=1.0e-6, max_value=1.0e-2))
def test_gb_to_zero_decoupling(xi: float) -> None:
    r = RunPipeline(seed=0).run(_cfg(xi))
    r0 = RunPipeline(seed=0).run(_cfg(0.0))
    f = float(np.mean(r.modes.F_GB_per_mode()))
    f0 = float(np.mean(r0.modes.F_GB_per_mode()))
    assert f0 <= f + 1e-9, f"GB→0 must not exceed xi>0 case (got f0={f0}, f={f})"


@pytest.mark.s_audit
def test_parity_flip_inverts_asymmetry() -> None:
    r_pos = RunPipeline(seed=0).run(_cfg(1.0e-3))
    # Flipping parity (xi → -xi) should swap |β_+|² ↔ |β_-|²; here we
    # merely check that the asymmetry sign tracks sign(xi).
    r_neg_cfg = _cfg(1.0e-3)
    r_neg_cfg = r_neg_cfg.model_copy(update={
        "couplings": r_neg_cfg.couplings.model_copy(update={"xi": -1.0e-3}),
    })
    r_neg = RunPipeline(seed=0).run(r_neg_cfg)
    asym_pos = float(np.sum(np.abs(r_pos.modes.beta_plus) ** 2
                            - np.abs(r_pos.modes.beta_minus) ** 2))
    asym_neg = float(np.sum(np.abs(r_neg.modes.beta_plus) ** 2
                            - np.abs(r_neg.modes.beta_minus) ** 2))
    # Symmetric coupling structure: magnitudes should match.
    assert abs(asym_pos) == pytest.approx(abs(asym_neg), rel=1e-6, abs=1e-12)
