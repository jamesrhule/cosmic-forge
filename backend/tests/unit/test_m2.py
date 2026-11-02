"""M2 scalar potential tests."""

from __future__ import annotations

import pytest

from ucgle_f1.domain import Potential
from ucgle_f1.m2_scalar import build_scalar_model


def test_starobinsky_compiles() -> None:
    m = build_scalar_model(Potential(kind="starobinsky", params={"M": 1.0e-5}))
    v = m.V(0.5, 1.0e-5)
    assert float(v) >= 0.0


def test_natural_compiles() -> None:
    m = build_scalar_model(Potential(kind="natural",
                                     params={"f_a": 1.0, "Lambda": 1.0e-3}))
    v = m.V(0.1, 1.0, 1.0e-3)
    assert float(v) >= 0.0


def test_custom_rejects_imports() -> None:
    with pytest.raises(ValueError):
        build_scalar_model(Potential(
            kind="custom", params={},
            customPython="__import__('os').system('rm -rf /')",
        ))


def test_custom_accepts_safe_expression() -> None:
    m = build_scalar_model(Potential(
        kind="custom", params={"a": 1.0, "b": 0.5},
        customPython="a * phi**2 + b * cos(phi)",
    ))
    assert m.symbolic_V is not None


def test_custom_potential_derivatives_are_symbolic_in_phi() -> None:
    # Regression (P1-02): custom potentials must differentiate in φ and bind
    # their parameters; V = m²φ²/2 ⇒ V′ = m²φ, V″ = m².
    m = build_scalar_model(Potential(kind="custom", params={"m": 1.0e-6}, customPython="m**2*phi**2/2"))
    assert float(m.V(2.0, 1.0e-6)) == pytest.approx(2.0e-12, rel=1e-12, abs=0)
    assert float(m.Vp(2.0, 1.0e-6)) == pytest.approx(2.0e-12, rel=1e-12, abs=0)
    assert float(m.Vpp(2.0, 1.0e-6)) == pytest.approx(1.0e-12, rel=1e-12, abs=0)
    assert float(m.Vp(2.0, 2.0e-6)) == pytest.approx(8.0e-12, rel=1e-12, abs=0)
