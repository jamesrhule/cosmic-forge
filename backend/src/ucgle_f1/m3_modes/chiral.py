"""Chiral tensor mode solver with Bogoliubov tracking.

Conventions
-----------
τ              conformal time (units: M_Pl⁻¹)
h_σ(τ, k)      canonically-normalised helicity mode, σ ∈ {+1, −1}
ω²_σ(τ, k) ≡  k² + A_σ(τ) k + B_σ(τ)

The CS (Chern-Simons) contribution enters linearly in k and flips
sign with helicity; the GB (Gauss-Bonnet) contribution enters as a
helicity-independent correction to the ``B`` term.

The transient GB amplification factor F_GB is defined as
F_GB(k) = |β_k|² after the horizon exit, averaged across helicities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

# High-precision unitarity check threshold (S3).
# Default target (``precision='high'``). The pipeline scales this by
# precision level so ``standard`` and ``fast`` modes don't trigger the
# mpmath escalation on every oscillatory solve.
_UNITARITY_TOL = 1e-12


@dataclass
class ChiralSpectrumInputs:
    """Background + coupling inputs for the chiral mode ODE."""

    tau_grid: NDArray[np.float64]
    # A_σ and B_σ are callables of τ returning a length-2 array
    # [A_+(τ), A_-(τ)] / [B_+(τ), B_-(τ)].
    A: Callable[[float], NDArray[np.float64]]
    B: Callable[[float], NDArray[np.float64]]
    k_modes: NDArray[np.float64]
    rtol: float = 1e-10
    atol: float = 1e-12
    use_diffrax: bool = True
    # Escalate to mpmath when the measured drift exceeds this. The
    # pipeline passes a relaxed threshold for ``standard``/``fast``
    # precision; ``high`` keeps the spec default of 1e-12.
    unitarity_tol: float = _UNITARITY_TOL


@dataclass
class ChiralModeResult:
    k: NDArray[np.float64]
    alpha_plus: NDArray[np.complex128]
    beta_plus: NDArray[np.complex128]
    alpha_minus: NDArray[np.complex128]
    beta_minus: NDArray[np.complex128]
    unitarity_drift: NDArray[np.float64]  # per-mode max |α|²−|β|²−1|

    def F_GB_per_mode(self) -> NDArray[np.float64]:
        """Helicity-averaged |β|² — the transient amplification factor."""
        return 0.5 * (np.abs(self.beta_plus) ** 2 + np.abs(self.beta_minus) ** 2)

    def F_GB_integrated(self) -> float:
        """Log-k integrated F_GB — the summary scalar F_GB used by M4."""
        per_mode = self.F_GB_per_mode()
        lk = np.log(self.k)
        return float(np.trapezoid(per_mode, lk))


def _omega_sq(
    tau: float,
    k: float,
    A: Callable[[float], NDArray[np.float64]],
    B: Callable[[float], NDArray[np.float64]],
) -> NDArray[np.float64]:
    """Return ω²_σ for σ = (+, -)."""
    Av = A(tau)
    Bv = B(tau)
    return k * k + Av * k + Bv


def _ode_rhs(
    tau: float,
    y: NDArray[np.complex128],
    k: float,
    A: Callable[[float], NDArray[np.float64]],
    B: Callable[[float], NDArray[np.float64]],
) -> NDArray[np.complex128]:
    """Second-order → first-order: y = [h_+, h_+', h_-, h_-']."""
    omg2 = _omega_sq(tau, k, A, B)
    return np.array(
        [y[1], -omg2[0] * y[0], y[3], -omg2[1] * y[2]],
        dtype=np.complex128,
    )


def _initial_bunch_davies(k: float) -> NDArray[np.complex128]:
    """Standard Bunch-Davies vacuum at large |k τ|."""
    h0 = 1.0 / np.sqrt(2.0 * k)
    hp0 = -1j * np.sqrt(k / 2.0)
    return np.array([h0, hp0, h0, hp0], dtype=np.complex128)


def _bogoliubov(
    h: complex,
    hp: complex,
    k: float,
) -> tuple[complex, complex]:
    """Extract (α, β) from (h, h') assuming a WKB-like basis."""
    # h = (α e^{-ikτ} + β e^{+ikτ}) / sqrt(2k)
    # h' = -ik (α e^{-ikτ} - β e^{+ikτ}) / sqrt(2k)
    sk = np.sqrt(2.0 * k)
    alpha = 0.5 * (sk * h + 1j / np.sqrt(2.0 / k) * hp)
    beta = 0.5 * (sk * h - 1j / np.sqrt(2.0 / k) * hp)
    return complex(alpha), complex(beta)


def solve_chiral_modes(inp: ChiralSpectrumInputs) -> ChiralModeResult:
    tau_span = (float(inp.tau_grid[0]), float(inp.tau_grid[-1]))

    alphas_p = np.empty_like(inp.k_modes, dtype=np.complex128)
    betas_p = np.empty_like(inp.k_modes, dtype=np.complex128)
    alphas_m = np.empty_like(inp.k_modes, dtype=np.complex128)
    betas_m = np.empty_like(inp.k_modes, dtype=np.complex128)
    drifts = np.empty_like(inp.k_modes, dtype=np.float64)

    if inp.use_diffrax:
        try:
            return _solve_with_diffrax(inp)
        except ImportError:
            pass  # fall through to scipy

    for i, k in enumerate(inp.k_modes):
        y0 = _initial_bunch_davies(float(k))
        # scipy's LSODA / Radau do not accept complex y0; we use DOP853,
        # which supports complex states natively.
        sol = solve_ivp(
            _ode_rhs,
            tau_span,
            y0,
            method="DOP853",
            t_eval=inp.tau_grid,
            args=(float(k), inp.A, inp.B),
            rtol=inp.rtol,
            atol=inp.atol,
        )
        if not sol.success:
            raise RuntimeError(f"Chiral ODE failed at k={k}: {sol.message}")

        h_plus_final = complex(sol.y[0, -1])
        hp_plus_final = complex(sol.y[1, -1])
        h_minus_final = complex(sol.y[2, -1])
        hp_minus_final = complex(sol.y[3, -1])

        a_p, b_p = _bogoliubov(h_plus_final, hp_plus_final, float(k))
        a_m, b_m = _bogoliubov(h_minus_final, hp_minus_final, float(k))

        alphas_p[i] = a_p
        betas_p[i] = b_p
        alphas_m[i] = a_m
        betas_m[i] = b_m

        drift_p = abs(abs(a_p) ** 2 - abs(b_p) ** 2 - 1.0)
        drift_m = abs(abs(a_m) ** 2 - abs(b_m) ** 2 - 1.0)
        drift = max(drift_p, drift_m)
        drifts[i] = drift

        if drift > inp.unitarity_tol:
            # Escalate to mpmath (dps=50) on this mode only.
            a_p, b_p, a_m, b_m, drift = _mpmath_refine(inp, float(k))
            alphas_p[i] = a_p
            betas_p[i] = b_p
            alphas_m[i] = a_m
            betas_m[i] = b_m
            drifts[i] = drift

    return ChiralModeResult(
        k=inp.k_modes,
        alpha_plus=alphas_p,
        beta_plus=betas_p,
        alpha_minus=alphas_m,
        beta_minus=betas_m,
        unitarity_drift=drifts,
    )


def _solve_with_diffrax(inp: ChiralSpectrumInputs) -> ChiralModeResult:
    """Preferred JAX path with Kvaerno5 + PIDController."""
    import diffrax  # noqa: F401
    import jax
    import jax.numpy as jnp
    from diffrax import ODETerm, PIDController, SaveAt, diffeqsolve
    from diffrax import Kvaerno5 as Solver

    tau_grid = jnp.asarray(inp.tau_grid, dtype=jnp.float64)

    # diffrax integrates a pytree; we flatten the 4-vector into real parts.
    def vf(t: float, y: jnp.ndarray, args: tuple[float]) -> jnp.ndarray:
        k = args[0]
        Av = jnp.asarray(inp.A(float(t)))
        Bv = jnp.asarray(inp.B(float(t)))
        omg2 = k * k + Av * k + Bv
        # y = [Re h+, Im h+, Re h+', Im h+', Re h-, Im h-, Re h-', Im h-']
        return jnp.array([
            y[2],
            y[3],
            -omg2[0] * y[0],
            -omg2[0] * y[1],
            y[6],
            y[7],
            -omg2[1] * y[4],
            -omg2[1] * y[5],
        ])

    term = ODETerm(vf)
    solver = Solver()
    stepsize = PIDController(rtol=inp.rtol, atol=inp.atol)
    saveat = SaveAt(t0=True, t1=True)

    def _run_one(k: float) -> tuple[complex, complex, complex, complex, float]:
        h0 = 1.0 / (2.0 * k) ** 0.5
        hp0_imag = -((k / 2.0) ** 0.5)
        y0 = jnp.array([h0, 0.0, 0.0, hp0_imag, h0, 0.0, 0.0, hp0_imag])
        sol = diffeqsolve(
            term,
            solver,
            t0=float(tau_grid[0]),
            t1=float(tau_grid[-1]),
            dt0=None,
            y0=y0,
            args=(float(k),),
            stepsize_controller=stepsize,
            saveat=saveat,
            max_steps=200_000,
        )
        y_final = sol.ys[-1]
        h_plus = complex(float(y_final[0]), float(y_final[1]))
        hp_plus = complex(float(y_final[2]), float(y_final[3]))
        h_minus = complex(float(y_final[4]), float(y_final[5]))
        hp_minus = complex(float(y_final[6]), float(y_final[7]))

        ap, bp = _bogoliubov(h_plus, hp_plus, k)
        am, bm = _bogoliubov(h_minus, hp_minus, k)
        drift = max(
            abs(abs(ap) ** 2 - abs(bp) ** 2 - 1.0),
            abs(abs(am) ** 2 - abs(bm) ** 2 - 1.0),
        )
        return ap, bp, am, bm, drift

    _ = jax  # silence unused-import lint
    alphas_p = np.empty_like(inp.k_modes, dtype=np.complex128)
    betas_p = np.empty_like(inp.k_modes, dtype=np.complex128)
    alphas_m = np.empty_like(inp.k_modes, dtype=np.complex128)
    betas_m = np.empty_like(inp.k_modes, dtype=np.complex128)
    drifts = np.empty_like(inp.k_modes, dtype=np.float64)
    for i, k in enumerate(inp.k_modes):
        ap, bp, am, bm, dr = _run_one(float(k))
        alphas_p[i] = ap
        betas_p[i] = bp
        alphas_m[i] = am
        betas_m[i] = bm
        drifts[i] = dr

    return ChiralModeResult(
        k=inp.k_modes,
        alpha_plus=alphas_p,
        beta_plus=betas_p,
        alpha_minus=alphas_m,
        beta_minus=betas_m,
        unitarity_drift=drifts,
    )


def _mpmath_refine(
    inp: ChiralSpectrumInputs,
    k: float,
) -> tuple[complex, complex, complex, complex, float]:
    """High-precision fallback when unitarity drifts above tolerance."""
    import mpmath as mp

    mp.mp.dps = 50

    def rhs(tau: object, y: list[mp.mpc]) -> list[mp.mpc]:
        # mpmath hands us an mpf; cast to float for the numpy-backed
        # coupling callables A, B.
        omg2 = _omega_sq(float(tau), k, inp.A, inp.B)
        return [
            y[1],
            -mp.mpc(float(omg2[0])) * y[0],
            y[3],
            -mp.mpc(float(omg2[1])) * y[2],
        ]

    h0 = mp.mpf(1) / mp.sqrt(mp.mpf(2) * k)
    hp0 = -1j * mp.sqrt(mp.mpf(k) / 2)
    y0 = [h0, hp0, h0, hp0]
    ys = mp.odefun(rhs, float(inp.tau_grid[0]), y0)  # type: ignore[attr-defined]
    y_final = ys(float(inp.tau_grid[-1]))
    h_plus = complex(y_final[0])
    hp_plus = complex(y_final[1])
    h_minus = complex(y_final[2])
    hp_minus = complex(y_final[3])
    ap, bp = _bogoliubov(h_plus, hp_plus, k)
    am, bm = _bogoliubov(h_minus, hp_minus, k)
    drift = max(
        abs(abs(ap) ** 2 - abs(bp) ** 2 - 1.0),
        abs(abs(am) ** 2 - abs(bm) ** 2 - 1.0),
    )
    return ap, bp, am, bm, drift


def F_GB(result: ChiralModeResult) -> float:
    """Scalar GB amplification factor used as input to M4."""
    return result.F_GB_integrated()
