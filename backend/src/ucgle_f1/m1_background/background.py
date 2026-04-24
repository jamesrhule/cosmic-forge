"""Friedmann background solver.

Equations (in reduced Planck units, M_Pl = 1):

    dρ_φ/dN = −3 ρ_φ − Γ_φ ρ_φ / H
    dρ_r/dN = −4 ρ_r + Γ_φ ρ_φ / H
    H² = (ρ_φ + ρ_r) / 3

with ``N = ln a`` as the independent variable. The solver returns an
interpolant over ``N ∈ [N_end_inflation, N_final]`` that later modules
query through the :class:`Background` API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicSpline

# Reduced Planck mass in GeV — astropy.cosmology constants would add a
# heavy import for a single number; keep this as a named constant.
M_PL_GEV: Final[float] = 2.4352e18
G_STAR_SM: Final[float] = 106.75  # SM relativistic d.o.f. above EW scale


@dataclass(frozen=True)
class BackgroundInputs:
    """Inputs for :func:`solve_background`."""

    rho_phi_init: float          # initial scalar energy density  (M_Pl^4)
    rho_r_init: float            # initial radiation energy density
    Gamma_phi: float             # scalar decay rate              (M_Pl)
    N_final: float = 30.0        # how far in e-folds to integrate
    rtol: float = 1e-10
    atol: float = 1e-12
    method: str = "LSODA"


@dataclass
class Background:
    """Evaluated background: interpolants over e-fold number N."""

    N: NDArray[np.float64]
    H: NDArray[np.float64]
    rho_phi: NDArray[np.float64]
    rho_r: NDArray[np.float64]
    T: NDArray[np.float64]
    _H_spline: CubicSpline
    _rho_phi_spline: CubicSpline
    _rho_r_spline: CubicSpline

    def H_of_N(self, N: float | NDArray[np.float64]) -> NDArray[np.float64]:
        return np.asarray(self._H_spline(N))

    def rho_phi_of_N(self, N: float | NDArray[np.float64]) -> NDArray[np.float64]:
        return np.asarray(self._rho_phi_spline(N))

    def rho_r_of_N(self, N: float | NDArray[np.float64]) -> NDArray[np.float64]:
        return np.asarray(self._rho_r_spline(N))

    def T_reh_GeV(self) -> float:
        """Temperature at which ρ_r first dominates ρ_φ."""
        idx = int(np.argmax(self.rho_r >= self.rho_phi))
        if idx == 0:
            return float(self.T[0]) * M_PL_GEV
        return float(self.T[idx]) * M_PL_GEV


def _rhs(
    _N: float,
    y: NDArray[np.float64],
    Gamma_phi: float,
) -> NDArray[np.float64]:
    rho_phi, rho_r = y
    # Floor to avoid H = 0 at the very tail.
    H = np.sqrt(max(rho_phi + rho_r, 1e-300) / 3.0)
    dphi = -3.0 * rho_phi - Gamma_phi * rho_phi / H
    drad = -4.0 * rho_r + Gamma_phi * rho_phi / H
    return np.array([dphi, drad])


def solve_background(inp: BackgroundInputs) -> Background:
    """Integrate the coupled reheating + radiation Friedmann system."""
    y0 = np.array([inp.rho_phi_init, inp.rho_r_init])
    span = (0.0, inp.N_final)

    sol = solve_ivp(
        _rhs,
        span,
        y0,
        method=inp.method,
        args=(inp.Gamma_phi,),
        rtol=inp.rtol,
        atol=inp.atol,
        dense_output=True,
        max_step=0.01,
    )

    if not sol.success:
        # Retry with stiff solver (Radau) on failure.
        sol = solve_ivp(
            _rhs,
            span,
            y0,
            method="Radau",
            args=(inp.Gamma_phi,),
            rtol=inp.rtol,
            atol=inp.atol,
            dense_output=True,
        )
        if not sol.success:
            raise RuntimeError(f"Friedmann solver failed: {sol.message}")

    N_grid = np.linspace(0.0, inp.N_final, 4001)
    rho_phi = np.asarray(sol.sol(N_grid)[0])
    rho_r = np.asarray(sol.sol(N_grid)[1])
    H = np.sqrt(np.maximum(rho_phi + rho_r, 1e-300) / 3.0)
    # T from ρ_r = (π²/30) g_* T⁴ :
    T = (30.0 * np.maximum(rho_r, 0.0) / (np.pi**2 * G_STAR_SM)) ** 0.25

    return Background(
        N=N_grid,
        H=H,
        rho_phi=rho_phi,
        rho_r=rho_r,
        T=T,
        _H_spline=CubicSpline(N_grid, H),
        _rho_phi_spline=CubicSpline(N_grid, rho_phi),
        _rho_r_spline=CubicSpline(N_grid, rho_r),
    )
