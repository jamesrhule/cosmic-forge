"""M2 — Scalar field sector.

Potentials are canonical (Starobinsky, natural, hilltop) plus a
``custom`` hook that accepts a Python source string from the
frontend ``RunConfig.potential.customPython``. The string is parsed
through sympy and compiled with ``sympy.lambdify(..., modules='jax')``
when JAX is available; otherwise it falls back to numpy.

Symbolic derivation (V(φ), V'(φ), V''(φ)) uses
``sympy.diffgeom`` + ``sympy`` so the same AST feeds the EOM, the
anomaly (M4) and the mode equation (M3).
"""

from __future__ import annotations

from .potentials import (
    ScalarModel,
    build_scalar_model,
    compile_potential,
)

__all__ = ["ScalarModel", "build_scalar_model", "compile_potential"]
