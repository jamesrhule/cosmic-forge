"""M2 — Scalar field sector.

Potentials are canonical (Starobinsky, natural, hilltop) plus a
``custom`` hook that accepts a source string from the frontend
``RunConfig.potential.customPython``: one sympy expression in ``phi``
(the canonical form), or ``def V(<name>): return <expr>`` (LEDGER,
JAMES DECISION 17). It is parsed with ``ast``, allow-listed and bounded
before sympy evaluates it (``potentials``), and compiled with
``sympy.lambdify(..., modules='jax')`` when JAX is available; otherwise
it falls back to numpy. ``check.check_potential`` is the API's
submit-time check (a custom potential compiles in a time-limited child).

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
