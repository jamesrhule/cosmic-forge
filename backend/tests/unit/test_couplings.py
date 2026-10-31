"""P1-03: physical Chern–Simons / Gauss–Bonnet couplings — strict properties."""

from __future__ import annotations

import numpy as np
import pytest

from ucgle_f1.domain import AgentTrace, Couplings, Potential, Reheating, RunConfig
from ucgle_f1.m7_infer.couplings import (
    A_END_H_END,
    M3_TAU_END,
    M3_TAU_START,
    coupling_profile,
)
from ucgle_f1.m7_infer.pipeline import RunPipeline

STARO = Potential(kind="starobinsky", params={"M": 1.0e-5})


def _c(xi: float = 1.0e-3, theta: float = 1.0e-3) -> Couplings:
    return Couplings(xi=xi, theta_grav=theta, f_a=1.0e17, M_star=1.0e18, M1=1.0e12, S_E2=1.0)


def _cfg(xi: float, theta: float = 1.0e-3) -> RunConfig:
    return RunConfig(
        potential=STARO, couplings=_c(xi, theta),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13), precision="fast",
        agent=AgentTrace(conversationId="c", hypothesisId="h"),
    )


# ── coupling level (exact) ──────────────────────────────────────────


def test_gb_to_zero_decouples_exactly_at_coupling_level() -> None:
    p = coupling_profile(STARO, _c(xi=0.0))
    assert np.all(p.B == 0.0) and np.all(p.C == 0.0)
    assert np.any(p.A_plus != 0.0)  # CS still on


def test_gb_terms_are_linear_in_xi_and_cs_term_independent_of_xi() -> None:
    p1, p2 = coupling_profile(STARO, _c(xi=1e-3)), coupling_profile(STARO, _c(xi=2e-3))
    np.testing.assert_allclose(p2.B, 2.0 * p1.B, rtol=1e-12, atol=0)
    np.testing.assert_allclose(p2.C, 2.0 * p1.C, rtol=1e-12, atol=0)
    np.testing.assert_array_equal(p2.A_plus, p1.A_plus)


def test_cs_term_is_parity_odd_and_gb_parity_even() -> None:
    p = coupling_profile(STARO, _c())
    for t in (-4.0, -1.0, -0.01):
        a = p.A_of_tau(t)
        assert a[0] == -a[1]
        b, c = p.B_of_tau(t), p.C_of_tau(t)
        assert b[0] == b[1] and c[0] == c[1]
    pm = coupling_profile(STARO, _c(theta=-1e-3))
    np.testing.assert_array_equal(pm.A_plus, -p.A_plus)


def test_window_normalisation() -> None:
    p = coupling_profile(STARO, _c())
    assert p.tau[0] <= -5.0
    # τ = −1/(a_end H_end) at the end of inflation.
    assert p.tau[-1] == pytest.approx(-1.0e-3, rel=1e-12)


def test_a_end_h_end_is_derived_from_the_m3_window() -> None:
    # A_END_H_END is not free: the end of inflation (ε = 1) is the last point
    # of M3's high-precision window, τ(N_end) = −1/(a_end H_end).
    assert A_END_H_END == -1.0 / M3_TAU_END["high"]
    p = coupling_profile(STARO, _c())
    tr = p.trajectory
    assert p.tau[-1] == M3_TAU_END["high"]
    assert p.a[-1] * float(np.interp(p.N_end, tr.N, tr.H)) == pytest.approx(A_END_H_END, rel=1e-6)
    # τ = −5 lies ≈ ln(5·10³) e-folds before the end (de Sitter estimate).
    assert p.tau[0] <= M3_TAU_START


@pytest.mark.parametrize("c", [0.1, 10.0])
def test_a_normalisation_is_a_gauge_choice(c: float) -> None:
    # a → c·a: τ → τ/c and, with k → c·k, B → c²B, A·k → c²A·k, C → C, so
    # ω²τ² (and every |β|²) is unchanged. Only k/(aH) is physical; the
    # normalisation fixes the unit of M3's k and nothing else.
    p1 = coupling_profile(STARO, _c(), tau_start=-5.0)
    pc = coupling_profile(STARO, _c(), tau_start=-5.0 / c, a_end_H_end=c * A_END_H_END)
    for t in (-4.0, -1.0, -0.1, -0.01):
        np.testing.assert_allclose(pc.B_of_tau(t / c), c**2 * p1.B_of_tau(t), rtol=1e-6)
        np.testing.assert_allclose(pc.A_of_tau(t / c), c * p1.A_of_tau(t), rtol=1e-6)
        np.testing.assert_allclose(pc.C_of_tau(t / c), p1.C_of_tau(t), rtol=1e-6)


def test_physical_is_the_pipeline_default() -> None:
    assert RunPipeline().coupling_model == "physical"


# ── pipeline level (physical coupling model) ───────────────────────


@pytest.fixture(scope="module")
def f_gb_zero() -> float:
    r0 = RunPipeline(seed=0, coupling_model="physical").run(_cfg(0.0))
    return float(np.mean(r0.modes.F_GB_per_mode()))


@pytest.mark.parametrize("xi", [1.0e-6, 1.0e-4, 7.8125e-3, 1.0e-2])
def test_gb_to_zero_decoupling_strict(xi: float, f_gb_zero: float) -> None:
    # Strict: F_GB is continuous in ξ at 0 (|ΔF| ≤ 1e-12 here), and the frozen
    # audit's inequality f0 ≤ f + 1e-9 holds, including ξ = 0.0078125.
    r = RunPipeline(seed=0, coupling_model="physical").run(_cfg(xi))
    f = float(np.mean(r.modes.F_GB_per_mode()))
    assert abs(f - f_gb_zero) <= 1e-12
    assert f_gb_zero <= f + 1e-9


def test_parity_flip_swaps_helicities_exactly() -> None:
    rp = RunPipeline(seed=0, coupling_model="physical").run(_cfg(1e-3, 1e-3))
    rm = RunPipeline(seed=0, coupling_model="physical").run(_cfg(1e-3, -1e-3))
    np.testing.assert_array_equal(np.abs(rm.modes.beta_plus) ** 2, np.abs(rp.modes.beta_minus) ** 2)
    np.testing.assert_array_equal(np.abs(rm.modes.beta_minus) ** 2, np.abs(rp.modes.beta_plus) ** 2)


def test_xi_flip_preserves_asymmetry_magnitude() -> None:
    # The frozen audit's ξ → −ξ statement: GB is parity-even, so flipping ξ
    # leaves |Σ(|β₊|² − |β₋|²)| unchanged to first order.
    def asym(xi: float) -> float:
        r = RunPipeline(seed=0, coupling_model="physical").run(_cfg(xi))
        return float(np.sum(np.abs(r.modes.beta_plus) ** 2 - np.abs(r.modes.beta_minus) ** 2))

    assert abs(asym(1e-3)) == pytest.approx(abs(asym(-1e-3)), rel=1e-6, abs=1e-12)
