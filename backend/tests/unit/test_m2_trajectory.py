"""P1-02: Klein–Gordon trajectory of φ (m2_scalar/trajectory.py)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.integrate import cumulative_trapezoid

from ucgle_f1.domain import Potential
from ucgle_f1.m1_background import BackgroundInputs, solve_background
from ucgle_f1.m2_scalar import compile_potential
from ucgle_f1.m2_scalar.trajectory import (
    pytransport_available,
    solve_trajectory,
    solve_trajectory_on_background,
    solve_trajectory_pytransport,
)

QUADRATIC = Potential(kind="custom", customPython="m**2*phi**2/2", params={"m": 1.0e-6})
PARAMS = {"m": 1.0e-6}


@pytest.fixture(scope="module")
def quad_model():  # type: ignore[no-untyped-def]
    return compile_potential(QUADRATIC)


def test_slow_roll_limit_quadratic_to_1e_6(quad_model) -> None:  # type: ignore[no-untyped-def]
    # Deep slow roll (ε = 2/φ² ≈ 2.2e-7): the numerical attractor must match
    # the analytic slow-roll solution dφ/dN = −2/φ, φ² = φ0² − 4N to 1e-6.
    phi0 = 3000.0
    tr = solve_trajectory(quad_model, PARAMS, phi0, N_max=1.0)
    assert tr.N_end_inflation is None
    x_sr = -2.0 / tr.phi
    assert float(np.max(np.abs(tr.dphi_dN / x_sr - 1.0))) < 1e-6
    N = tr.N[1:]
    dphi2 = (phi0**2 - tr.phi[1:] ** 2) / (4.0 * N)
    assert float(np.max(np.abs(dphi2 - 1.0))) < 1e-6


def test_end_of_inflation_and_reheating_stage_quadratic(quad_model) -> None:  # type: ignore[no-untyped-def]
    phi0 = 16.0
    tr = solve_trajectory(quad_model, PARAMS, phi0, N_after_end=4.0)
    assert tr.stages == ["inflation:DOP853", "reheating:Radau"]
    assert tr.N_end_inflation is not None
    # Inflation ends exactly where ε = x²/2 reaches 1 …
    # (linear interpolation on the 4001-point output grid limits this to ~1e-3)
    assert float(np.interp(tr.N_end_inflation, tr.N, tr.epsilon)) == pytest.approx(1.0, abs=1e-3)
    # … which is after the slow-roll estimate (ε_V = 2/φ² = 1 at φ = √2,
    # N_sr = (φ0² − 2)/4) but within the last ~1.5 e-folds where slow roll fails.
    n_sr = (phi0**2 - 2.0) / 4.0
    assert n_sr < tr.N_end_inflation < n_sr + 1.5
    # Oscillation-averaged ρ_φ = 3H² redshifts like matter (a^{-3}) after inflation.
    mask = tr.N > tr.N_end_inflation + 1.0
    scaled = 3.0 * tr.H[mask] ** 2 * np.exp(3.0 * (tr.N[mask] - tr.N_end_inflation))
    first = scaled[: len(scaled) // 3].mean()
    last = scaled[-len(scaled) // 3 :].mean()
    assert last == pytest.approx(first, rel=0.1)


def test_conformal_derivatives_match_numerical_tau_derivative(quad_model) -> None:  # type: ignore[no-untyped-def]
    tr = solve_trajectory(quad_model, PARAMS, 16.0, N_max=10.0, n_out=20001)
    a = tr.a()
    tau = cumulative_trapezoid(1.0 / (a * tr.H), tr.N, initial=0.0)
    num = np.gradient(tr.phi, tau)
    np.testing.assert_allclose(tr.dphi_dtau()[5:-5], num[5:-5], rtol=1e-4)
    num2 = np.gradient(tr.dphi_dtau(), tau)
    np.testing.assert_allclose(tr.d2phi_dtau2()[5:-5], num2[5:-5], rtol=1e-3)


def test_test_field_on_m1_background(quad_model) -> None:  # type: ignore[no-untyped-def]
    bg = solve_background(BackgroundInputs(rho_phi_init=1.0e-9, rho_r_init=1.0e-20, Gamma_phi=1.0e-6, N_final=3.0))
    tr = solve_trajectory_on_background(quad_model, PARAMS, bg, phi0=1.0e-3, dphi_dN0=0.0)
    assert tr.stages == ["background:Radau"]
    assert np.all(np.isfinite(tr.phi)) and tr.phi.shape == bg.N.shape
    # m ≫ H: a test field oscillates; its envelope decays (Hubble friction).
    assert np.max(np.abs(tr.phi[-400:])) < np.max(np.abs(tr.phi[:400]))


def test_pytransport_is_a_soft_import() -> None:
    if pytransport_available():
        pytest.skip("PyTransport installed")
    with pytest.raises(ImportError, match="PyTransport 3.0 is not installed"):
        solve_trajectory_pytransport()
