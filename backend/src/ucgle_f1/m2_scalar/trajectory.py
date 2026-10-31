"""Klein–Gordon evolution of the inflaton φ (P1-02).

Units: reduced Planck units (M_Pl = 1). Independent variable N = ln a.
With x ≡ dφ/dN, ρ_φ = ½φ̇² + V, φ̇ = H x and the slow-roll parameter
ε ≡ −Ḣ/H², the Klein–Gordon equation with perturbative decay Γ_φ,

    φ̈ + (3H + Γ_φ) φ̇ + V′(φ) = 0,
    ρ̇_r = −4Hρ_r + Γ_φ φ̇²,

becomes, in e-folds,

    dx/dN    = −(3 − ε) x − (Γ_φ/H) x − V′/H²,
    dρ_r/dN  = −4 ρ_r + Γ_φ H x²,
    H²       = (V + ρ_r) / (3 − x²/2),
    ε        = x²/2 + (2/3) ρ_r / H².

(For ρ_r = Γ_φ = 0 this is the standard single-field system
dx/dN = −(3 − ε)(x + V′/V); slow roll gives x ≈ −V′/V.)

Numerically the e-fold form is singular once the field oscillates:
H² = V/(3 − x²/2) has a vanishing denominator whenever V → 0 (x²/2 → 3).
So the integration runs in cosmic time t with state (φ, φ̇, ρ_r, N),

    dφ/dt = φ̇,  dφ̇/dt = −(3H + Γ_φ) φ̇ − V′,
    dρ_r/dt = −4Hρ_r + Γ_φ φ̇²,  dN/dt = H,
    H² = (½φ̇² + V + ρ_r)/3   (never singular),

and is reported on an N grid (N(t) is monotonic). Two stages, as P1-02
asks: inflation (ε < 1) with an explicit high-order integrator (DOP853);
after ε first reaches 1 the field oscillates with frequency m ≫ H and the
stiff reheating stage is integrated with Radau (implicit, L-stable).

``solve_trajectory_on_background`` evolves φ as a test field on a
given M1 :class:`~ucgle_f1.m1_background.Background` (H(N) and ε(N) from
the background instead of from φ).

Conformal-time derivatives (′ = d/dτ, dτ = dN/(aH)) for M3/M7:

    φ′  = a H x,
    φ″  = a² H² [ (1 − ε) x + dx/dN ].
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

from .potentials import ScalarModel


def potential_args(model: ScalarModel, params: dict[str, float]) -> tuple[float, ...]:
    """Order a Potential.params dict to match ``model.param_names``."""
    missing = [p for p in model.param_names if p not in params and p != "_unused"]
    if missing:
        raise ValueError(f"potential parameters missing: {missing}")
    return tuple(float(params.get(p, 0.0)) for p in model.param_names)


@dataclass
class Trajectory:
    """φ(N) and derived quantities on the integration grid."""

    N: NDArray[np.float64]
    phi: NDArray[np.float64]
    dphi_dN: NDArray[np.float64]
    d2phi_dN2: NDArray[np.float64]
    H: NDArray[np.float64]
    epsilon: NDArray[np.float64]
    rho_r: NDArray[np.float64]
    N_end_inflation: float | None
    stages: list[str] = field(default_factory=list)

    def a(self, a_ref: float = 1.0, N_ref: float = 0.0) -> NDArray[np.float64]:
        """Scale factor a(N) = a_ref · e^{N − N_ref}."""
        return a_ref * np.exp(self.N - N_ref)

    def dphi_dtau(self, a_ref: float = 1.0, N_ref: float = 0.0) -> NDArray[np.float64]:
        """φ′ = a H dφ/dN."""
        return self.a(a_ref, N_ref) * self.H * self.dphi_dN

    def d2phi_dtau2(self, a_ref: float = 1.0, N_ref: float = 0.0) -> NDArray[np.float64]:
        """φ″ = a² H² [(1 − ε) dφ/dN + d²φ/dN²]."""
        a = self.a(a_ref, N_ref)
        return a**2 * self.H**2 * ((1.0 - self.epsilon) * self.dphi_dN + self.d2phi_dN2)


def _t_rhs(
    model: ScalarModel, args: tuple[float, ...], Gamma_phi: float,
) -> Callable[[float, NDArray[np.float64]], NDArray[np.float64]]:
    """Cosmic-time system for y = (φ, φ̇, ρ_r, N)."""

    def rhs(_t: float, y: NDArray[np.float64]) -> NDArray[np.float64]:
        phi, pd, rho_r = float(y[0]), float(y[1]), max(float(y[2]), 0.0)
        V = float(model.V(phi, *args))
        H = np.sqrt(max(0.5 * pd * pd + V + rho_r, 1e-300) / 3.0)
        dpd = -(3.0 * H + Gamma_phi) * pd - float(model.Vp(phi, *args))
        drho = -4.0 * H * rho_r + Gamma_phi * pd * pd
        return np.array([pd, dpd, drho, H])

    return rhs


def _epsilon_t(V: float, pd: float, rho_r: float) -> float:
    H2 = max(0.5 * pd * pd + V + rho_r, 1e-300) / 3.0
    return (0.5 * pd * pd + (2.0 / 3.0) * rho_r) / H2


def _sample_on_N(sol: Any, t_lo: float, t_hi: float, N_targets: NDArray[np.float64],
                 model: ScalarModel, args: tuple[float, ...]) -> NDArray[np.float64]:
    """Evaluate a cosmic-time dense solution at given N (N(t) monotonic).

    A dense t table gives the first guess; two Newton steps
    (δt = δN / H) put every sample on its target N to round-off.
    """
    tt = np.linspace(t_lo, t_hi, 200_001)
    NN = sol(tt)[3]
    t = np.interp(N_targets, NN, tt)
    for _ in range(3):
        Y = sol(t)
        V = np.asarray(model.V(Y[0], *args), dtype=np.float64)
        H = np.sqrt(np.maximum(0.5 * Y[1] ** 2 + V + np.maximum(Y[2], 0.0), 1e-300) / 3.0)
        t = np.clip(t + (N_targets - Y[3]) / H, t_lo, t_hi)
    return np.asarray(sol(t))


def solve_trajectory(
    model: ScalarModel,
    params: dict[str, float],
    phi0: float,
    *,
    dphi_dN0: float | None = None,
    N_max: float = 80.0,
    N_after_end: float = 5.0,
    Gamma_phi: float = 0.0,
    n_out: int = 4001,
    rtol: float = 1e-12,
    atol: float = 1e-14,
) -> Trajectory:
    """Self-consistent inflation → reheating trajectory.

    ``dphi_dN0`` defaults to the slow-roll attractor −V′/V. Stage 1
    (DOP853) stops when ε reaches 1 (end of inflation) or at ``N_max``;
    stage 2 (Radau) continues for ``N_after_end`` e-folds of the stiff
    oscillating/reheating phase.
    """
    args = potential_args(model, params)
    V0 = float(model.V(phi0, *args))
    if V0 <= 0:
        raise ValueError("V(φ0) must be positive to start inflation")
    x0 = -float(model.Vp(phi0, *args)) / V0 if dphi_dN0 is None else float(dphi_dN0)
    if 0.5 * x0 * x0 >= 3.0:
        raise ValueError("|dφ/dN| must be below √6")
    H0 = np.sqrt(V0 / (3.0 - 0.5 * x0 * x0))
    rhs = _t_rhs(model, args, Gamma_phi)

    def end_of_inflation(_t: float, y: NDArray[np.float64]) -> float:
        return _epsilon_t(float(model.V(float(y[0]), *args)), float(y[1]), max(float(y[2]), 0.0)) - 1.0

    end_of_inflation.terminal = True  # type: ignore[attr-defined]
    end_of_inflation.direction = 1  # type: ignore[attr-defined]

    def reached_N_max(_t: float, y: NDArray[np.float64]) -> float:
        return float(y[3]) - N_max

    reached_N_max.terminal = True  # type: ignore[attr-defined]

    y0 = np.array([phi0, H0 * x0, 0.0, 0.0])
    t_big = 1e6 * (N_max + N_after_end + 1.0) / H0
    s1 = solve_ivp(rhs, (0.0, t_big), y0, method="DOP853", rtol=rtol, atol=atol,
                   dense_output=True, events=(end_of_inflation, reached_N_max))
    if not s1.success:
        raise RuntimeError(f"inflation stage failed: {s1.message}")
    stages = ["inflation:DOP853"]
    ended = len(s1.t_events[0]) > 0
    N_end = float(s1.y_events[0][0][3]) if ended else None
    pieces: list[tuple[Any, float, float, float, float]] = [
        (s1.sol, 0.0, float(s1.t[-1]), 0.0, float(s1.y[3, -1])),
    ]

    if ended and N_after_end > 0:
        assert N_end is not None
        target = N_end + N_after_end

        def reached_target(_t: float, y: NDArray[np.float64]) -> float:
            return float(y[3]) - target

        reached_target.terminal = True  # type: ignore[attr-defined]
        t1 = float(s1.t[-1])
        s2 = solve_ivp(rhs, (t1, t1 + 1e6 * t_big), s1.y[:, -1], method="Radau",
                       rtol=max(rtol, 1e-10), atol=atol, dense_output=True, events=reached_target)
        if not s2.success:
            raise RuntimeError(f"reheating stage failed: {s2.message}")
        stages.append("reheating:Radau")
        pieces.append((s2.sol, t1, float(s2.t[-1]), N_end, float(s2.y[3, -1])))

    N = np.linspace(0.0, pieces[-1][4], n_out)
    Y = np.empty((4, n_out))
    for sol, t_lo, t_hi, n_lo, n_hi in pieces:
        m = (N >= n_lo) & (N <= n_hi)
        if np.any(m):
            Y[:, m] = _sample_on_N(sol, t_lo, t_hi, N[m], model, args)
    phi, pd, rho_r = Y[0], Y[1], np.maximum(Y[2], 0.0)
    V = np.asarray(model.V(phi, *args), dtype=np.float64)
    Vp = np.asarray(model.Vp(phi, *args), dtype=np.float64)
    H = np.sqrt(np.maximum(0.5 * pd**2 + V + rho_r, 1e-300) / 3.0)
    eps = (0.5 * pd**2 + (2.0 / 3.0) * rho_r) / H**2
    x = pd / H
    # dx/dN = φ̈/H² + ε x, with φ̈ = −(3H + Γ)φ̇ − V′.
    phi_ddot = -(3.0 * H + Gamma_phi) * pd - Vp
    d2 = phi_ddot / H**2 + eps * x
    return Trajectory(N=Y[3], phi=phi, dphi_dN=x, d2phi_dN2=d2, H=H, epsilon=eps,
                      rho_r=rho_r, N_end_inflation=N_end, stages=stages)


def solve_trajectory_on_background(
    model: ScalarModel,
    params: dict[str, float],
    background: Any,
    phi0: float,
    dphi_dN0: float,
    *,
    Gamma_phi: float = 0.0,
    rtol: float = 1e-10,
    atol: float = 1e-14,
) -> Trajectory:
    """φ as a test field on an M1 background (Radau; H(N), ε(N) from M1).

    dx/dN = −(3 − ε_bg) x − (Γ_φ/H) x − V′/H², with ε_bg = −d ln H/dN.
    """
    args = potential_args(model, params)
    N_grid = np.asarray(background.N, dtype=np.float64)
    dlnH = background._H_spline.derivative()

    def rhs(N: float, y: NDArray[np.float64]) -> NDArray[np.float64]:
        phi, x = float(y[0]), float(y[1])
        H = float(background.H_of_N(N))
        eps = -float(dlnH(N)) / H
        dx = -(3.0 - eps) * x - (Gamma_phi / H) * x - float(model.Vp(phi, *args)) / (H * H)
        return np.array([x, dx])

    sol = solve_ivp(rhs, (float(N_grid[0]), float(N_grid[-1])), np.array([phi0, dphi_dN0]),
                    method="Radau", t_eval=N_grid, rtol=rtol, atol=atol)
    if not sol.success:
        raise RuntimeError(f"KG on background failed: {sol.message}")
    H = np.asarray(background.H_of_N(N_grid), dtype=np.float64)
    eps = -np.asarray(dlnH(N_grid), dtype=np.float64) / H
    phi, x = sol.y
    Vp = np.asarray(model.Vp(phi, *args), dtype=np.float64)
    d2 = -(3.0 - eps) * x - (Gamma_phi / H) * x - Vp / H**2
    return Trajectory(N=N_grid, phi=phi, dphi_dN=x, d2phi_dN2=d2, H=H, epsilon=eps,
                      rho_r=np.asarray(background.rho_r, dtype=np.float64),
                      N_end_inflation=None, stages=["background:Radau"])


# ── PyTransport 3.0 (optional multi-field backend) ─────────────────────


def pytransport_available() -> bool:
    """True when the PyTransport 3.0 package is importable (soft import)."""
    try:
        import PyTransport  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False
    return True


def solve_trajectory_pytransport(*_args: Any, **_kwargs: Any) -> Trajectory:
    """Multi-field backend via PyTransport 3.0 (not on any package index).

    PyTransport must be installed by hand (docs/qcompass/optional-backends.md);
    P1-06 pins it as a git source. Until then the single-field solver
    above is the only backend: this raises with a clear message instead
    of guessing PyTransport's API.
    """
    if not pytransport_available():
        msg = ("PyTransport 3.0 is not installed (optional multi-field backend; "
               "see docs/qcompass/optional-backends.md). Use solve_trajectory().")
        raise ImportError(msg)
    msg = ("PyTransport adapter not wired yet: its 3.0 API is verified when "
           "P1-06 pins the package (LEDGER correction 3).")
    raise NotImplementedError(msg)


__all__ = [
    "Trajectory",
    "potential_args",
    "pytransport_available",
    "solve_trajectory",
    "solve_trajectory_on_background",
    "solve_trajectory_pytransport",
]
