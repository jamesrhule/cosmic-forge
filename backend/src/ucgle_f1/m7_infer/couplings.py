"""Physical Chern–Simons and Gauss–Bonnet couplings for M3 (P1-03).

This is the pipeline's default coupling model (LEDGER, JAMES DECISION 11).
The original schematic ``A``/``B`` lambdas stay available in ``pipeline.py``
as ``coupling_model="schematic"``, for diagnostics only: with f_a in M_Pl
its CS term is a constant ±θ_grav/f̂_a that drives one helicity unstable
for UI-scale couplings (``RunPipeline.coupling_model``).

Units
-----
Reduced Planck units throughout (M_Pl = 2.4352e18 GeV = 1, ``M_PL_GEV``;
the LEDGER's "2.44e18" is the same constant to three figures). GeV
appears only at the API/UI boundary: ``RunConfig.couplings.f_a`` is in GeV
and is converted here with ``M_PL_GEV``. The potential's parameters
arrive in API units too (natural ``f`` and hilltop ``mu`` in GeV) and are
converted once by ``Potential.engine()`` (W1-PARAMS). φ is the inflaton
(Kawai & Kim, arXiv:1702.07689, Eq. 2: "an axion field φ (identified as
the inflaton)").

Model and conventions
---------------------
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

Mapping to Kawai & Kim's normalisation (LEDGER, JAMES DECISION 11)
------------------------------------------------------------------
Kawai & Kim write the gravitational couplings as

    −(1/16) ξ_KK(φ) R²_GB + (1/16) ϑ(φ) R R̃,
    ξ_KK(φ) = −δ ln[2 e^φ η⁴(i e^φ)],  δ = −1,      ϑ(φ) = γ φ,  γ = 1,

with η the Dedekind eta function. Term by term:

* GB. −½ ξ(φ) R²_GB ≡ −(1/16) ξ_KK(φ) R²_GB  ⇔  ξ(φ) = ξ_KK(φ)/8. Then
  G_T = 1 − ½ H ξ̇_KK, the Satoh–Soda form (arXiv:0806.4594) that Kawai
  & Kim use. Only ξ̇ and ξ̈ enter, so only ξ_KK′ and ξ_KK″ matter:
  ξ_KK′(φ) = −δ [1 − (π/3) e^φ E₂(i e^φ)], with E₂ the weight-2
  Eisenstein series (d ln η(τ)/dτ = (iπ/12) E₂(τ)).
* CS. With the same reduction, (1/16) ϑ R R̃ gives
  z_λ² ∝ a² (1 − λ k ϑ′/(2a²)), so f(φ) = ϑ(φ)/2 = γ φ/2 in the
  normalisation above.

UCGLE-F1 keeps its own coupling parameters (Decision 11). They map onto
Kawai & Kim as follows:

* ``xi`` (dimensionless): UCGLE-F1's coupling function is linear,
  ξ(φ) = xi·φ, so xi plays the role of ξ_KK′(φ)/8 over M3's window.
  The linear model has ξ_φφ = 0, so it does not carry Kawai & Kim's
  ξ_KK″ term. This is a model difference, not a fit: no value of xi is
  derived from δ.
* ``theta_grav`` (dimensionless) and ``f_a`` (GeV at the API, f̂_a =
  f_a/M_PL_GEV here): f(φ) = theta_grav·φ/f̂_a, so Kawai & Kim's γ = 1
  corresponds to theta_grav/f̂_a = γ/2 = 1/2.
* ``M_star``, ``M1`` (GeV) and ``S_E2`` (dimensionless): the EFT cutoff,
  the lightest right-handed neutrino mass and the sphaleron coefficient
  of the boxed F1 estimate. They do not enter the tensor action, so they
  have no counterpart in −(1/16)ξ_KK R²_GB + (1/16)ϑ RR̃, and the M1–M6
  chain does not read them.

Kawai & Kim's equation numbers (beyond Eq. 2 above) could not be
checked: arXiv is unreachable from the build sandbox. The coefficient
mapping above is the one Decision 11 records.

Canonical mode and first-order coefficients
-------------------------------------------
With u_λ = z_λ h_λ, z_λ² = a² Q_λ / 4, Q_λ = G_T − λ k g,
P_λ = F_T − λ k g, the mode equation is
u″ + [k² P_λ/Q_λ − z_λ″/z_λ] u = 0. To first order in the couplings
(δ_T ≡ G_T − 1, Δ ≡ F_T − G_T, k g all ≪ 1):

    ω_λ² = k² (1 + C) + A_λ k + B   (− a″/a, see below)
    C   = Δ = −4 (ξ̈ − H ξ̇)
    B   = −(½ δ_T″ + ℋ δ_T′)
    A_λ = λ (½ g″ + ℋ g′)

The pure-GR −a″/a term is *not* in B. M3 integrates the
coupling-induced deviation in its Minkowski/WKB basis, so F_GB = |β|²
measures coupling-induced mixing, as in the original M3 design.
Including −a″/a needs the M3 basis change tracked with P1-04/P1-07.

In e-folds (′ = aH d/dN, ℋ = aH, ε = −Ḣ/H²) both B and A_λ use the
same operator 𝒪[y] ≡ ½y″ + ℋy′ = a²H² [ ½ y_NN + ½(3 − ε) y_N ]:

    δ_T = −4 H ξ̇ = −4 ξ_φ H² x,          x = dφ/dN,
    g = f′/a² = f_φ H x / a,
    ξ̈ = ξ_φφ H² x² + ξ_φ H² (x_N − ε x).

GB is parity-even (B, C helicity-independent); CS is parity-odd
(A_+ = −A_−). θ_grav → −θ_grav therefore swaps the helicities exactly.

Time normalisation: ``A_END_H_END`` (a convention, not physics)
---------------------------------------------------------------
The overall normalisation of a is a gauge freedom. Under
a → c a (so ℋ → c ℋ, τ → τ/c, k → c k) the coefficients scale as
B → c² B, A_λ k → c² A_λ k and C → C, so ω_λ² τ² and every |β|² are
unchanged: only k/(a H) is physical. ``A_END_H_END`` is a normalisation
CONVENTION, set by one condition taken from the code's own τ grid: the
end of inflation (ε = 1) is the last point of M3's high-precision
window, τ(N_end) = ``M3_TAU_END["high"]`` = −10⁻³. Since
τ(N) = −1/(a_end H_end) − ∫_N^{N_end} dN′/(aH), this gives

    a_end H_end = −1 / M3_TAU_END["high"] = 10³.

Within M3 it fixes the unit of the comoving k (M3's k = 1 is the mode
with k/(a_end H_end) = 10⁻³). It does NOT cancel downstream:

* M4's ΔN_L, and so the raw η_B, scale linearly with it (ΔN_L ∝ c under
  a → c a; ``m4_anomaly/anomaly.py`` measures this on every run as
  ``normalisation_residual``, and ``pipeline.eta_B_refusal`` refuses η_B
  until P1-04 matches a, or a·T, to reheating so ΔN_L is invariant);
* M6's placeholder f_Hz = 1e-19·k inherits the k unit (``m6_gw/sgwb.py``);
* with M3's τ and k grids fixed, which modes are sub- or super-horizon at
  τ_start and τ_end depends on it (below).

Grids. The τ and k grids are the pipeline's (pre-existing) M3 design; they
are not taken from the paper. A Bunch–Davies start needs k|τ_start| ≫ 1
for every mode; with τ_start = −5 that holds only for k ≫ 0.2, so on the
``fast`` grid (k ∈ [0.1, 10]) the two lowest modes start with k|τ| < 1,
and on ``high`` (k ∈ [10⁻³, 10³]) 25 of 64 do. Choosing grids with
k_min|τ_start| ≫ 1 changes every frozen-audit number and is P1-04/P1-07
work (LEDGER routing from W1 PHYS3).

Where the window sits (computed on M2's trajectory with this
normalisation, e-folds before ε = 1): τ = −5 / −1 / −0.1 are
10.06 / 8.35 / 5.84 for the Kawai–Kim natural benchmark (f_a = 8.7),
9.17 / 7.54 / 5.19 for Starobinsky M = 10⁻⁵ and 9.19 / 7.58 / 5.26 for
natural f_a = 1, Λ = 10⁻³. The de Sitter estimate ln(−10³τ) gives
8.52 / 6.91 / 4.61, which undershoots because aH is not constant.
``tests/unit/test_couplings.py`` checks the window condition and the
gauge scaling of the coefficients.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import CubicSpline

from ..domain import Couplings, Potential
from ..m1_background.background import M_PL_GEV
from ..m2_scalar import compile_potential
from ..m2_scalar.natural import KK_N_E, natural_phi_star
from ..m2_scalar.trajectory import Trajectory, solve_trajectory

# M3's conformal-time window (pipeline τ-grid): start, and end per precision.
M3_TAU_START: float = -5.0
M3_TAU_END: dict[str, float] = {"fast": -1.0, "standard": -1.0e-1, "high": -1.0e-3}
# Normalisation convention (module docstring): the end of inflation is the
# last point of the high-precision window, τ(N_end) = −1/(a_end H_end) =
# M3_TAU_END["high"]. |β|² is independent of it; M4's ΔN_L (and so the raw
# η_B) and M6's placeholder f_Hz are not, which M4 must undo (P1-04).
A_END_H_END: float = -1.0 / M3_TAU_END["high"]


def initial_field(pot: Potential) -> float:
    """Starting φ (M_Pl) for an inflationary trajectory of this potential.

    Per kind (documented choices, overridable via ``params['phi0']``):
    starobinsky: φ₀ = 5.5 (≈ 60 e-folds); hilltop: φ₀ = 10⁻³ μ; custom:
    needs ``params['phi0']``.

    natural: the slow-roll pivot φ_*(N_e = 60), the benchmark's N_e
    (m2_scalar/natural.py), but never closer to the hilltop than
    π f_a (1 − 10⁻⁶). For super-Planckian f_a (the Kawai–Kim f_a = 8.7)
    this is the pivot; for f_a ≲ 1, where slow roll fails near the
    hilltop and φ_*(60) lies within 10⁻¹³ of π f_a, the hilltop bound
    applies, as before.
    """
    pot = pot.engine()  # M2's units (no-op for a converted potential)
    if "phi0" in pot.params:
        return float(pot.params["phi0"])
    if pot.kind == "starobinsky":
        return 5.5
    if pot.kind == "natural":
        f_a = float(pot.params.get("f_a", 1.0))
        return min(natural_phi_star(f_a, KK_N_E), float(np.pi * f_a * (1.0 - 1.0e-6)))
    if pot.kind == "hilltop":
        return 1.0e-3 * float(pot.params.get("mu", 1.0))
    msg = "custom potentials need params['phi0'] (initial inflaton value, M_Pl units)"
    raise ValueError(msg)


@dataclass(frozen=True)
class CouplingArrays:
    """The tensor-sector background on the whole inflationary trajectory (N ≤ N_end).

    The un-truncated inputs of :class:`CouplingProfile`, kept for M4's
    canonical tensor modes (P1-04): conformal time τ, a, H, ε, and the
    coupling functions of the module docstring, δ_T = G_T − 1, Δ = F_T − G_T
    (= C) and g = f′/a² (CS; Kamada et al. 2007.08029 Eq. 3.20 write
    z² ∝ a²(1 − λ k f′/a²), i.e. Q_λ = 1 + δ_T − λ k g).
    """

    N: NDArray[np.float64]
    tau: NDArray[np.float64]
    a: NDArray[np.float64]
    H: NDArray[np.float64]
    eps: NDArray[np.float64]
    delta_T: NDArray[np.float64]
    Delta: NDArray[np.float64]
    g: NDArray[np.float64]
    a_end_H_end: float


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
    # P1-04: the full-window arrays M4 builds its tensor background from.
    arrays: CouplingArrays | None = None

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


def coupling_profile(
    pot: Potential,
    couplings: Couplings,
    tau_start: float = M3_TAU_START,
    *,
    a_end_H_end: float = A_END_H_END,
) -> CouplingProfile:
    """Build the physical coupling profile for one RunConfig.

    ``a_end_H_end`` is exposed only so the gauge scaling in the module
    docstring can be tested; the pipeline always uses ``A_END_H_END``.
    """
    pot = pot.engine()  # M2's units (no-op for a converted potential)
    model = compile_potential(pot)
    params = dict(pot.params)
    tr = solve_trajectory(model, params, initial_field(pot), N_after_end=0.0, n_out=20001)
    if tr.N_end_inflation is None:
        msg = "potential did not end inflation within N_max; cannot place M3's window"
        raise ValueError(msg)
    N_end = tr.N_end_inflation
    m = tr.N <= N_end
    N, H, x, xN, eps = tr.N[m], tr.H[m], tr.dphi_dN[m], tr.d2phi_dN2[m], tr.epsilon[m]
    a = (a_end_H_end / H[-1]) * np.exp(N - N[-1])
    aH = a * H

    # τ(N) = −1/(a_end H_end) − ∫_N^{N_end} dN′/(aH).
    # Accumulate the tail ∫_N^{N_end} from the end (no cancellation).
    inv = 1.0 / aH
    seg = 0.5 * (inv[1:] + inv[:-1]) * np.diff(N)
    tail = np.concatenate([np.cumsum(seg[::-1])[::-1], [0.0]])
    tau = -1.0 / a_end_H_end - tail
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
        arrays=CouplingArrays(N=N, tau=tau, a=a, H=H, eps=eps, delta_T=delta, Delta=Cv, g=g,
                              a_end_H_end=float(a_end_H_end)),
    )


__all__ = [
    "A_END_H_END",
    "CouplingArrays",
    "M3_TAU_END",
    "M3_TAU_START",
    "CouplingProfile",
    "coupling_profile",
    "initial_field",
]
