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
