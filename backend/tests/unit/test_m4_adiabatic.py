"""P1-04: the adiabatic expansion of ⟨RR̃⟩ (arXiv:2007.08029 Sec. 3.2), order by order.

Analytic limits:

* de Sitter with a constant Chern–Simons rate Θ (Kamada et al. Sec. 2.1):
  each adiabatic order adds exactly one UV term of their Eq. 3.21,
  𝒥_ad = a³ H⁵ κ̃/π² · {(Λ/H)⁴ [order 4] + 3(Λ/H)² [order 6]
                        − 10 ln(Λ/c) [order 8]},  κ̃ ≃ Θ/16 (Eq. 3.4);
* de Sitter without CS: the Bunch–Davies |u|² = (1 + 1/(kη)²)/k is the
  adiabatic series, which terminates;
* radiation (a ∝ η, z″ = 0): Ω = k at every order;
* Minkowski with a constant GB sound-speed shift C: Ω = k√(1 + C);
* parity: GB alone gives no helicity-odd 𝒥; CS → −CS flips it.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from ucgle_f1.m4_anomaly.adiabatic import (
    ADIABATIC_ORDER,
    AdiabaticJ,
    Background,
    adiabatic_frequency,
    de_sitter_background,
)

H = 1.0
THETA = 1.0e-8  # leading order in Θ, as Eq. 3.21 (O(κ̃²) dropped)


def _kappa(theta: float) -> float:
    return 1.0 / math.sqrt(256.0 / theta**2 - 3.0)  # Eq. 3.4


def _integral(coeffs: dict[int, float], lo: float, hi: float, a: float) -> float:
    tot = 0.0
    for p, c in coeffs.items():
        q = p + 3
        tot += c * (math.log(hi / lo) if q == 0 else (hi**q - lo**q) / q)
    return tot / (2.0 * math.pi**2 * a**2)


def _slice(hi_order: int, lo_order: int, bg: Background) -> dict[int, float]:
    """Coefficients of the ε^{lo_order}…ε^{hi_order−1} part of 𝒥 (Kamada's CS-only model)."""
    out = dict(AdiabaticJ(hi_order, gb=False).coefficients(bg))
    if lo_order:
        for p, c in AdiabaticJ(lo_order, gb=False).coefficients(bg).items():
            out[p] = out.get(p, 0.0) - c
    return out


@pytest.mark.parametrize("eta", [-1.0, -0.37])
@pytest.mark.parametrize(("lam_over_h", "c_over_h"), [(100.0, 1e-2), (30.0, 1e-1)])
def test_each_order_adds_one_term_of_kamada_eq_3_21(eta: float, lam_over_h: float, c_over_h: float) -> None:
    bg = de_sitter_background(eta, H, THETA)
    lo, hi = c_over_h * bg.a, lam_over_h * bg.a       # physical cutoffs c < k/a < Λ
    unit = bg.a**3 * H**5 * _kappa(THETA) / math.pi**2
    L, c = lam_over_h, c_over_h
    quartic = _integral(_slice(4, 0, bg), lo, hi, bg.a)
    quadratic = _integral(_slice(6, 4, bg), lo, hi, bg.a)
    logarithm = _integral(_slice(8, 6, bg), lo, hi, bg.a)
    # The lower cutoff enters the power terms as (Λ⁴ − c⁴), (Λ² − c²).
    assert quartic == pytest.approx(unit * (L**4 - c**4), rel=1e-9, abs=0)
    assert quadratic == pytest.approx(unit * 3.0 * (L**2 - c**2), rel=1e-9, abs=0)
    # −10 ln(2Λ/H) + 10 ln(2c/H) (first line of Eq. 3.21).
    assert logarithm == pytest.approx(unit * (-10.0) * math.log(L / c), rel=1e-9, abs=0)


def test_fourth_order_is_the_plan_default_and_removes_only_the_quartic_term() -> None:
    assert ADIABATIC_ORDER == 4
    bg = de_sitter_background(-1.0, H, THETA)
    # With and without the GB functions the CS-only background gives the same 𝒥.
    def nz(d: dict[int, float]) -> dict[int, float]:
        return {p: c for p, c in d.items() if c != 0.0}

    assert nz(AdiabaticJ(4).coefficients(bg)) == nz(AdiabaticJ(4, gb=False).coefficients(bg))
    # Order 4: 𝒥 ∝ k (Λ⁴ after d³k); orders 6 and 8 add k⁻¹ (Λ²) and k⁻³ (log).
    leading = {p for p, c in AdiabaticJ(4).coefficients(bg).items() if c != 0.0}
    assert leading == {1}
    six = {p for p, c in _slice(6, 4, bg).items() if abs(c) > 1e-20}
    assert -1 in six


@pytest.mark.parametrize("x", [3.0, 10.0, 30.0])
def test_de_sitter_bunch_davies_is_the_adiabatic_series(x: float) -> None:
    # Θ = 0, a = −1/(Hη): exact |u|² = (1 + 1/(kη)²)/k (Kamada normalisation, Eq. 2.18).
    eta = -1.0
    k = x / abs(eta)
    bg = de_sitter_background(eta, H, 0.0)
    exact = (1.0 + 1.0 / (k * eta) ** 2) / k
    o4 = 1.0 / adiabatic_frequency(4, k, bg, gb=False)   # Ω = k − 1/(kη²)
    o6 = 1.0 / adiabatic_frequency(6, k, bg, gb=False)   # + 1/(k³η⁴)
    # Ω to ε³ misses the 1/(kη)⁴ term of 1/Ω; to ε⁵ it is exact through 1/(kη)⁴,
    # and the series 1/Ω terminates, so the error drops to O((kη)⁻⁶).
    assert abs(o4 - exact) / exact == pytest.approx(1.0 / x**4, rel=2.0 / x**2)
    assert abs(o6 - exact) / exact <= 2.0 / x**6
    assert adiabatic_frequency(6, k, bg, gb=False) == pytest.approx(
        k - 1.0 / (k * eta**2) + 1.0 / (k**3 * eta**4), rel=1e-14, abs=0
    )


def test_radiation_era_frequency_is_k_at_every_order() -> None:
    # a ∝ η: A_j = dʲ ln η/dηʲ = (−1)^{j−1}(j−1)!/ηʲ, z″/z = a″/a = 0.
    eta = 2.5
    A = [(-1.0) ** (j - 1) * math.factorial(j - 1) / eta**j for j in range(1, 12)]
    bg = Background(a=eta, A=A, G=[0.0])
    for order in (2, 4, 6, 8):
        assert adiabatic_frequency(order, 0.7, bg, gb=False) == pytest.approx(0.7, rel=1e-14, abs=0)


@pytest.mark.parametrize("C", [1e-3, 1e-2])
def test_constant_sound_speed_gives_k_sqrt_1_plus_c(C: float) -> None:
    # Minkowski, constant GB shift Δ = C: Ω̄² = k²(1 + C) exactly; C counts as ε².
    bg = Background(a=1.0, A=[0.0], G=[0.0], E=[0.0], C=[C])
    k = 3.0
    exact = k * math.sqrt(1.0 + C)
    assert adiabatic_frequency(4, k, bg) == pytest.approx(k * (1 + C / 2), rel=1e-15, abs=0)
    assert abs(adiabatic_frequency(6, k, bg) - exact) <= k * C**3 / 8.0


def test_gauss_bonnet_alone_is_parity_even_and_cs_is_odd() -> None:
    rng = np.random.default_rng(0)
    for order in (4, 6):
        J = AdiabaticJ(order)
        A = list(rng.normal(size=12))
        E = list(rng.normal(size=12) * 1e-3)
        Cs = list(rng.normal(size=12) * 1e-3)
        G = list(rng.normal(size=12) * 1e-3)
        no_cs = J.coefficients(Background(a=1.3, A=A, G=[0.0] * 12, E=E, C=Cs))
        assert all(c == 0.0 for c in no_cs.values())
        plus = J.integrand(np.array([0.5, 2.0]), Background(a=1.3, A=A, G=G, E=E, C=Cs))
        minus = J.integrand(np.array([0.5, 2.0]), Background(a=1.3, A=A, G=[-g for g in G], E=E, C=Cs))
        assert np.any(plus != 0.0)
        np.testing.assert_allclose(minus, -plus, rtol=1e-12, atol=0)


def test_integral_is_the_exact_k_integral_of_the_integrand() -> None:
    from scipy.integrate import quad

    bg = de_sitter_background(-0.8, 2.0, 1e-3)
    J = AdiabaticJ(6)
    lo, hi = 0.3, 40.0
    num, _ = quad(lambda k: k**2 * float(J.integrand(k, bg)) / (2 * math.pi**2), lo, hi,
                  epsabs=0.0, epsrel=1e-13, limit=200)
    assert J.integral(lo, hi, bg) == pytest.approx(num, rel=1e-11, abs=0)


def test_rejects_odd_or_too_low_orders() -> None:
    with pytest.raises(ValueError, match="even"):
        AdiabaticJ(3)
    with pytest.raises(ValueError, match="even"):
        AdiabaticJ(0)
