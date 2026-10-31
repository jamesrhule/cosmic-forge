"""P1-01: conformal time in M1, plus the background scaling laws.

The scaling-law tests also guard the two physics drifts the fast audits
miss (docs/build/evidence/P0-07.md): the matter dilution coefficient in
``_rhs`` and the reduced Planck mass constant.
"""

from __future__ import annotations

import numpy as np
import pytest

from ucgle_f1.m1_background import BackgroundInputs, solve_background
from ucgle_f1.m1_background.background import M_PL_GEV


@pytest.fixture(scope="module")
def reheating_bg():  # type: ignore[no-untyped-def]
    # The pipeline's own M1 inputs (m7_infer/pipeline.py).
    return solve_background(BackgroundInputs(rho_phi_init=1.0e-9, rho_r_init=1.0e-20, Gamma_phi=1.0e-6))


def test_round_trip_N_tau_N_below_1e_10(reheating_bg) -> None:  # type: ignore[no-untyped-def]
    bg = reheating_bg
    rng = np.random.default_rng(1234)
    # Nodes, midpoints and random off-node points across the whole run.
    N = np.concatenate([bg.N, 0.5 * (bg.N[1:] + bg.N[:-1]), rng.uniform(bg.N[0], bg.N[-1], 2000)])
    back = bg.N_of_tau(bg.tau_of_N(N))
    rel = np.abs(back - N) / np.maximum(np.abs(N), 1e-300)
    rel = np.where(N == 0.0, np.abs(back - N), rel)
    assert float(np.max(rel)) < 1e-10


def test_tau_is_increasing_from_zero(reheating_bg) -> None:  # type: ignore[no-untyped-def]
    bg = reheating_bg
    assert bg.tau is not None and np.all(np.diff(bg.tau) > 0)
    assert bg.tau[0] == 0.0


def test_matter_domination_conformal_time_is_analytic() -> None:
    # Pure matter: H = H0 e^{−3N/2} ⇒ τ(N) = 2 (e^{N/2} − 1)/H0.
    rho0 = 3.0e-10
    bg = solve_background(BackgroundInputs(rho_phi_init=rho0, rho_r_init=0.0, Gamma_phi=0.0, N_final=5.0))
    H0 = np.sqrt(rho0 / 3.0)
    np.testing.assert_allclose(bg.tau, 2.0 * np.expm1(bg.N / 2.0) / H0, rtol=1e-9)


def test_tau_interpolants_agree_with_N_interpolants(reheating_bg) -> None:  # type: ignore[no-untyped-def]
    bg = reheating_bg
    np.testing.assert_allclose(bg.a_of_tau(bg.tau), np.exp(bg.N), rtol=1e-12)
    np.testing.assert_allclose(bg.H_of_tau(bg.tau), bg.H, rtol=1e-12)
    np.testing.assert_allclose(bg.rho_phi_of_tau(bg.tau), bg.rho_phi, rtol=1e-12, atol=1e-300)
    np.testing.assert_allclose(bg.rho_r_of_tau(bg.tau), bg.rho_r, rtol=1e-12, atol=1e-30)


def test_radiation_domination_conformal_time_is_analytic() -> None:
    # Pure radiation: H = H0 e^{−2N} ⇒ τ(N) = (e^N − 1)/H0 and a(τ) = 1 + H0 τ.
    rho0 = 3.0e-10
    bg = solve_background(BackgroundInputs(rho_phi_init=0.0, rho_r_init=rho0, Gamma_phi=0.0, N_final=5.0))
    H0 = np.sqrt(rho0 / 3.0)
    np.testing.assert_allclose(bg.tau, np.expm1(bg.N) / H0, rtol=1e-9)
    tau = np.linspace(bg.tau[0], bg.tau[-1], 777)
    np.testing.assert_allclose(bg.a_of_tau(tau), 1.0 + H0 * tau, rtol=1e-7)


def test_matter_dilutes_as_a_minus_3_without_decay() -> None:
    # Γ_φ = 0: ρ_φ ∝ a^{−3} exactly (a coefficient drift, e.g. −3 → −4, fails here).
    bg = solve_background(BackgroundInputs(rho_phi_init=1.0e-9, rho_r_init=0.0, Gamma_phi=0.0, N_final=5.0))
    np.testing.assert_allclose(bg.rho_phi, 1.0e-9 * np.exp(-3.0 * bg.N), rtol=1e-6)


def test_radiation_dilutes_as_a_minus_4() -> None:
    bg = solve_background(BackgroundInputs(rho_phi_init=0.0, rho_r_init=1.0e-9, Gamma_phi=0.0, N_final=5.0))
    np.testing.assert_allclose(bg.rho_r, 1.0e-9 * np.exp(-4.0 * bg.N), rtol=1e-6)


def test_reduced_planck_mass_constant() -> None:
    # M_Pl = (8πG)^{-1/2} = 2.435 × 10^18 GeV (PDG); guards against unit drift.
    assert M_PL_GEV == pytest.approx(2.435e18, rel=1e-3)
