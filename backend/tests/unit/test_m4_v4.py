"""P1-04: M4's V4 integrand on Maleknejad's own mode model (arXiv:2412.09490, Eqs. 7–15).

V4 parameterises the transient production of a GW background in the
radiation era (a ∝ τ) as (Eqs. 9–11)

    h_s(τ, q) = a⁻¹(τ) 𝒯_s(τ, q) e^{−iqτ} h_{s,q,0},
    𝒯_s = 1 − e^{−π β_s (τ − τ_in)},   β_± = β (1 ± b_χ),

and finds for the Eq. 7 integrand at τ ≫ τ_* (Eq. 13)

    (|∂_τ h_s|² − q²|h_s|²)|_{τ_in}^{τ} = −(π β_s / a_in)² |h_s(τ_0)|²,

so that, with Ω_gw,0(q) = Σ_s (2π q⁵/3H₀²)|h_s(τ_0)|² and Ω^± = (1 ± χ)Ω/2
(Eq. 12), the helicity sum carries [2b_χ + (1 + b_χ²)χ] (Eqs. 14–15).
These tests feed V4's modes to M4's ``boundary_bracket`` (the per-mode
integrand M4 evaluates for its V4 cross-check) and recover Eq. 13 and the
Eq. 15 helicity factor. The linearised helicity sum M4 integrates is the
exact odd part of that bracket.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from ucgle_f1.m4_anomaly.physical import _odd_bracket, boundary_bracket

# V4's late-time limit needs ℋ ≪ πβ (β/ℋ_* > 1 is V4's assumption; it uses 10³).
BETA = 50.0
TAU_IN = 1.0
A_IN = 1.0


def _v4_mode(tau: float, q: float, beta_s: float, h0: complex) -> tuple[complex, complex]:
    """Eqs. 9–10 in a radiation era a = a_in τ/τ_in: (h, ∂_τ h), analytic."""
    a = A_IN * tau / TAU_IN
    ap = A_IN / TAU_IN
    T = 1.0 - math.exp(-math.pi * beta_s * (tau - TAU_IN))
    Tp = math.pi * beta_s * math.exp(-math.pi * beta_s * (tau - TAU_IN))
    ph = complex(math.cos(q * tau), -math.sin(q * tau))
    h = T * ph * h0 / a
    hp = (Tp - 1j * q * T - (ap / a) * T) * ph * h0 / a
    return h, hp


@pytest.mark.parametrize("q", [3.0, 30.0])
@pytest.mark.parametrize("b_chi", [-0.5, 0.0, 0.7])
@pytest.mark.parametrize("s", [+1.0, -1.0])
def test_eq7_integrand_on_v4_modes_gives_eq13(q: float, b_chi: float, s: float) -> None:
    beta_s = BETA * (1.0 + s * b_chi)                       # Eq. 11
    h0 = 0.37 + 0.11j
    tau = 400.0                                             # τ ≫ τ_* : 𝒯 = 1
    hi, hpi = _v4_mode(TAU_IN, q, beta_s, h0)
    hf, hpf = _v4_mode(tau, q, beta_s, h0)
    delta = (boundary_bracket(hf, hpf, q, s) - boundary_bracket(hi, hpi, q, s)) / (s * q)
    h_today = abs(h0) ** 2                                  # a_0 = 1 ⇒ |h_s(τ_0)|² = |h0|²
    eq13 = -((math.pi * beta_s / A_IN) ** 2) * h_today
    # The neglected late-time term is +(ℋ/a)²|h0|² = |h0|²/(τ² a²) (V4: τ ≫ τ_*).
    late = h_today / (tau**2 * (A_IN * tau / TAU_IN) ** 2)
    assert delta == pytest.approx(eq13 + late, rel=1e-12, abs=0)
    assert abs(late / eq13) < 1e-12


@pytest.mark.parametrize("b_chi", [-0.5, 0.3])
@pytest.mark.parametrize("chi", [-0.2, 0.0, 0.6])
def test_helicity_sum_carries_the_eq15_factor(b_chi: float, chi: float) -> None:
    # |h_±(τ_0)|² from Ω_gw,0 and Eq. 12; Σ_s s q (Δ bracket) ∝ [2b_χ + (1 + b_χ²)χ].
    q, H0, omega = 5.0, 1.0e-3, 1.0e-6
    tot = 0.0
    for s in (+1.0, -1.0):
        h2 = 3.0 * H0**2 * (1.0 + s * chi) / 2.0 * omega / (2.0 * math.pi * q**5)
        beta_s = BETA * (1.0 + s * b_chi)
        hi, hpi = _v4_mode(TAU_IN, q, beta_s, complex(math.sqrt(h2), 0.0))
        hf, hpf = _v4_mode(1.0e4, q, beta_s, complex(math.sqrt(h2), 0.0))
        tot += boundary_bracket(hf, hpf, q, s) - boundary_bracket(hi, hpi, q, s)
    # Σ_s s (1 + s b_χ)² (1 + s χ) = 2 [2b_χ + (1 + b_χ²) χ]; |h_s|² = 3H₀²(1 + sχ)Ω/(4πq⁵).
    expected = -q * (math.pi * BETA / A_IN) ** 2 * 3.0 * H0**2 * omega / (2.0 * math.pi * q**5) * (
        2.0 * b_chi + (1.0 + b_chi**2) * chi
    )
    assert tot == pytest.approx(expected, rel=1e-9, abs=1e-30)


def test_linearised_helicity_sum_is_the_exact_odd_part() -> None:
    # B is quadratic in h, so Σ_λ B(h₀ + λδh) is exactly linear in δh: M4's
    # first-order (in the CS coupling) sum loses nothing at that order.
    rng = np.random.default_rng(1)
    for _ in range(20):
        h0, hp0, dh, dhp = (complex(*rng.normal(size=2)) for _ in range(4))
        k = float(rng.uniform(0.1, 10.0))
        direct = sum(boundary_bracket(h0 + lam * dh, hp0 + lam * dhp, k, lam) for lam in (1.0, -1.0))
        assert _odd_bracket(h0, hp0, dh, dhp, k) == pytest.approx(direct, rel=1e-12, abs=1e-12)
