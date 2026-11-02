"""M4 physical path (P1-04): canonical tensor modes → regularised n_L → n_L/s.

Kamada et al. (arXiv:2007.08029, "V3") and Maleknejad (arXiv:2412.09490,
"V4") write the anomaly source as a total derivative. With h_λ the tensor
mode (λ = +1 right, −1 left), z_λ² = a² Q_λ / 2 (V3 Eq. 3.20, M_Pl = 1) and

    B_λ(k, τ) ≡ λ k ( |h_λ′|² − k² |h_λ|² ),

V3 Eq. 2.28 is a⁴⟨RR̃⟩ = ∂_τ ∫ d³k/(2π)³ Σ_λ B_λ, and V4 Eq. 7 is the same
statement for the chiral gravitational charge, Δ𝒦 ∝ a⁻³ Σ_s s ∫ d³q q
(|∂_τ h|² − q²|h|²)|_{τ_in}^{τ}. The anomaly (V3 Eq. 2.24, V4 Eq. 1) then
gives the comoving lepton number (V3 Eq. 2.29)

    a_f³ n_L(τ_f) = N_{R−L} / (24 (4π)²) · ∫ d³k/(2π)³ Σ_λ [B_λ − B_λ^ad]_{τ_i}^{τ_f},

where B^ad is the adiabatic counterterm to ``ADIABATIC_ORDER`` (V3 Sec. 3.2,
``adiabatic.py``). This module evaluates it two ways on the same modes:

* **time integral** (V3 Eq. 2.24 integrated): the local density
  ∂_τ B_λ = λ k [ −4 (z′/z) |h′|² − 2 k² (1 + P/Q) Re(h h*′) ], from the
  mode equation (z² h′)′ + k² z² (P/Q) h = 0, is integrated along with the
  mode by the ODE solver from the mode's exact initial bracket. This is
  M4's ΔN_L;
* **boundary term** (V4 Eq. 7): B_λ − B_λ^ad at τ_end. This is the V4
  cross-check ``delta_Q_A_V4``.

The lower limit is τ_i → −∞ (V3 Eq. 2.29 with the vacuum in the far past):
there every mode is in the adiabatic vacuum and B − B^ad → 0. At a finite
start k/(aH) = x it is the order-6 tail ∝ 1/x of the vacuum bracket, which
the limit removes; dropping it, rather than subtracting its finite-x value,
makes the result independent of x (measured < 1e-5 between x = 100 and 200).

They are equal only if the mode equation's z″/z is the derivative of the
z′/z used in B, so the cross-check tests the background chain, not just
algebra. Both use V3's normalisation (Eq. 2.29); V4's Eq. 8 prints the
prefactor N_χ/(24·4π), which contradicts its own Eq. 1 (N_χ/(24(4π)²)), so
V4 contributes the functional form, not a constant.

Mode equation (V3 Eq. 2.14 with the Gauss–Bonnet sound speed of
``m7_infer/couplings.py``): u″ + [k² P/Q − z″/z] u = 0, u = z h,
Q_λ = 1 + δ_T − λ k g, P_λ = Q_λ + Δ. Unlike M3 (which integrates only the
coupling-induced part in a Minkowski basis), the GR term a″/a is included:
these are the physical tensor modes. Each mode starts in the adiabatic
(WKB) vacuum u = Ω^{−1/2} e^{−i∫Ω}, u′ = (−iΩ − Ω′/2Ω) u (V3 Eq. 3.14,
normalisation of Eq. 2.18) at k/(aH) = ``X_START`` ≫ 1, and is integrated
in e-folds N (d/dτ = aH d/dN) to the end of inflation, so no τ ↔ N
inversion enters.

Normalisation (the P1-04 gap the PHYS3 lane routed). Under a → c a,
τ → τ/c, k → c k (``A_END_H_END`` is such a convention): g → g/c, ℋ → c ℋ,
u → u/√c, z → c z, so B → B/c and ∫d³k B → c³ ∫d³k B, which cancels
a_f³: n_L is invariant. ``normalisation_residual`` re-runs this whole
module on the rescaled background and k-grid and reports
|Y_L(c)/Y_L − 1|.

Reheating. After inflation the inflaton oscillates (w = 0) until it decays
at T_reh: n_L a³ and ρ a³ are both conserved, so n_L/ρ is; at reheating
ρ = (π²/30) g_* T⁴ and s = (2π²/45) g_* T³ = (4/3) ρ/T, hence

    Y_L ≡ n_L/s = n_L(τ_end) · (3 T_reh / 4) / ρ_end = n_L(τ_end) T_reh / (4 H_end²),

with ρ_end = 3 H_end² (M_Pl = 1) from M2's trajectory and T_reh the run's
input. g_* cancels. Y_L is conserved afterwards; M5 converts it.

Band. The k-integral runs over the run's k-grid (the M3 grid). After the
fourth-order subtraction the V3 Eq. 3.21 Λ² and ln Λ terms remain, so the
band result is not cutoff-free; ``uv_band_sensitivity`` (the share of the
last ln k interval) reports how converged it is, and
``m7_infer.pipeline.eta_B_refusal`` refuses η_B above 0.5 %.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicSpline

from .adiabatic import ADIABATIC_ORDER, AdiabaticJ, Background, adiabatic_omega_parts

if TYPE_CHECKING:
    from ..m7_infer.couplings import CouplingArrays

# V3 Sec. 2.2: three left-handed leptons without light right-handed partners,
# N_{R−L} = −3 (V4's N_χ = N_L − N_R = +3 with the opposite sign convention).
N_R_MINUS_L = -3.0
# V3 Eq. 2.24 / 2.29 prefactor N_{R−L}/(24 (4π)²).
ANOMALY_PREFACTOR = N_R_MINUS_L / (24.0 * (4.0 * math.pi) ** 2)
# Adiabatic start: k/(aH) at τ_i (sub-horizon, k|τ| ≫ 1 in de Sitter).
X_START = 100.0
# ODE tolerances for the canonical modes.
MODE_RTOL = 1e-9


@dataclass
class TensorBackground:
    """The tensor-sector background as smooth functions of N (``CouplingArrays``).

    ``c`` applies the normalisation probe a → c a exactly: aH → c aH,
    g = f′/a² → g/c (f′ = dφ/dτ → c f′), δ_T and Δ unchanged.
    """

    arrays: CouplingArrays
    c: float = 1.0
    # One vector spline in N of [ln aH, ln a, g·a, δ_T, Δ] (c = 1); ln c is
    # added to the first two. g = f′/a² spans ~25 decades over the trajectory
    # (∝ 1/a), so the smooth g·a = f_φ H dφ/dN is splined instead.
    _s: CubicSpline = field(init=False, repr=False)
    _lnc: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        ar = self.arrays
        N = np.asarray(ar.N, dtype=float)
        a = np.asarray(ar.a, dtype=float)
        cols = np.column_stack([
            np.log(a * np.asarray(ar.H)), np.log(a), np.asarray(ar.g) * a,
            np.asarray(ar.delta_T), np.asarray(ar.Delta),
        ])
        self._s = CubicSpline(N, cols, axis=0)
        self._lnc = math.log(self.c)

    @property
    def N_end(self) -> float:
        return float(self.arrays.N[-1])

    @property
    def N_start(self) -> float:
        return float(self.arrays.N[0])

    def rescaled(self, c: float) -> TensorBackground:
        return TensorBackground(self.arrays, self.c * c)

    def N_at_horizon_ratio(self, k: float, x: float) -> float:
        """N where k/(aH) = x (aH grows while ε < 1)."""
        N = np.asarray(self.arrays.N, dtype=float)
        ln_aH = self._s(N)[:, 0] + self._lnc
        target = math.log(k / x)
        if target < ln_aH[0]:
            msg = (f"mode k = {k:.3g} has k/(aH) < {x:g} already at the trajectory start; "
                   "M4 cannot place it in the adiabatic vacuum")
            raise ValueError(msg)
        if target >= ln_aH[-1]:
            return float(N[-1])
        return float(np.interp(target, ln_aH, N))

    def values(self, N: float) -> tuple[float, ...]:
        """(a, ℋ, ℋ′, g, g′, g″, δ_T, δ_T′, δ_T″, Δ, Δ′, Δ″) at N (′ = d/dτ).

        τ-derivatives come from the same splines (y′ = aH y_N,
        y″ = aH (aH)_N y_N + (aH)² y_NN), so the mode equation's z″/z is the
        exact τ-derivative of the z′/z used in B (the V4 cross-check).
        g = (g a)/a with a ∝ e^N: g_N = ((ga)_N − ga)/a,
        g_NN = ((ga)_NN − 2(ga)_N + ga)/a; under a → c a, g → g/c.
        """
        y0, y1, y2 = self._s(N), self._s(N, 1), self._s(N, 2)
        aH = math.exp(float(y0[0]) + self._lnc)
        aH_N = aH * float(y1[0])
        a = math.exp(float(y0[1]) + self._lnc)
        ga, ga1, ga2 = float(y0[2]), float(y1[2]), float(y2[2])
        g, gN, gNN = ga / a, (ga1 - ga) / a, (ga2 - 2.0 * ga1 + ga) / a
        d2 = aH * aH_N
        a2 = aH * aH
        dT, dTN, dTNN = float(y0[3]), float(y1[3]), float(y2[3])
        Dl, DlN, DlNN = float(y0[4]), float(y1[4]), float(y2[4])
        return (a, aH, d2,
                g, aH * gN, d2 * gN + a2 * gNN,
                dT, aH * dTN, d2 * dTN + a2 * dTNN,
                Dl, aH * DlN, d2 * DlN + a2 * DlNN)

    _KEYS = ("a", "aH", "A2", "g", "g1", "g2", "dT", "dT1", "dT2", "Dl", "Dl1", "Dl2")

    def local(self, N: float) -> dict[str, float]:
        """:meth:`values` as a dict."""
        return dict(zip(self._KEYS, self.values(N), strict=True))

    def adiabatic_background(self, N: float) -> Background:
        v = self.local(N)
        return Background(
            a=v["a"], A=(v["aH"], v["A2"]),
            G=(v["g"], v["g1"], v["g2"]), E=(v["dT"], v["dT1"], v["dT2"]),
            C=(v["Dl"], v["Dl1"], v["Dl2"]),
        )


def _zero(v: dict[str, float], k: float) -> tuple[float, float, float, float, float]:
    """Parity-even (g = 0) coefficients: (Q₀, Z₀ = z′/z, R₀ = P/Q, ω₀², 1/z₀²)."""
    Q = 1.0 + v["dT"]
    Q1, Q2 = v["dT1"], v["dT2"]
    Z = v["aH"] + 0.5 * Q1 / Q
    zpp = v["A2"] + 0.5 * Q2 / Q - 0.5 * (Q1 / Q) ** 2 + Z * Z
    R = 1.0 + v["Dl"] / Q
    return Q, Z, R, k * k * R - zpp, 2.0 / (v["a"] ** 2 * Q)


def _first(v: dict[str, float], k: float) -> tuple[float, float, float]:
    """First order in the CS coupling, per unit λ (ε₁ = −k g): (δZ, δR, δ(z″/z))."""
    Q = 1.0 + v["dT"]
    Q1, Q2 = v["dT1"], v["dT2"]
    e0, e1, e2 = -k * v["g"], -k * v["g1"], -k * v["g2"]
    Z = v["aH"] + 0.5 * Q1 / Q
    dZ = 0.5 * e1 / Q - 0.5 * Q1 * e0 / Q**2
    dR = -v["Dl"] * e0 / Q**2
    dzpp = (0.5 * e2 / Q - 0.5 * Q2 * e0 / Q**2
            - (Q1 / Q) * (e1 / Q - Q1 * e0 / Q**2) + 2.0 * Z * dZ)
    return dZ, dR, dzpp


def boundary_bracket(h: complex, hp: complex, k: float, lam: float) -> float:
    """B_λ = λ k (|h′|² − k²|h|²): the per-mode integrand of V3 Eq. 2.28 and of
    V4 Eq. 7 (Δ𝒦 ∝ Σ_s s ∫d³q q (|∂_τ h|² − q²|h|²)|_{τ_in}^{τ})."""
    return lam * k * (abs(hp) ** 2 - k * k * abs(h) ** 2)


def _odd_bracket(h: complex, hp: complex, dh: complex, dhp: complex, k: float) -> float:
    """Σ_λ B_λ to first order in the CS coupling, h_λ = h₀ + λ δh:
    Σ_λ λ k (|h_λ′|² − k²|h_λ|²) = 4 k Re(h₀′* δh′ − k² h₀* δh)."""
    return 4.0 * k * ((hp.conjugate() * dhp).real - k * k * (h.conjugate() * dh).real)


@dataclass
class ModeAnomaly:
    """One k: helicity-summed boundary values and time integral (first order in g)."""

    k: float
    N_start: float
    S_start: float
    S_end: float
    integral: float          # ∫ dτ ∂_τ Σ_λ B_λ (V3 Eq. 2.24 integrated)
    h_end: complex = 0j      # h₀ (g = 0) at the end of inflation
    dh_end: complex = 0j     # δh (first-order CS response per unit λ) there


def _initial_state(bg: TensorBackground, k: float, N0: float,
                   order: int = ADIABATIC_ORDER) -> tuple[complex, complex, complex, complex]:
    """(h₀, h₀′, δh, δh′) of the adiabatic vacuum u = Ω^{−1/2} e^{−i∫Ω} (V3 Eq. 3.14), h = u/z.

    Ω is V3's adiabatic frequency to the subtraction order (Eq. 3.15, strict
    expansion, ``adiabatic.adiabatic_omega_parts``), split as Ω₀ + λ δΩ, so
    the exact mode starts in the vacuum whose bracket the counterterm
    subtracts: S − S^ad at the start then falls off with k/(aH) faster than
    the counterterm grows (a first-order WKB start leaves an O((aH/k)²)
    mismatch, which made the result depend on the start time).
    Ω′/Ω and (δΩ/Ω₀)′ are centred differences in N (d/dτ = aH d/dN).
    """
    def parts(N: float) -> tuple[float, float]:
        return adiabatic_omega_parts(order, k, bg.adiabatic_background(N))

    v0 = bg.local(N0)
    Q, Z, _, _, iz2 = _zero(v0, k)
    dZ = _first(v0, k)[0]
    Om, dOm = parts(N0)
    if Om <= 0.0:
        msg = f"mode k = {k:.3g} has no adiabatic vacuum at its start (Ω = {Om:.3g})"
        raise ValueError(msg)
    step = 1e-4
    lo = max(N0 - step, bg.N_start)
    hi = min(N0 + step, bg.N_end)
    (Op, dOp), (Omn, dOmn) = parts(hi), parts(lo)
    r = v0["aH"] * (math.log(Op) - math.log(Omn)) / (hi - lo)          # Ω₀′/Ω₀
    dr = v0["aH"] * (dOp / Op - dOmn / Omn) / (hi - lo)               # (δΩ/Ω₀)′
    u = 1.0 / math.sqrt(Om)
    up = (-1j * Om - 0.5 * r) * u
    du = -0.5 * (dOm / Om) * u
    dup = (-1j * dOm - 0.5 * dr) * u + (-1j * Om - 0.5 * r) * du
    s = math.sqrt(iz2)                                 # 1/z₀
    dlnz = 0.5 * (-k * v0["g"]) / Q                    # δz/z per unit λ
    h, hp = u * s, (up - Z * u) * s
    dh = (du - dlnz * u) * s
    dhp = (dup - dZ * u - Z * du) * s - dlnz * hp
    return h, hp, dh, dhp


def solve_mode(bg: TensorBackground, k: float, x_start: float = X_START,
               rtol: float = MODE_RTOL) -> ModeAnomaly:
    """Tensor mode k from k/(aH) = x_start to the end of inflation, in N.

    Integrates h₀ (g = 0) and its first-order CS response δh (h_λ = h₀ + λ δh):
        h₀″ = −2 Z₀ h₀′ − k² R₀ h₀,
        δh″ = −2 Z₀ δh′ − k² R₀ δh − 2 δZ h₀′ − k² δR h₀,
    with Z = z′/z, R = P/Q, and the helicity-summed anomaly density
        ∂_τ Σ_λ B_λ = 4k [ −4 Z₀ Re(h₀′*δh′) − k²(R₀+1) Re(h₀*δh′ + h₀′*δh)
                           − 2 δZ |h₀′|² − k² δR Re(h₀ h₀′*) ].
    The parity-odd sum is linear in g at first order, so it is obtained
    without the cancellation of two nearly equal helicities (for the
    Kawai–Kim fixture k g ~ 1e-12, below the ODE's relative tolerance).
    """
    N0 = bg.N_at_horizon_ratio(k, x_start)
    h, hp, dh, dhp = _initial_state(bg, k, N0)
    S0 = _odd_bracket(h, hp, dh, dhp, k)

    kk = k * k

    def rhs(N: float, y: NDArray[np.float64]) -> NDArray[np.float64]:
        (_, aH, A2, g, g1, g2, dT, dT1, dT2, Dl, _, _) = bg.values(N)
        Q = 1.0 + dT
        Z = aH + 0.5 * dT1 / Q
        R = 1.0 + Dl / Q
        e0, e1 = -k * g, -k * g1
        dZ = 0.5 * e1 / Q - 0.5 * dT1 * e0 / Q**2
        dR = -Dl * e0 / Q**2
        hr, hi, hpr, hpi, dhr, dhi, dhpr, dhpi = y[0], y[1], y[2], y[3], y[4], y[5], y[6], y[7]
        hppr = -2.0 * Z * hpr - kk * R * hr
        hppi = -2.0 * Z * hpi - kk * R * hi
        dhppr = -2.0 * Z * dhpr - kk * R * dhr - 2.0 * dZ * hpr - kk * dR * hr
        dhppi = -2.0 * Z * dhpi - kk * R * dhi - 2.0 * dZ * hpi - kk * dR * hi
        re_hp_dhp = hpr * dhpr + hpi * dhpi            # Re(h₀′* δh′)
        re_h_dhp = hr * dhpr + hi * dhpi               # Re(h₀* δh′)
        re_hp_dh = hpr * dhr + hpi * dhi               # Re(h₀′* δh)
        re_h_hp = hr * hpr + hi * hpi                  # Re(h₀ h₀′*)
        dS = 4.0 * k * (-4.0 * Z * re_hp_dhp - kk * (R + 1.0) * (re_h_dhp + re_hp_dh)
                        - 2.0 * dZ * (hpr * hpr + hpi * hpi) - kk * dR * re_h_hp)
        inv = 1.0 / aH
        return np.array([hpr * inv, hpi * inv, hppr * inv, hppi * inv,
                         dhpr * inv, dhpi * inv, dhppr * inv, dhppi * inv, dS * inv])

    y0 = np.array([h.real, h.imag, hp.real, hp.imag, dh.real, dh.imag, dhp.real, dhp.imag, 0.0])
    sh, shp = abs(h), abs(hp)
    sdh, sdhp = max(abs(dh), 1e-300), max(abs(dhp), 1e-300)
    atol = 1e-13 * np.array([sh, sh, shp, shp, sdh, sdh, sdhp, sdhp, max(abs(S0), 1e-300)])
    sol = solve_ivp(rhs, (N0, bg.N_end), y0, method="DOP853", rtol=rtol, atol=atol)
    if not sol.success:
        msg = f"tensor mode k = {k:.3g} failed: {sol.message}"
        raise RuntimeError(msg)
    yf = sol.y[:, -1]
    Sf = _odd_bracket(complex(yf[0], yf[1]), complex(yf[2], yf[3]),
                      complex(yf[4], yf[5]), complex(yf[6], yf[7]), k)
    return ModeAnomaly(k=k, N_start=N0, S_start=S0, S_end=Sf, integral=float(yf[8]),
                       h_end=complex(yf[0], yf[1]), dh_end=complex(yf[4], yf[5]))


@dataclass
class LeptonNumber:
    """M4's physical result for one run."""

    k: NDArray[np.float64]
    per_mode_time: NDArray[np.float64]       # Σ_λ (B(τ_i) + ∫∂_τB − B^ad(τ_end)) per k
    per_mode_boundary: NDArray[np.float64]   # Σ_λ (B − B^ad)(τ_end) per k (V4 Eq. 7)
    n_L_time: float                          # n_L(τ_end), time-integrated (V3 2.24)
    n_L_boundary: float                      # n_L(τ_end), boundary form (V4 Eq. 7)
    Y_L: float                               # n_L/s at reheating (time-integrated)
    Y_L_V4: float                            # n_L/s at reheating (boundary form)
    v4_rel_disagreement: float
    uv_band_sensitivity: float
    a_end: float
    H_end: float
    order: int = ADIABATIC_ORDER
    x_start: float = X_START


def _k_integral(k: NDArray[np.float64], per_mode: NDArray[np.float64]) -> float:
    """∫ d³k/(2π)³ = ∫ d ln k k³/(2π²), trapezoid on the run's log grid."""
    return float(np.trapezoid(k**3 * per_mode, np.log(k)) / (2.0 * math.pi**2))


def lepton_number(bg: TensorBackground, k: NDArray[np.float64], T_reh: float,
                  order: int = ADIABATIC_ORDER, x_start: float = X_START,
                  rtol: float = MODE_RTOL) -> LeptonNumber:
    """n_L at the end of inflation and Y_L = n_L/s at reheating (module docstring)."""
    k = np.asarray(k, dtype=float)
    J = AdiabaticJ(order)
    bg_end = bg.adiabatic_background(bg.N_end)
    Bad_end = J.integrand(k, bg_end)                   # Σ_λ B^ad at τ_end
    t_mode = np.empty_like(k)
    b_mode = np.empty_like(k)
    for i, kk in enumerate(k):
        m = solve_mode(bg, float(kk), x_start, rtol)
        # Lower limit τ_i → −∞ (V3 Eq. 2.29): there every mode is in the
        # adiabatic vacuum and S − S^ad → 0; at a finite start it is the
        # order-6 tail ∝ aH/k, which the τ_i → −∞ limit removes. So the
        # boundary form is S(τ_end) − S^ad(τ_end), and the time-integrated
        # form starts from the exact initial bracket.
        b_mode[i] = m.S_end - float(Bad_end[i])
        t_mode[i] = (m.S_start + m.integral) - float(Bad_end[i])
    a_end = bg_end.a
    H_end = bg_end.A[0] / a_end
    pref = ANOMALY_PREFACTOR / a_end**3
    nt = pref * _k_integral(k, t_mode)
    nb = pref * _k_integral(k, b_mode)
    dil = T_reh / (4.0 * H_end**2)
    v4 = abs(nt - nb) / abs(nb) if nb != 0.0 else (0.0 if nt == 0.0 else math.inf)
    if len(k) > 2 and nt != 0.0:
        uv = abs(nt - pref * _k_integral(k[:-1], t_mode[:-1])) / abs(nt)
    else:
        uv = 0.0 if nt == 0.0 else math.inf
    return LeptonNumber(
        k=k, per_mode_time=t_mode, per_mode_boundary=b_mode, n_L_time=nt, n_L_boundary=nb,
        Y_L=nt * dil, Y_L_V4=nb * dil, v4_rel_disagreement=float(v4),
        uv_band_sensitivity=float(uv), a_end=a_end, H_end=H_end, order=order, x_start=x_start,
    )
