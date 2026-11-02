"""W1-PARAMS: the API's potential parameters and their one conversion to M2.

JAMES DECISION 11: internal units are reduced-Planck, M_Pl = M_PL_GEV GeV = 1;
GeV appears only at the API boundary. ``Potential.engine()`` is the one
conversion, with the one M_Pl (``m1_background.background.M_PL_GEV``).
"""

from __future__ import annotations

import re

import numpy as np
import pytest
import sympy as sp
from pydantic import ValidationError

from ucgle_f1 import domain
from ucgle_f1.domain import EnginePotential, Potential
from ucgle_f1.m1_background.background import M_PL_GEV
from ucgle_f1.m2_scalar import compile_potential
from ucgle_f1.m7_infer.couplings import initial_field


def test_the_conversion_uses_the_one_m_pl() -> None:
    assert M_PL_GEV == 2.4352e18
    assert not hasattr(domain, "M_PL_GEV"), "domain imports M_PL_GEV, never defines its own"


def test_natural_configurator_form_converts_to_m2_units() -> None:
    eng = Potential(kind="natural", params={"f": 7e16, "Lambda4": 2.5e-7}).engine()
    assert set(eng.params) == {"f_a", "Lambda"}
    assert eng.params["f_a"] == 7e16 / M_PL_GEV
    assert eng.params["f_a"] == pytest.approx(0.028745072273324573, rel=1e-15)
    assert eng.params["Lambda"] == 2.5e-7 ** 0.25
    assert eng.params["Lambda"] ** 4 == pytest.approx(2.5e-7, rel=1e-15)
    assert eng.params["Lambda"] == pytest.approx(0.022360679774997897, rel=1e-15)


def test_hilltop_converts_mu_and_keeps_v0_and_p() -> None:
    eng = Potential(kind="hilltop", params={"V0": 1e-7, "mu": 1e16, "p": 4}).engine()
    assert eng.params == {"V0": 1e-7, "mu": 1e16 / M_PL_GEV, "p": 4.0}


@pytest.mark.parametrize("pot", [
    Potential(kind="natural", params={"f_a": 8.7, "Lambda": 0.0071154324599829784}),
    Potential(kind="starobinsky", params={"M": 1.3e-5}),
    Potential(kind="custom", params={"m": 1e-6}, customPython="m**2*phi**2/2"),
    Potential(kind="natural", params={"f_a": 1.0, "Lambda": 1e-3, "phi0": 2.0}),
], ids=["natural-M2", "starobinsky", "custom", "phi0"])
def test_m_pl_parameters_pass_through_bit_for_bit(pot: Potential) -> None:
    eng = pot.engine()
    assert eng.params == pot.params
    assert all(eng.params[k] is pot.params[k] for k in pot.params)
    assert (eng.kind, eng.customPython) == (pot.kind, pot.customPython)


def test_engine_is_idempotent_so_nothing_is_converted_twice() -> None:
    eng = Potential(kind="hilltop", params={"V0": 1e-7, "mu": 1e16}).engine()
    assert isinstance(eng, EnginePotential)
    assert eng.engine() is eng
    assert compile_potential(eng).symbolic_V == compile_potential(
        Potential(kind="hilltop", params={"V0": 1e-7, "mu": 1e16}),
    ).symbolic_V
    # initial_field (φ₀ = 10⁻³ μ) sees μ in M_Pl whether given the API or M2 form.
    api = Potential(kind="hilltop", params={"V0": 1e-7, "mu": 1e16})
    assert initial_field(api) == initial_field(eng) == 1e-3 * (1e16 / M_PL_GEV)


