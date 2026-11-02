"""⟨R R̃⟩ integrator and ΔN_L accumulator.

Legacy proxy (schematic path only, below):
  ⟨R R̃⟩(τ) = (1/4π²) ∫ d³k/(2π)³ k/a⁴ Δ_chirality(τ, k)
  Δ_chirality(τ, k) = k(|β_+|² − |β_-|²)   (no subtraction: ``_adiabatic_subtraction`` ≡ 0)
  ΔN_L(T_reh) = (1/16π²) ∫ dτ a³ ⟨R R̃⟩(τ) / (T_reh³)
and its V4 "cross-check" is an unnormalised Ω_gw^± indicator. The physical
path (``physical.py``, ``adiabatic.py``) replaces both on the default
coupling model.

Units (LEDGER, JAMES DECISION 11): reduced-Planck throughout. M3's k,
τ and a, and so the source ∫dτ a³⟨RR̃⟩, are in M_Pl units, and
``AnomalyInputs.T_reh`` is in M_Pl too; the pipeline converts the API's
``reheating.T_reh_GeV`` with ``M_PL_GEV`` at the boundary. (Until W1
PHYS3 M4 divided the M_Pl-unit source by T_reh in GeV³, which is off
by M_PL_GEV³ ≈ 1.44e55.)

Two paths (P1-04):

* **physical** (``AnomalyInputs.background`` set; the pipeline's default
  ``coupling_model="physical"``): ``physical.py``. Canonical tensor modes
  on M2's inflationary background, V3's ⟨RR̃⟩ (Eq. 2.28) with the
  adiabatic subtraction to ``adiabatic.ADIABATIC_ORDER`` (Sec. 3.2),
  n_L(τ_end) from V3 Eq. 2.29, and ΔN_L ≡ Y_L = n_L/s at reheating. The V4
  cross-check (Eq. 7, boundary form) is ``delta_Q_A_V4``. ΔN_L is
  invariant under a → c·a, k → c·k, τ → τ/c; ``normalisation_residual``
  re-runs the whole path on the rescaled background and k-grid.
* **legacy** (no background: the diagnostic ``coupling_model="schematic"``):
  the pre-P1-04 proxy below, with no subtraction. It is not invariant
  (ΔN_L ∝ c under a → c·a: the integrand k³(|β₊|² − |β₋|²) a⁻⁴ against
  a³ dτ scales as c³·c⁻⁴·c⁻¹·c³ = c), reports
  ``adiabatic_subtraction_implemented = False``, and η_B is refused on it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import quad as scipy_quad

from ..m3_modes import ChiralModeResult
from . import physical as _phys
from .adiabatic import ADIABATIC_ORDER

# 2π² reduced Planck mass^3, etc. We keep everything in M_Pl units.


# Probe factor for the normalisation check (any c ≠ 1 works: the current
# source is exactly linear in c, an invariant one is independent of it).
NORMALISATION_PROBE_C = 10.0

# P1-04: V3's adiabatic subtraction (2007.08029 Sec. 3.2) is implemented in
# ``adiabatic.py`` and applied by the physical path (``physical.py``). Each
# AnomalyResult reports whether *its* ⟨RR̃⟩ had it applied: True on the
# physical path, False on the legacy proxy (``_adiabatic_subtraction`` below
# is still the zero placeholder there), and ``eta_B_refusal`` refuses η_B
# when it is False.
ADIABATIC_SUBTRACTION_IMPLEMENTED = True


@dataclass
class AnomalyInputs:
    tau_grid: NDArray[np.float64]
    a_of_tau: Callable[[float], float]   # scale factor a(τ)
    modes: ChiralModeResult
    T_reh: float                         # reheating temperature, M_Pl units
    cross_check_V4: bool = True
    # P1-04: the tensor-sector background (``CouplingProfile.arrays``). Set →
    # physical path; None → legacy proxy (no subtraction, η_B refused).
    background: object | None = None


@dataclass
class AnomalyResult:
    # Legacy: ⟨RR̃⟩(τ) on M3's τ grid. Physical (P1-04): the per-k regularised
    # source k³Σ_λ[B − B^ad](τ_end)/(2π²) on the run's k grid.
    rr_dual: NDArray[np.float64]
    delta_N_L: float                      # final asymmetry at T_reh
    delta_Q_A_V4: float | None            # cross-check from V4
    # Legacy: trapezoid vs quad of the proxy. Physical (P1-04, S6): the
    # start-time sensitivity |Y(k/aH = 100) − Y(50)| / |Y|.
    adiabatic_residual: float
    # P1-04 quadrature cross-check of the k-integral: mpmath.quad at 30
    # digits vs scipy.integrate.quad on the same interpolated integrand.
    quad_rel_disagreement: float = float("nan")
    quad_flag: bool = False               # True when disagreement > 1e-8
    # |ΔN_L(a → c·a) / ΔN_L(a) − 1| (module docstring). 0 for a physical
    # (normalisation-invariant) ΔN_L; c − 1 for the current M4 (P1-04).
    normalisation_residual: float = float("nan")
    # Whether this run's ⟨RR̃⟩ had V3's adiabatic subtraction applied (True
    # only on the physical path). Defaults to False: fail closed.
    adiabatic_subtraction_implemented: bool = False
    # Physical path only (NaN on the legacy path; ``eta_B_refusal`` fails closed):
    # |time-integrated − boundary| / |boundary| (V3 Eq. 2.24 vs V4 Eq. 7);
    v4_rel_disagreement: float = float("nan")
    # share of n_L from the last ln k interval of the run's k band (UV convergence);
    uv_band_sensitivity: float = float("nan")
    # n_L at the end of inflation (M_Pl³) and the subtraction order used.
    n_L_end: float = float("nan")
    adiabatic_order: int = 0


def _chirality_density(res: ChiralModeResult) -> NDArray[np.float64]:
    """(|h_+|² − |h_-|²) integrand, mapped to |β|² difference.

    After horizon exit the canonical modes satisfy
        |h_σ|² = |α_σ + β_σ|² / (2k)
    so a clean helicity asymmetry proxy is (|β_+|² − |β_-|²) × k.
    """
    return res.k * (np.abs(res.beta_plus) ** 2 - np.abs(res.beta_minus) ** 2)


def _adiabatic_subtraction(k: NDArray[np.float64]) -> NDArray[np.float64]:
    """Minimal subtraction constant: zero at leading adiabatic order.

    The gravitational anomaly integrand is finite after the parity-odd
    projection, so the minimal subtraction reduces to a counterterm
    that vanishes for the helicity-asymmetric combination. We keep
    this hook in place so users can override the scheme. It is not V3's
    adiabatic subtraction (P1-04): ``ADIABATIC_SUBTRACTION_IMPLEMENTED``
    stays False until it is, and η_B is refused meanwhile.
    """
    return np.zeros_like(k)


def rr_dual_density(res: ChiralModeResult) -> NDArray[np.float64]:
    """⟨R R̃⟩ integrand as a function of k (per-mode contribution)."""
    integrand = _chirality_density(res) - _adiabatic_subtraction(res.k)
    # d³k/(2π)³ → (k²/2π²) in isotropic gauge, so multiply by that factor.
    return (res.k**2 / (2.0 * np.pi**2)) * integrand


QUAD_FLAG_THRESHOLD = 1e-8


def quad_cross_check(log_k: NDArray[np.float64], per_mode: NDArray[np.float64]) -> tuple[float, bool]:
    """Integrate the per-mode integrand over log k with mpmath (dps 30) and scipy.

    Both integrate the same piecewise-linear interpolant (``np.interp``
    semantics), with mpmath split at every node so each sub-interval is
    smooth. Returns (relative disagreement, flag); flag is True above
    :data:`QUAD_FLAG_THRESHOLD` (P1-04).
    """
    import mpmath as mp

    xs = [float(v) for v in log_k]
    ys = [float(v) for v in per_mode]

    def interp(x: float) -> float:
        return float(np.interp(x, xs, ys))

    s_val, _ = scipy_quad(interp, xs[0], xs[-1], points=xs[1:-1] if len(xs) > 2 else None,
                          limit=max(50, 4 * len(xs)), epsabs=0.0, epsrel=1e-13)
    with mp.workdps(30):
        def f(x: object) -> object:
            xf = mp.mpf(x)
            i = int(np.clip(np.searchsorted(xs, float(xf)) - 1, 0, len(xs) - 2))
            x0, x1 = mp.mpf(xs[i]), mp.mpf(xs[i + 1])
            y0, y1 = mp.mpf(ys[i]), mp.mpf(ys[i + 1])
            return y0 + (y1 - y0) * (xf - x0) / (x1 - x0)
        m_val = mp.quad(f, xs)
    m_float = float(m_val)
    denom = max(abs(m_float), 1e-300)
    rel = abs(s_val - m_float) / denom if m_float != 0.0 or s_val != 0.0 else 0.0
    return float(rel), bool(rel > QUAD_FLAG_THRESHOLD)


def _source(
    tau_grid: NDArray[np.float64],
    a_of_tau: Callable[[float], float],
    modes: ChiralModeResult,
) -> tuple[NDArray[np.float64], float]:
    """⟨RR̃⟩(τ) and the leptogenesis source ∫dτ a³⟨RR̃⟩ (M_Pl units)."""
    per_mode = rr_dual_density(modes)
    log_k = np.log(modes.k)

    # Integrate over log k using trapezoid (the integrand peaks near
    # horizon-crossing modes and falls off exponentially either side).
    rr_of_tau = np.empty_like(tau_grid)
    for i, tau in enumerate(tau_grid):
        a_tau = a_of_tau(float(tau))
        rr_of_tau[i] = np.trapezoid(per_mode / a_tau**4, log_k)

    # Time integral ∫ dτ a³ ⟨RR̃⟩ — the leptogenesis source.
    a3 = np.array([a_of_tau(float(t)) ** 3 for t in tau_grid])
    return rr_of_tau, float(np.trapezoid(a3 * rr_of_tau, tau_grid))


def _rescaled(modes: ChiralModeResult, c: float) -> ChiralModeResult:
    """The same Bogoliubov coefficients on the comoving grid k → c·k."""
    return replace(modes, k=c * modes.k)


def normalisation_residual(inp: AnomalyInputs, c: float = NORMALISATION_PROBE_C) -> float:
    """|ΔN_L(a → c·a) / ΔN_L(a) − 1| on the same M3 output (module docstring).

    Re-runs :func:`_source` with τ → τ/c, a(τ) → c·a(c·τ) and k → c·k;
    |β|² is unchanged under that rescaling (``m7_infer/couplings.py``). A
    zero source on both sides is invariant (residual 0).
    """
    _, s1 = _source(inp.tau_grid, inp.a_of_tau, inp.modes)
    _, sc = _source(inp.tau_grid / c, lambda t: c * inp.a_of_tau(c * t), _rescaled(inp.modes, c))
    if s1 == 0.0:
        return 0.0 if sc == 0.0 else float("inf")
    return float(abs(sc / s1 - 1.0))


def delta_N_L(inp: AnomalyInputs) -> AnomalyResult:
    if inp.background is not None:
        return _physical_delta_N_L(inp)
    return _legacy_delta_N_L(inp)


def _physical_delta_N_L(inp: AnomalyInputs) -> AnomalyResult:
    """P1-04 physical path (``physical.py``): ΔN_L = Y_L = n_L/s at reheating."""
    bg = _phys.TensorBackground(inp.background)  # type: ignore[arg-type]
    k = np.asarray(inp.modes.k, dtype=float)
    res = _phys.lepton_number(bg, k, inp.T_reh)
    # Start-time sensitivity: the same modes started at half the k/(aH).
    half = _phys.lepton_number(bg, k, inp.T_reh, x_start=0.5 * _phys.X_START)
    if res.Y_L != 0.0:
        adiabatic_residual = abs(half.Y_L / res.Y_L - 1.0)
    else:
        adiabatic_residual = 0.0 if half.Y_L == 0.0 else float("inf")
    log_k = np.log(k)
    per_mode = k**3 * res.per_mode_time
    try:
        qrel, qflag = quad_cross_check(log_k, per_mode)
    except Exception:  # noqa: BLE001 — telemetry must not fail the run
        qrel, qflag = float("nan"), True
    c = NORMALISATION_PROBE_C
    resc = _phys.lepton_number(bg.rescaled(c), c * k, inp.T_reh)
    if res.Y_L != 0.0:
        norm = abs(resc.Y_L / res.Y_L - 1.0)
    else:
        norm = 0.0 if resc.Y_L == 0.0 else float("inf")
    return AnomalyResult(
        # Per-k regularised source k³ Σ_λ[B − B^ad](τ_end)/(2π²) on the run's
        # k-grid (the integrand of n_L over ln k), not a τ series.
        rr_dual=per_mode / (2.0 * np.pi**2),
        delta_N_L=float(res.Y_L),
        delta_Q_A_V4=float(res.Y_L_V4) if inp.cross_check_V4 else None,
        adiabatic_residual=float(adiabatic_residual),
        quad_rel_disagreement=qrel,
        quad_flag=qflag,
        normalisation_residual=float(norm),
        adiabatic_subtraction_implemented=True,
        v4_rel_disagreement=float(res.v4_rel_disagreement),
        uv_band_sensitivity=float(res.uv_band_sensitivity),
        n_L_end=float(res.n_L_time),
        adiabatic_order=ADIABATIC_ORDER,
    )


def _legacy_delta_N_L(inp: AnomalyInputs) -> AnomalyResult:
    """Pre-P1-04 proxy (legacy/schematic path): no subtraction, not invariant."""
    per_mode = rr_dual_density(inp.modes)
    log_k = np.log(inp.modes.k)
    rr_of_tau, source = _source(inp.tau_grid, inp.a_of_tau, inp.modes)
    dNL = source / (16.0 * np.pi**2 * inp.T_reh**3)

    # V4 cross-check: same integrand reparametrized via ΔQ_A from Ω_gw^±.
    dQA = _v4_cross_check(inp.modes) if inp.cross_check_V4 else None

    # Adiabatic-scheme residual = fractional disagreement between
    # minimal subtraction and the adiabatic-k² integrator (which we
    # can compute independently via scipy.integrate.quad on the
    # interpolated integrand).
    try:
        integrand_interp = lambda lk: np.interp(  # noqa: E731
            lk, log_k, per_mode
        )
        adiabatic_int, _ = scipy_quad(
            integrand_interp,
            float(log_k[0]),
            float(log_k[-1]),
            epsabs=1e-12,
            epsrel=1e-10,
        )
        minimal_int = np.trapezoid(per_mode, log_k)
        denom = abs(adiabatic_int) + 1e-300
        residual = abs(minimal_int - adiabatic_int) / denom
    except Exception:  # noqa: BLE001 — resilient telemetry
        residual = float("nan")

    try:
        qrel, qflag = quad_cross_check(log_k, per_mode)
    except Exception:  # noqa: BLE001 — telemetry must not fail the run
        qrel, qflag = float("nan"), True

    return AnomalyResult(
        rr_dual=rr_of_tau,
        delta_N_L=float(dNL),
        delta_Q_A_V4=dQA,
        adiabatic_residual=float(residual),
        quad_rel_disagreement=qrel,
        quad_flag=qflag,
        normalisation_residual=normalisation_residual(inp),
        adiabatic_subtraction_implemented=False,
    )


def _v4_cross_check(res: ChiralModeResult) -> float:
    """ΔQ_A = ∫ dq/q × q² (Ω_gw^+ − Ω_gw^-) / (2π)  [V4 Eq. 11].

    We identify Ω_gw^σ ∝ k⁴ |h_σ|² after horizon exit; the ratio is
    scheme-independent, so the numeric prefactor drops out and we
    return a dimensionless indicator that should equal ``delta_N_L``
    up to overall normalisation.
    """
    k = res.k
    Om_plus = k**4 * (np.abs(res.alpha_plus) ** 2 + np.abs(res.beta_plus) ** 2)
    Om_minus = k**4 * (np.abs(res.alpha_minus) ** 2 + np.abs(res.beta_minus) ** 2)
    integrand = (Om_plus - Om_minus) * k
    return float(np.trapezoid(integrand, np.log(k)) / (2.0 * np.pi))
