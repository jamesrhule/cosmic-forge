"""Physical Chern–Simons and Gauss–Bonnet couplings for M3 (P1-03).

Replaces the schematic ``A``/``B`` lambdas in ``pipeline.py``.

Model and conventions (reduced Planck units, M_Pl = 1)
-------------------------------------------------------
    S = ∫d⁴x √−g [ R/2 − ½(∂φ)² − V(φ) − ½ ξ(φ) R²_GB + L_CS ],

with the parity-odd Chern–Simons term normalised so that, for tensor
helicities λ = ±1 (right/left), the quadratic tensor action is

    S_T = Σ_λ (1/8) ∫dτ d³k a² [ (G_T − λ k g) |h′_λ|²
                                 − (F_T − λ k g) k² |h_λ|² ],
    g ≡ f′(τ)/a²,  f′ = df/dτ.

The Gauss–Bonnet coefficients follow from mapping ξ(φ)R²_GB onto the
Horndeski functions (G₂…G₅) and the general tensor action
S_T = (1/8)∫dt d³x a³[𝒢_T ḣ² − ℱ_T (∂h)²/a²]:

    G_T = 1 − 4 H ξ̇,   F_T = 1 − 4 ξ̈   (cosmic-time dots).

The CS normalisation above is a *definition* of f's normalisation (the
standard z_λ = a√(1 − λ k f′/a²) form). Kawai & Kim (arXiv:1702.07689)
use this action. Their equation numbers could not be checked here: the
paper is unreachable from the build sandbox. This derivation is
therefore recorded as an OPEN-WITH-GAP item, not a verified port
(docs/build/evidence/P1-03.md).

Canonical mode and first-order coefficients
-------------------------------------------
With u_λ = z_λ h_λ, z_λ² = a² Q_λ / 4, Q_λ = G_T − λ k g,
P_λ = F_T − λ k g, the mode equation is
u″ + [k² P_λ/Q_λ − z_λ″/z_λ] u = 0. To first order in the couplings
(δ ≡ G_T − 1, Δ ≡ F_T − G_T, k g all ≪ 1):

    ω_λ² = k² (1 + C) + A_λ k + B   (− a″/a, see below)
    C   = Δ = −4 (ξ̈ − H ξ̇)
    B   = −(½ δ″ + ℋ δ′)
    A_λ = λ (½ g″ + ℋ g′)

The pure-GR −a″/a term is *not* in B. M3 integrates the
coupling-induced deviation in its Minkowski/WKB basis, so F_GB = |β|²
measures coupling-induced mixing, as in the original M3 design.
Including −a″/a needs the M3 basis change tracked with P1-04/P1-07.

In e-folds (′ = aH d/dN, ℋ = aH, ε = −Ḣ/H²) both B and A_λ use the
same operator 𝒪[y] ≡ ½y″ + ℋy′ = a²H² [ ½ y_NN + ½(3 − ε) y_N ]:

    δ = −4 H ξ̇ = −4 ξ_φ H² x,          x = dφ/dN,
    g = f′/a² = f_φ H x / a,
    ξ̈ = ξ_φφ H² x² + ξ_φ H² (x_N − ε x).

Coupling functions (model assumption, documented): ξ(φ) = ξ·φ and
f(φ) = θ_grav·φ/f̂_a, with f̂_a = f_a / M_Pl (f_a in GeV in RunConfig).
GB is parity-even (B, C helicity-independent); CS is parity-odd
(A_+ = −A_−). θ_grav → −θ_grav therefore swaps the helicities exactly.

Time normalisation
------------------
M3 integrates on τ ∈ [−5, τ_end] with τ_end ∈ {−1, −0.1, −1e-3}.
Inflation ends at N_end (ε = 1). The scale factor is normalised so that
a_end H_end = 10³, and τ(N) = −1/(a_end H_end) − ∫_N^{N_end} dN′/(aH).
With this, τ ≈ −1/(aH): τ = −1e-3 is the end of inflation, and
τ = −5 is ≈ 8.5 e-folds earlier, so M3's window covers the last
e-folds of inflation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import CubicSpline

from ..domain import Couplings, Potential
from ..m1_background.background import M_PL_GEV
from ..m2_scalar import compile_potential
from ..m2_scalar.trajectory import Trajectory, solve_trajectory

A_END_H_END = 1.0e3


def initial_field(pot: Potential) -> float:
    """Starting φ (M_Pl) for an inflationary trajectory of this potential.

    Per kind (documented choices, overridable via ``params['phi0']``):
    starobinsky: φ₀ = 5.5 (≈ 60 e-folds); natural: φ₀ = π f (1 − 10⁻⁶),
    just off the hilltop; hilltop: φ₀ = 10⁻³ μ; custom: needs
    ``params['phi0']``.
    """
    if "phi0" in pot.params:
        return float(pot.params["phi0"])
    if pot.kind == "starobinsky":
        return 5.5
    if pot.kind == "natural":
        return float(np.pi * pot.params.get("f_a", 1.0) * (1.0 - 1.0e-6))
    if pot.kind == "hilltop":
        return 1.0e-3 * float(pot.params.get("mu", 1.0))
    msg = "custom potentials need params['phi0'] (initial inflaton value, M_Pl units)"
    raise ValueError(msg)


@dataclass
class CouplingProfile:
    """A_±(τ), B(τ), C(τ) and a(τ) on M3's conformal-time axis."""

    tau: NDArray[np.float64]
    A_plus: NDArray[np.float64]
    B: NDArray[np.float64]
    C: NDArray[np.float64]
    a: NDArray[np.float64]
    trajectory: Trajectory
    N_end: float
    _A: CubicSpline
    _B: CubicSpline
    _C: CubicSpline
    _lna: CubicSpline

    def A_of_tau(self, tau: float) -> NDArray[np.float64]:
        v = float(self._A(tau))
        return np.array([+v, -v])

    def B_of_tau(self, tau: float) -> NDArray[np.float64]:
        v = float(self._B(tau))
        return np.array([v, v])

    def C_of_tau(self, tau: float) -> NDArray[np.float64]:
        v = float(self._C(tau))
        return np.array([v, v])

    def a_of_tau(self, tau: float) -> float:
        return float(np.exp(self._lna(tau)))


