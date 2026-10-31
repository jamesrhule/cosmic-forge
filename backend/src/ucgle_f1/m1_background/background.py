"""Friedmann background solver.

Equations (in reduced Planck units, M_Pl = 1):

    dρ_φ/dN = −3 ρ_φ − Γ_φ ρ_φ / H
    dρ_r/dN = −4 ρ_r + Γ_φ ρ_φ / H
    H² = (ρ_φ + ρ_r) / 3

with ``N = ln a`` as the independent variable. The solver returns an
interpolant over ``N ∈ [N_end_inflation, N_final]`` that later modules
query through the :class:`Background` API.

Conformal time (P1-01). With ``a = a₀ eᴺ`` (``a₀ = 1`` at the start of
the integration, N = 0) and ``dτ = dt / a = dN / (a H)``,

    τ(N) = τ₀ + ∫₀ᴺ dN' e^{−N'} / H(N'),

integrated with its own tight-tolerance ODE on the dense Friedmann
solution (so the ρ solution itself is not perturbed). ``τ₀ = 0`` marks
the start of the integration window; only differences of τ are
physical. ``τ(N)`` is strictly increasing (H > 0), so ``N(τ)`` is its
exact inverse, evaluated by Newton iteration on the τ(N) spline.
Interpolants in τ: a(τ), H(τ), ρ_φ(τ), ρ_r(τ) (``CubicSpline`` on the
τ nodes of the N grid).
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
    # Conformal time (P1-01). Optional so callers that construct a
    # Background by hand keep working; solve_background always fills them.
    tau: NDArray[np.float64] | None = None
    _tau_of_N_spline: CubicSpline | None = None
    _a_of_tau_spline: CubicSpline | None = None
    _H_of_tau_spline: CubicSpline | None = None
    _rho_phi_of_tau_spline: CubicSpline | None = None
    _rho_r_of_tau_spline: CubicSpline | None = None

    def H_of_N(self, N: float | NDArray[np.float64]) -> NDArray[np.float64]:
        return np.asarray(self._H_spline(N))

    def rho_phi_of_N(self, N: float | NDArray[np.float64]) -> NDArray[np.float64]:
        return np.asarray(self._rho_phi_spline(N))

    def rho_r_of_N(self, N: float | NDArray[np.float64]) -> NDArray[np.float64]:
        return np.asarray(self._rho_r_spline(N))

    # ── conformal time (P1-01) ─────────────────────────────────────
    def _require_tau(self) -> None:
        if self._tau_of_N_spline is None:
            msg = "Background has no conformal-time interpolants (build it with solve_background)"
            raise ValueError(msg)

    def tau_of_N(self, N: float | NDArray[np.float64]) -> NDArray[np.float64]:
        """Conformal time τ(N) (M_Pl⁻¹, τ = 0 at N = 0)."""
        self._require_tau()
        assert self._tau_of_N_spline is not None
        return np.asarray(self._tau_of_N_spline(N))

    def N_of_tau(self, tau: float | NDArray[np.float64]) -> NDArray[np.float64]:
        """Inverse of :meth:`tau_of_N`: Newton iteration on the τ(N) spline.

        τ(N) is strictly increasing, so the root is unique; the initial
        guess comes from linear interpolation of the node table and the
        iteration uses the spline's analytic derivative dτ/dN = e^{−N}/H.
        """
        self._require_tau()
        assert self._tau_of_N_spline is not None and self.tau is not None
        t = np.atleast_1d(np.asarray(tau, dtype=np.float64))
        n = np.interp(t, self.tau, self.N)
        dspl = self._tau_of_N_spline.derivative()
        for _ in range(60):
            step = (self._tau_of_N_spline(n) - t) / dspl(n)
            n = np.clip(n - step, self.N[0], self.N[-1])
            if np.all(np.abs(step) <= 1e-15 * np.maximum(1.0, np.abs(n))):
                break
        return n if np.ndim(tau) else n.reshape(())

    def a_of_tau(self, tau: float | NDArray[np.float64]) -> NDArray[np.float64]:
        """Scale factor a(τ) (a = 1 at τ = 0)."""
        self._require_tau()
        assert self._a_of_tau_spline is not None
        return np.asarray(self._a_of_tau_spline(tau))

    def H_of_tau(self, tau: float | NDArray[np.float64]) -> NDArray[np.float64]:
        """Hubble rate H(τ) (cosmic-time H, M_Pl units)."""
        self._require_tau()
        assert self._H_of_tau_spline is not None
        return np.asarray(self._H_of_tau_spline(tau))

    def rho_phi_of_tau(self, tau: float | NDArray[np.float64]) -> NDArray[np.float64]:
        self._require_tau()
        assert self._rho_phi_of_tau_spline is not None
        return np.asarray(self._rho_phi_of_tau_spline(tau))

    def rho_r_of_tau(self, tau: float | NDArray[np.float64]) -> NDArray[np.float64]:
        self._require_tau()
        assert self._rho_r_of_tau_spline is not None
        return np.asarray(self._rho_r_of_tau_spline(tau))

    def T_reh_GeV(self) -> float:
        """Temperature at which ρ_r first dominates ρ_φ."""
        idx = int(np.argmax(self.rho_r >= self.rho_phi))
        if idx == 0:
            return float(self.T[0]) * M_PL_GEV
        return float(self.T[idx]) * M_PL_GEV


_RHO_FLOOR: Final[float] = 1e-300


def _rhs_log(
    _N: float,
    y: NDArray[np.float64],
    Gamma_phi: float,
    phi_on: bool,
    rad_on: bool,
) -> NDArray[np.float64]:
    """Friedmann system in y = (ln ρ_φ, ln ρ_r).

    d ln ρ_φ/dN = −3 − Γ_φ / H
    d ln ρ_r/dN = −4 + Γ_φ (ρ_φ/ρ_r) / H
    Working in logarithms gives uniform *relative* accuracy while the
    densities fall by tens of orders of magnitude (P1-01 found the linear
    form with ``atol = 1e-12`` drifting by ~25 % after five e-folds once
    ρ ≪ atol). A component that is identically zero is frozen out.
    """
    rho_phi = np.exp(y[0]) if phi_on else 0.0
    rho_r = np.exp(y[1]) if rad_on else 0.0
    H = np.sqrt(max(rho_phi + rho_r, 1e-300) / 3.0)
    dphi = (-3.0 - Gamma_phi / H) if phi_on else 0.0
    drad = (-4.0 + Gamma_phi * np.exp(y[0] - y[1]) / H) if (rad_on and phi_on) else (-4.0 if rad_on else 0.0)
    return np.array([dphi, drad])


def solve_background(inp: BackgroundInputs) -> Background:
    """Integrate the coupled reheating + radiation Friedmann system."""
    if inp.rho_phi_init < 0 or inp.rho_r_init < 0:
        raise ValueError("energy densities must be non-negative")
    phi_on = inp.rho_phi_init > 0.0
    # Radiation is evolved if present initially or sourced by decay.
    rad_on = inp.rho_r_init > 0.0 or (phi_on and inp.Gamma_phi > 0.0)
    if not (phi_on or rad_on):
        raise ValueError("at least one energy density must be positive")
    y0 = np.array([
        np.log(inp.rho_phi_init) if phi_on else 0.0,
        np.log(max(inp.rho_r_init, _RHO_FLOOR)) if rad_on else 0.0,
    ])
    span = (0.0, inp.N_final)
    args = (inp.Gamma_phi, phi_on, rad_on)

    sol = solve_ivp(
        _rhs_log,
        span,
        y0,
        method=inp.method,
        args=args,
        rtol=inp.rtol,
        atol=inp.atol,
        dense_output=True,
        max_step=0.01,
    )

    if not sol.success:
        # Retry with stiff solver (Radau) on failure.
        sol = solve_ivp(
            _rhs_log,
            span,
            y0,
            method="Radau",
            args=args,
            rtol=inp.rtol,
            atol=inp.atol,
            dense_output=True,
        )
        if not sol.success:
            raise RuntimeError(f"Friedmann solver failed: {sol.message}")

    def _rho(n: float | NDArray[np.float64]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        ly = np.asarray(sol.sol(n))
        rp = np.exp(ly[0]) if phi_on else np.zeros_like(ly[0])
        rr = np.exp(ly[1]) if rad_on else np.zeros_like(ly[1])
        return rp, rr

    N_grid = np.linspace(0.0, inp.N_final, 4001)
    rho_phi, rho_r = _rho(N_grid)
    H = np.sqrt(np.maximum(rho_phi + rho_r, 1e-300) / 3.0)
    # T from ρ_r = (π²/30) g_* T⁴ :
    T = (30.0 * np.maximum(rho_r, 0.0) / (np.pi**2 * G_STAR_SM)) ** 0.25

    # ── conformal time (P1-01): dτ/dN = e^{−N} / H(N) on the dense solution.
    def _dtau_dN(n: float, _y: NDArray[np.float64]) -> NDArray[np.float64]:
        rp, rr = _rho(n)
        h = np.sqrt(max(float(rp + rr), 1e-300) / 3.0)
        return np.array([np.exp(-n) / h])

    tsol = solve_ivp(
        _dtau_dN, span, np.array([0.0]), method="DOP853",
        t_eval=N_grid, rtol=1e-13, atol=1e-16,
    )
    if not tsol.success:
        raise RuntimeError(f"conformal-time quadrature failed: {tsol.message}")
    tau = np.asarray(tsol.y[0])
    a = np.exp(N_grid)

    return Background(
        N=N_grid,
        H=H,
        rho_phi=rho_phi,
        rho_r=rho_r,
        T=T,
        _H_spline=CubicSpline(N_grid, H),
        _rho_phi_spline=CubicSpline(N_grid, rho_phi),
        _rho_r_spline=CubicSpline(N_grid, rho_r),
        tau=tau,
        _tau_of_N_spline=CubicSpline(N_grid, tau),
        _a_of_tau_spline=CubicSpline(tau, a),
        _H_of_tau_spline=CubicSpline(tau, H),
        _rho_phi_of_tau_spline=CubicSpline(tau, rho_phi),
        _rho_r_of_tau_spline=CubicSpline(tau, rho_r),
    )