@pytest.mark.parametrize(("kind", "params", "message"), [
    ("natural", {"f": 7e16, "Lambda4": 2.5e-7, "f_a": 1.0, "Lambda": 1e-3}, "ambiguous parameters"),
    ("natural", {"f": 7e16, "Lambda": 1e-3}, "ambiguous parameters"),
    ("natural", {"f": 0.0, "Lambda4": 2.5e-7}, "f [GeV] must be positive"),
    ("natural", {"f_a": -1.0, "Lambda": 1e-3}, "f_a [M_Pl] must be positive"),
    ("natural", {"f": float("nan"), "Lambda4": 2.5e-7}, "f must be finite"),
    ("natural", {"F": 7e16}, "unknown parameter(s) ['F']"),
    ("starobinsky", {"M": -1e-5}, "M [M_Pl] must be positive"),
    ("hilltop", {"V0": 1e-7, "mu": 1e16, "p": 4.5}, "p must be an integer from 2 to 64"),
    ("hilltop", {"V0": 1e-7, "mu": 1e16, "p": 1}, "p must be an integer from 2 to 64"),
    ("hilltop", {"V0": 1e-7, "mu": 1e16, "Lambda": 1e-3}, "unknown parameter(s) ['Lambda']"),
    ("hilltop", {"V0": 0.0, "mu": 1e16}, "V0 [M_Pl^4] must be positive"),
], ids=["both-forms", "mixed", "zero-f", "negative-f_a", "nan", "unknown", "negative-M",
        "fractional-p", "p-below-2", "hilltop-unknown", "zero-V0"])
def test_bad_parameters_are_refused_with_a_clear_message(
    kind: str, params: dict[str, float], message: str,
) -> None:
    with pytest.raises(ValidationError, match=re.escape(message)):
        Potential(kind=kind, params=params)  # type: ignore[arg-type]


def test_missing_parameters_are_named_in_the_form_the_client_used() -> None:
    assert Potential(kind="natural", params={"f": 7e16}).missing_params() == ["Lambda4 [M_Pl^4]"]
    assert Potential(kind="natural", params={"f_a": 1.0}).missing_params() == ["Lambda [M_Pl]"]
    assert Potential(kind="natural").missing_params() == ["f [GeV]", "Lambda4 [M_Pl^4]"]
    assert Potential(kind="hilltop", params={"mu": 1e16, "p": 4}).missing_params() == ["V0 [M_Pl^4]"]
    assert Potential(kind="hilltop", params={"V0": 1e-7, "mu": 1e16}).missing_params() == []
    assert Potential(kind="custom", customPython="phi**2").missing_params() == []


# ── hilltop: V0 (1 − (φ/μ)^p), p = 4 by default ──────────────────────


def _old_hilltop() -> sp.Expr:
    """M2's hilltop expression before W1-PARAMS, built the same way."""
    phi = sp.symbols("phi", real=True)
    V0, mu = sp.symbols("V0 mu", real=True, positive=True)
    return V0 * (1 - (phi / mu) ** 4)


def test_hilltop_p4_is_the_original_expression_symbol_for_symbol() -> None:
    old = _old_hilltop()
    for params in ({"V0": 1e-7, "mu": 0.5}, {"V0": 1e-7, "mu": 0.5, "p": 4.0}):
        m = compile_potential(Potential(kind="hilltop", params=params).engine())
        assert m.symbolic_V == old
        assert sp.srepr(m.symbolic_V) == sp.srepr(old)
        assert m.param_names == ("V0", "mu")


def test_hilltop_p4_values_are_bit_identical_to_the_original() -> None:
    phi_s = sp.symbols("phi", real=True)
    V0_s, mu_s = sp.symbols("V0 mu", real=True, positive=True)
    old = _old_hilltop()
    old_fns = [sp.lambdify((phi_s, V0_s, mu_s), e, modules="numpy")
               for e in (old, sp.diff(old, phi_s), sp.diff(old, phi_s, 2))]
    m = compile_potential(Potential(kind="hilltop", params={"V0": 1e-7, "mu": 0.5}).engine())
    phi = np.linspace(-0.4, 0.4, 101)
    for new_fn, old_fn in zip((m.V, m.Vp, m.Vpp), old_fns):
        np.testing.assert_array_equal(new_fn(phi, 1e-7, 0.5), old_fn(phi, 1e-7, 0.5))


def test_hilltop_power_is_the_configured_p() -> None:
    phi = sp.symbols("phi", real=True)
    V0, mu = sp.symbols("V0 mu", real=True, positive=True)
    m = compile_potential(Potential(kind="hilltop", params={"V0": 2.0, "mu": 0.5, "p": 6}).engine())
    assert m.symbolic_V == V0 * (1 - (phi / mu) ** 6)
    assert float(m.V(0.25, 2.0, 0.5)) == pytest.approx(2.0 * (1 - 0.5**6), rel=1e-15)
