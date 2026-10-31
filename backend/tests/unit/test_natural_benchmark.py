"""Kawai–Kim natural-inflation benchmark (JAMES DECISION 11): Λ from A_s."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from scipy.integrate import quad
from scipy.optimize import brentq

from ucgle_f1.domain import Potential
from ucgle_f1.m2_scalar import compile_potential
from ucgle_f1.m2_scalar.natural import (
    KK_A_S,
    KK_F_A,
    KK_N_E,
    kawai_kim_natural_params,
    natural_lambda_from_As,
    natural_mass,
    natural_phi_end,
    natural_phi_star,
)
from ucgle_f1.m7_infer.couplings import initial_field

_REPO = Path(__file__).resolve().parents[3]
_FIXTURE = _REPO / "public" / "fixtures" / "runs" / "kawai-kim-natural.json"


def _numeric_As(f_a: float, Lam: float, N_e: float) -> float:
    """A_s from M2's compiled potential, independently of the closed forms:
    root-find ε_V = 1, integrate N = ∫ V/V′ dφ by quadrature, root-find the
    pivot, then A_s = V / (24π² ε_V)."""
    m = compile_potential(Potential(kind="natural", params={"f_a": f_a, "Lambda": Lam}))

    def V(p: float) -> float:
        return float(m.V(p, f_a, Lam))

    def Vp(p: float) -> float:
        return float(m.Vp(p, f_a, Lam))

    def eps(p: float) -> float:
        return 0.5 * (Vp(p) / V(p)) ** 2

    # Bracket away from the hilltop, where V/V′ has a non-integrable pole;
    # for f_a = 8.7 the bracket's top is ≈ 280 e-folds before the end.
    hi = 0.9 * math.pi * f_a
    phi_end = brentq(lambda p: eps(p) - 1.0, 1e-6 * f_a, hi, xtol=1e-15, rtol=1e-15)

    def N(p: float) -> float:
        return quad(lambda q: V(q) / Vp(q), phi_end, p, epsabs=0.0, epsrel=1e-13, limit=200)[0]

    phi_star = brentq(lambda p: N(p) - N_e, phi_end, hi, xtol=1e-14, rtol=1e-15)
    return V(phi_star) / (24.0 * math.pi**2 * eps(phi_star))


def test_lambda_reproduces_As_at_60_efolds() -> None:
    lam = natural_lambda_from_As(KK_F_A, KK_A_S, KK_N_E)
    assert _numeric_As(KK_F_A, lam, KK_N_E) == pytest.approx(KK_A_S, rel=1e-9)


def test_inflaton_mass_is_about_5e_minus_6() -> None:
    p = kawai_kim_natural_params()
    m = natural_mass(p["f_a"], p["Lambda"])
    # Decision 11 quotes m ≈ 5e-6 M_Pl (one significant figure); slow roll
    # gives 5.82e-6 M_Pl. Pinned to round-off, plus the quoted scale.
    assert m == pytest.approx(5.819468861216026e-06, rel=1e-12)
    assert m == pytest.approx(5.0e-6, rel=0.2)


def test_closed_forms_are_consistent() -> None:
    f = KK_F_A
    pe = natural_phi_end(f)
    eps_end = 0.5 * (math.sin(pe / f) / (f * (1.0 - math.cos(pe / f)))) ** 2
    assert eps_end == pytest.approx(1.0, rel=1e-13)
    assert natural_phi_star(f, 0.0) == pytest.approx(pe, rel=1e-13)
    assert pe < natural_phi_star(f, KK_N_E) < math.pi * f


def test_fixture_carries_the_benchmark_parameters() -> None:
    blob = json.loads(_FIXTURE.read_text())
    pot = blob["config"]["potential"]
    assert pot["kind"] == "natural"
    assert set(pot["params"]) == {"f_a", "Lambda"}
    assert pot["params"] == kawai_kim_natural_params()
    assert blob["synthetic"] is True


def test_natural_initial_field_is_the_pivot_for_the_benchmark() -> None:
    p = kawai_kim_natural_params()
    phi0 = initial_field(Potential(kind="natural", params=p))
    assert phi0 == natural_phi_star(KK_F_A, KK_N_E)
    # Sub-Planckian f_a keeps the hilltop bound (slow roll fails there).
    small = initial_field(Potential(kind="natural", params={"f_a": 1.0, "Lambda": 1e-3}))
    assert small == math.pi * (1.0 - 1.0e-6)
