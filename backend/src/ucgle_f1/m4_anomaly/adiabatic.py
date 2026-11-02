"""Adiabatic regularisation of ⟨RR̃⟩ (P1-04), after Kamada, Kokubu, Soda,
Yamada (arXiv:2007.08029, "V3"), Sec. 3.2.

What is computed
----------------
Kamada et al. write the Chern–Pontryagin expectation value as a total
derivative (their Eq. 2.28, with h = u/z),

    ⟨RR̃⟩ = a⁻⁴ ∂_η 𝒥(η),
    𝒥(η) = ∫ d³k/(2π)³ Σ_{A=R,L} (λ_A k / z_A²)
             { |u_A′|² − (k² − (z_A′/z_A)²)|u_A|² − (z_A′/z_A)(u_A u_A*′ + u_A′ u_A*) }
          = ∫ d³k/(2π)³ Σ_A λ_A k ( |h_A′|² − k²|h_A|² ),                 (2.28)

with z_A² = (a² M_Pl²/2)(1 − λ_A k f′/a²) (Eq. 3.20), λ_R = +1, λ_L = −1,
and the lepton number at η_f, from the anomaly Eq. 2.24, is (Eq. 2.29)

    n_L(η_f) = N_{R−L} / (24 (4π)² a_f³) · [𝒥(η_f) − 𝒥(η_i)].

The adiabatic mode u_ad = Ω^{−1/2} exp(i∫Ω) (Eq. 3.14) solves the mode
equation u″ + (k² − z″/z) u = 0 (Eq. 2.14) when (Eqs. 3.15–3.16)

    Ω² = Ω̄² + ¾ (Ω′/Ω)² − ½ Ω″/Ω,      Ω̄² = k² − z″/z,

and its 𝒥 integrand is (Eq. 3.17)

    λ k / (Ω z²) { Ω² + ¼ (Ω′/Ω)² − (k² − (z′/z)²) + (z′/z)(Ω′/Ω) }.

Counting (Eqs. 3.18–3.20): one power of the adiabatic parameter ε per
conformal-time derivative of the background, and one for f′ itself
(z² = (a²/2)(1 − λ k ε f′/a²)). Ω is expanded strictly in ε,
Ω = k + Σ_{n≥1} ω_n εⁿ, solving Eq. 3.15 order by order (the paper's
recursion 3.19 prints the last term as Ω″/Ω′; Eq. 3.15 has Ω″/Ω, which is
what is solved here). ⟨RR̃⟩ = a⁻⁴ ε ∂_η 𝒥 (Eq. 3.21), so ⟨RR̃⟩ to adiabatic
order N is 𝒥 to ε^{N−1}. Kamada et al. find the quartic UV divergence at
ε⁴, the quadratic at ε⁶ and the logarithm at ε⁸ (Eq. 3.21, de Sitter with
constant Θ = −8 H f′/a):

    𝒥_ad = a³ H⁵ κ̃ / (π² M_Pl²) · { (Λ/H)⁴ + 3 (Λ/H)² − 10 ln(2Λ/H) + 10 ln(2c/H) },
    κ̃ = 1/√(256/Θ² − 3) ≃ Θ/16                                           (3.4)

(their a^{−3} in the first line of 3.21 must read a³: ∂_η a³ = 3a⁴H gives the
second line). ``tests/unit/test_m4_adiabatic.py`` checks each order against
these coefficients.

P1-04 asks for the subtraction "to fourth adiabatic order"
(``ADIABATIC_ORDER``); per Eq. 3.21 that removes the quartic divergence
only. Orders 6 and 8 are available here and tested, and M4 reports how
much its result still depends on the UV cutoff.

Representation
--------------
Every coefficient is a rational function of k and of the background
derivatives at one instant:

    A_j = d^j ln a / dη^j  (j ≥ 1),     G_j = d^j g / dη^j,  g ≡ f′/a²,

so 𝒥's integrand at fixed η, summed over helicities, is a Laurent
polynomial in k. Its k-integral is therefore exact (closed form), which
is what :meth:`AdiabaticJ.integral` evaluates. The symbolic expansion is
built once per order with sympy and cached.

Units: reduced Planck (M_Pl = 1), as everywhere in M1–M6 (Decision 11).
Normalisation: Kamada's u ≃ ω^{−1/2} e^{−i∫ω} (Eq. 2.18), i.e. |u|² = 1/k
for a free mode; the exact-mode helpers in ``anomaly.py`` use the same.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Sequence

import numpy as np
import sympy as sp
from numpy.typing import NDArray

# P1-04: "adiabatic regularisation ... to fourth adiabatic order".
ADIABATIC_ORDER = 4

_k = sp.Symbol("k", positive=True)
_lam = sp.Symbol("lam")

Series = list[sp.Expr]


def _syms(m: int) -> tuple[list[sp.Symbol], list[sp.Symbol], list[sp.Symbol], list[sp.Symbol]]:
    """A_1..A_m (A[0] unused), G_0..G_m, E_0..E_m, C_0..C_m."""
    A = [sp.Integer(0)] + [sp.Symbol(f"A{j}") for j in range(1, m + 1)]
    G = [sp.Symbol(f"G{j}") for j in range(0, m + 1)]
    E = [sp.Symbol(f"E{j}") for j in range(0, m + 1)]
    C = [sp.Symbol(f"C{j}") for j in range(0, m + 1)]
    return A, G, E, C


def _args(m: int) -> list[sp.Symbol]:
    A, G, E, C = _syms(m)
    return [*A[1:], *G, *E, *C]


def _mul(a: Series, b: Series, n: int) -> Series:
    out: Series = [sp.Integer(0)] * (n + 1)
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        for j in range(0, n + 1 - i):
            if j < len(b) and b[j] != 0:
                out[i + j] += ai * b[j]
    return [sp.expand(c) for c in out]


def _add(*terms: Series) -> Series:
    n = max(len(t) for t in terms)
    return [sp.expand(sum((t[i] if i < len(t) else 0 for t in terms), sp.Integer(0))) for i in range(n)]


def _scale(a: Series, c: sp.Expr) -> Series:
    return [sp.expand(c * x) for x in a]


def _inv(a: Series, n: int) -> Series:
    """1/a as a truncated series; a[0] must be non-zero."""
    a0 = a[0]
    rest = [sp.Integer(0)] + [-x / a0 for x in a[1:]]
    out: Series = [sp.Integer(1)] + [sp.Integer(0)] * n
    p: Series = [sp.Integer(1)] + [sp.Integer(0)] * n
    for _ in range(n):
        p = _mul(p, rest, n)
        out = _add(out, p)
    return _scale(out[: n + 1], 1 / a0)


def _deriv(m: int) -> Callable[[Series, int], Series]:
    A, G, E, C = _syms(m)

    def d0(e: sp.Expr) -> sp.Expr:
        out = sp.Integer(0)
        for j in range(1, m):
            out += sp.diff(e, A[j]) * A[j + 1]
        for F in (G, E, C):
            for j in range(0, m):
                out += sp.diff(e, F[j]) * F[j + 1]
        if any(e.has(F[m]) for F in (G, E, C)) or e.has(A[m]):
            msg = "derivative order exceeds the symbol table"
            raise RuntimeError(msg)
        return sp.expand(out)

    def D(a: Series, n: int) -> Series:
        # d/dη carries one ε: shift by one order.
        return ([sp.Integer(0)] + [d0(x) for x in a])[: n + 1]

    return D


@lru_cache(maxsize=8)
def _expansion(order: int, gb: bool = True) -> tuple[list[sp.Expr], list[sp.Expr], int]:
    """(ω_n for n ≤ N, 𝒥-integrand coefficients ε⁰…ε^{N}, m) with N = order − 1.

    The 𝒥 coefficients are a⁻²-stripped and summed over λ = ±1. ``gb=False``
    drops the Gauss–Bonnet functions (E, C ≡ 0): Kamada et al.'s CS-only
    model, much cheaper to expand at order 8.
    """
    if order < 2 or order % 2:
        msg = "adiabatic order must be an even integer ≥ 2"
        raise ValueError(msg)
    n = order - 1  # 𝒥 to ε^{N−1} gives ⟨RR̃⟩ to ε^N
    m = n + 4      # enough derivative symbols for Ω′ at ε^n
    A, G, E, C = _syms(m)
    D = _deriv(m)
    k, lam = _k, _lam
    nn = n + 2

    # Q = G_T − λ k g = 1 + δ_T − λ k ε g (3.20; δ_T = G_T − 1, the GB shift,
    # carries two derivatives: ε²). z² = a² Q / 2.
    Q: Series = [sp.Integer(1), -lam * k * G[0], E[0] if gb else sp.Integer(0)]
    iQ = _inv(Q, nn)
    zp = _add([sp.Integer(0), A[1]], _scale(_mul(D(Q, nn), iQ, nn), sp.Rational(1, 2)))
    W = _add(D(zp, nn), _mul(zp, zp, nn))                         # z″/z
    # Ω̄² = k² P/Q − z″/z (3.16), P = F_T − λ k g = Q + ε² Δ, Δ = F_T − G_T
    # (the GB sound-speed shift, C in m3_modes; zero in Kamada et al.'s model).
    Obar2 = _add([k**2], _scale(_mul([sp.Integer(0), sp.Integer(0), C[0] if gb else sp.Integer(0)],
                                     iQ, nn), k**2),
                 _scale(W, -1))

    # Solve Eq. 3.15 strictly order by order: Ω = k + Σ ω_j ε^j.
    Om: Series = [k] + [sp.Integer(0)] * nn
    for j in range(1, nn + 1):
        dO = D(Om, nn)
        R = _add(
            _mul(_mul(Om, Om, nn), _mul(Om, Om, nn), nn),
            _scale(_mul(dO, dO, nn), sp.Rational(-3, 4)),
            _scale(_mul(Om, D(dO, nn), nn), sp.Rational(1, 2)),
            _scale(_mul(Obar2, _mul(Om, Om, nn), nn), -1),
        )
        Om[j] = sp.expand(-R[j] / (2 * k**3))

    dO = D(Om, n)
    iO = _inv(Om[: n + 1], n)
    r = _mul(dO, iO, n)                                           # Ω′/Ω
    zpn = zp[: n + 1]
    brace = _add(
        _mul(Om[: n + 1], Om[: n + 1], n),
        _scale(_mul(r, r, n), sp.Rational(1, 4)),
        [-k**2],
        _mul(zpn, zpn, n),
        _mul(zpn, r, n),
    )
    pref = _scale(_mul(iO, _inv(Q, n), n), 2 * lam * k)          # λ k/(Ω z²)·a², z² = a²Q/2
    J = _mul(pref, brace, n)
    Jsum = [sp.expand(c.subs(lam, 1) + c.subs(lam, -1)) for c in J]
    return Om[: n + 1], Jsum, m


@lru_cache(maxsize=8)
def _compiled(order: int, gb: bool = True) -> tuple[int, list[int], list[Callable[..., float]], list[Callable[..., float]]]:
    """Lambdified Laurent coefficients of the helicity-summed 𝒥 integrand (cached)."""
    _, J, m = _expansion(order, gb)
    args = _args(m)
    total = sp.expand(sum(J, sp.Integer(0)))
    # Laurent coefficients in k (the k² of d³k is added in AdiabaticJ.integral()).
    shift = 4 * order + 8
    poly = sp.Poly(sp.expand(total * _k**shift), _k)
    powers: list[int] = []
    fns: list[Callable[..., float]] = []
    for (deg,), coeff in poly.terms():
        powers.append(int(deg) - shift)
        fns.append(sp.lambdify(args, coeff, modules="math"))
    per_order = [sp.lambdify([_k, *args], c, modules="math") for c in J]
    return m, powers, fns, per_order


@dataclass(frozen=True)
class Background:
    """Background at one conformal time η.

    a; A_j = dʲ ln a/dηʲ (j ≥ 1); G_j = dʲ g/dηʲ with g = f′/a² (CS, Eq. 3.20);
    E_j = dʲ δ_T/dηʲ with δ_T = G_T − 1 and C_j = dʲ Δ/dηʲ with Δ = F_T − G_T
    (GB; ``m7_infer/couplings.py``). Missing entries are zero.
    """

    a: float
    A: Sequence[float]          # A_1, A_2, …
    G: Sequence[float]          # G_0, G_1, …
    E: Sequence[float] = ()     # E_0, E_1, …
    C: Sequence[float] = ()     # C_0, C_1, …

    def values(self, m: int) -> list[float]:
        def pad(x: Sequence[float], n: int) -> list[float]:
            v = [float(y) for y in x][:n]
            return v + [0.0] * (n - len(v))

        return pad(self.A, m) + pad(self.G, m + 1) + pad(self.E, m + 1) + pad(self.C, m + 1)

    def needed(self, order: int) -> int:
        """Highest derivative index the order-``order`` expansion reads."""
        return _expansion(order)[2]


class AdiabaticJ:
    """The adiabatic 𝒥 integrand (Eq. 3.17) to a given adiabatic order.

    ``order`` is the adiabatic order of ⟨RR̃⟩ (Eq. 3.21): 𝒥 is kept to
    ε^{order−1}. At fixed η the helicity sum is a Laurent polynomial in k,
    ``Σ_p c_p k^p``; :meth:`integral` integrates d³k/(2π)³ of it exactly.
    """

    def __init__(self, order: int = ADIABATIC_ORDER, *, gb: bool = True) -> None:
        self.order = order
        self.gb = gb
        self._m, self._powers, self._coeffs, self._per_order = _compiled(order, gb)

    def coefficients(self, bg: Background) -> dict[int, float]:
        """{p: c_p} with Σ_λ (a² × integrand) = Σ_p c_p k^p (a⁻² stripped)."""
        vals = bg.values(self._m)
        out: dict[int, float] = {}
        for p, f in zip(self._powers, self._coeffs, strict=True):
            out[p] = out.get(p, 0.0) + float(f(*vals))
        return out

    def integrand(self, k: float | NDArray[np.float64], bg: Background) -> NDArray[np.float64]:
        """Σ_λ of the Eq. 3.17 integrand at comoving k (including the a⁻² of 1/z²)."""
        kk = np.asarray(k, dtype=float)
        tot = np.zeros_like(kk)
        for p, c in self.coefficients(bg).items():
            tot = tot + c * kk**p
        return tot / bg.a**2

    def per_order(self, k: float, bg: Background) -> list[float]:
        """Σ_λ integrand split by adiabatic order ε⁰…ε^{order−1} (a⁻² included)."""
        vals = bg.values(self._m)
        return [float(f(float(k), *vals)) / bg.a**2 for f in self._per_order]

    def integral(self, k_lo: float, k_hi: float, bg: Background) -> float:
        """∫_{k_lo}^{k_hi} d³k/(2π)³ Σ_λ integrand = (1/2π²) ∫ dk k² (…), exactly."""
        tot = 0.0
        for p, c in self.coefficients(bg).items():
            q = p + 3
            if q == 0:
                tot += c * (np.log(k_hi) - np.log(k_lo))
            else:
                tot += c * (k_hi**q - k_lo**q) / q
        return tot / (2.0 * np.pi**2 * bg.a**2)


@lru_cache(maxsize=8)
def _omega_parts(order: int, gb: bool = True) -> tuple[Callable[..., float], Callable[..., float]]:
    """Lambdified helicity-even and helicity-odd (per unit λ) parts of Ω to ε^{order−1}."""
    Om, _, m = _expansion(order, gb)
    tot = sp.expand(sum(Om, sp.Integer(0)))
    plus, minus = tot.subs(_lam, 1), tot.subs(_lam, -1)
    even = sp.expand((plus + minus) / 2)
    odd = sp.expand((plus - minus) / 2)
    args = [_k, *_args(m)]
    return sp.lambdify(args, even, modules="math"), sp.lambdify(args, odd, modules="math")


def adiabatic_omega_parts(order: int, k: float, bg: Background) -> tuple[float, float]:
    """(Ω_even, Ω_odd) with Ω_λ = Ω_even + λ Ω_odd, to ε^{order−1} (Eq. 3.15).

    The odd part is computed directly (not as a difference of the two
    helicities), so a CS coupling far below double precision relative to k
    is resolved. M4 starts its exact modes in this adiabatic vacuum.
    """
    even, odd = _omega_parts(order)
    m = _expansion(order)[2]
    vals = bg.values(m)
    return float(even(float(k), *vals)), float(odd(float(k), *vals))


def adiabatic_frequency(order: int, k: float, bg: Background, *, gb: bool = True) -> float:
    """Ω to ε^{order−1} (Eq. 3.15, strict expansion), helicity λ = +1.

    Exposed for the analytic-limit tests (de Sitter, radiation, Minkowski).
    """
    Om, _, m = _expansion(order, gb)
    f = sp.lambdify([_k, _lam, *_args(m)], sum(Om, sp.Integer(0)), modules="math")
    return float(f(float(k), 1.0, *bg.values(m)))


def de_sitter_background(eta: float, H: float, theta: float, n: int = 12) -> Background:
    """a = −1/(Hη), Θ = −8 H f′/a constant (Kamada Sec. 2.1): g = f′/a² = Θ η / 8.

    A_j = dʲ ln a/dηʲ = dʲ[−ln(−η)]/dηʲ = −(−1)^{j−1} (j−1)!/ηʲ.
    """
    a = -1.0 / (H * eta)
    A = []
    for j in range(1, n + 1):
        # d^j/dη^j [−ln(−η)] = −(−1)^{j−1} (j−1)! / η^j
        A.append(-((-1.0) ** (j - 1)) * float(math.factorial(j - 1)) / eta**j)
    G = [theta * eta / 8.0, theta / 8.0] + [0.0] * (n - 1)
    return Background(a=a, A=tuple(A), G=tuple(G))