def _op(y: NDArray[np.float64], N: NDArray[np.float64], aH: NDArray[np.float64],
        eps: NDArray[np.float64]) -> NDArray[np.float64]:
    """𝒪[y] = ½y″ + ℋy′ = a²H² [½ y_NN + ½(3 − ε) y_N] (spline derivatives in N)."""
    s = CubicSpline(N, y)
    return aH**2 * (0.5 * s(N, 2) + 0.5 * (3.0 - eps) * s(N, 1))


def coupling_profile(pot: Potential, couplings: Couplings, tau_start: float = -5.0) -> CouplingProfile:
    """Build the physical coupling profile for one RunConfig."""
    model = compile_potential(pot)
    params = dict(pot.params)
    tr = solve_trajectory(model, params, initial_field(pot), N_after_end=0.0, n_out=20001)
    if tr.N_end_inflation is None:
        msg = "potential did not end inflation within N_max; cannot place M3's window"
        raise ValueError(msg)
    N_end = tr.N_end_inflation
    m = tr.N <= N_end
    N, H, x, xN, eps = tr.N[m], tr.H[m], tr.dphi_dN[m], tr.d2phi_dN2[m], tr.epsilon[m]
    a = (A_END_H_END / H[-1]) * np.exp(N - N[-1])
    aH = a * H

    # τ(N) = −1/(a_end H_end) − ∫_N^{N_end} dN′/(aH).
    # Accumulate the tail ∫_N^{N_end} from the end (no cancellation).
    inv = 1.0 / aH
    seg = 0.5 * (inv[1:] + inv[:-1]) * np.diff(N)
    tail = np.concatenate([np.cumsum(seg[::-1])[::-1], [0.0]])
    tau = -1.0 / A_END_H_END - tail
    if tau[0] > tau_start:
        msg = f"trajectory covers τ ≥ {tau[0]:.3g} only; M3 needs τ ≥ {tau_start}"
        raise ValueError(msg)

    # Coupling functions ξ(φ) = ξ φ, f(φ) = θ_grav φ / f̂_a (linear ⇒ ξ_φφ = 0).
    xi_phi = float(couplings.xi)
    f_hat = float(couplings.f_a) / M_PL_GEV
    f_phi = float(couplings.theta_grav) / f_hat

    delta = -4.0 * xi_phi * H**2 * x                      # G_T − 1
    xi_dd = xi_phi * H**2 * (xN - eps * x)                 # ξ̈ (ξ_φφ = 0)
    xi_d = xi_phi * H * x                                  # ξ̇
    Cv = -4.0 * (xi_dd - H * xi_d)                         # F_T − G_T
    Bv = -_op(delta, N, aH, eps)
    g = f_phi * H * x / a
    Ap = _op(g, N, aH, eps)                                # A_+ (A_− = −A_+)

    keep = tau >= tau_start - 1.0
    t = tau[keep]
    return CouplingProfile(
        tau=t, A_plus=Ap[keep], B=Bv[keep], C=Cv[keep], a=a[keep], trajectory=tr, N_end=N_end,
        _A=CubicSpline(t, Ap[keep]), _B=CubicSpline(t, Bv[keep]), _C=CubicSpline(t, Cv[keep]),
        _lna=CubicSpline(t, np.log(a[keep])),
    )


__all__ = ["A_END_H_END", "CouplingProfile", "coupling_profile", "initial_field"]
