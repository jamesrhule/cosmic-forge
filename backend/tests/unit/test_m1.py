"""M1 Friedmann background tests."""

from __future__ import annotations

import numpy as np

from ucgle_f1.m1_background import BackgroundInputs, solve_background


def test_background_runs_and_is_monotone() -> None:
    bg = solve_background(BackgroundInputs(
        rho_phi_init=1.0e-9, rho_r_init=1.0e-20, Gamma_phi=1.0e-6,
    ))
    assert bg.H.shape == bg.N.shape
    # H(N) is non-increasing in an expanding universe with dilution.
    assert np.all(np.diff(bg.H) <= 1.0e-9)
    # ρ_r rises until reheating completes, then falls.
    argmax = int(np.argmax(bg.rho_r))
    assert 0 < argmax < len(bg.rho_r) - 1


def test_t_reh_positive() -> None:
    bg = solve_background(BackgroundInputs(
        rho_phi_init=1.0e-9, rho_r_init=1.0e-20, Gamma_phi=1.0e-6,
    ))
    assert bg.T_reh_GeV() > 0
