"""Scalar potentials + safe ``custom`` compiler.

The ``custom`` kind accepts a Python snippet that defines a
``V(phi, **params)`` function using only the symbols exposed in
``_SAFE_SYMPY_NS``. We parse with sympy (NOT exec) to avoid arbitrary
code execution on the server.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Callable

import numpy as np
import sympy as sp

from ..domain import Potential

# Symbols allowed inside a custom potential expression.
_SAFE_SYMPY_NS: dict[str, object] = {
    "sqrt": sp.sqrt,
    "log": sp.log,
    "exp": sp.exp,
    "sin": sp.sin,
    "cos": sp.cos,
    "tanh": sp.tanh,
    "cosh": sp.cosh,
    "sinh": sp.sinh,
    "pi": sp.pi,
    "Rational": sp.Rational,
}


@dataclass
class ScalarModel:
    """Compiled scalar sector for a given potential."""

    V: Callable[..., np.ndarray]
    Vp: Callable[..., np.ndarray]
    Vpp: Callable[..., np.ndarray]
    symbolic_V: sp.Expr
    param_names: tuple[str, ...]


def _custom_expr(source: str) -> sp.Expr:
    """Parse a user-supplied ``V(phi, ...)`` body into a sympy Expr.

    The string must contain a single Python expression (no statements,
    no imports). We validate with ``ast`` before handing to
    ``sympy.sympify`` so arbitrary calls cannot leak in.
    """
    tree = ast.parse(source.strip(), mode="eval")
    # Walk; reject attribute access, calls to non-allowed names, etc.
    allowed_calls = set(_SAFE_SYMPY_NS)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if not isinstance(func, ast.Name) or func.id not in allowed_calls:
                raise ValueError(
                    f"custom potential: call to '{ast.dump(func)}' not allowed"
                )
        if isinstance(node, ast.Attribute | ast.Import | ast.ImportFrom):
            raise ValueError("custom potential: imports / attributes not allowed")
        if isinstance(node, ast.Name):
            # Free names will be interpreted as sympy symbols by sympify.
            pass
    return sp.sympify(source, locals=_SAFE_SYMPY_NS)


def compile_potential(pot: Potential) -> ScalarModel:
    phi = sp.symbols("phi", real=True)
    params = sp.symbols(sorted(pot.params.keys()) or ("_unused",), real=True)
    params = (params,) if isinstance(params, sp.Symbol) else params
    param_names = tuple(str(p) for p in params)

    if pot.kind == "starobinsky":
        M = sp.symbols("M", real=True, positive=True)
        expr = (3 * M**2 / 4) * (1 - sp.exp(-sp.sqrt(sp.Rational(2, 3)) * phi)) ** 2
        param_names = ("M",)
        params = (M,)
    elif pot.kind == "natural":
        f_a, Lam = sp.symbols("f_a Lambda", real=True, positive=True)
        expr = Lam**4 * (1 - sp.cos(phi / f_a))
        param_names = ("f_a", "Lambda")
        params = (f_a, Lam)
    elif pot.kind == "hilltop":
        V0, mu = sp.symbols("V0 mu", real=True, positive=True)
        expr = V0 * (1 - (phi / mu) ** 4)
        param_names = ("V0", "mu")
        params = (V0, mu)
    elif pot.kind == "custom":
        if not pot.customPython:
            raise ValueError("custom potential requires customPython body")
        expr = _custom_expr(pot.customPython)
    else:
        raise ValueError(f"Unknown potential kind: {pot.kind}")

    Vp = sp.diff(expr, phi)
    Vpp = sp.diff(Vp, phi)

    # Prefer JAX backend; gracefully fall back to numpy.
    try:
        import jax  # noqa: F401

        backend = "jax"
    except ImportError:
        backend = "numpy"

    V_fn = sp.lambdify((phi, *params), expr, modules=backend)
    Vp_fn = sp.lambdify((phi, *params), Vp, modules=backend)
    Vpp_fn = sp.lambdify((phi, *params), Vpp, modules=backend)

    return ScalarModel(
        V=V_fn,
        Vp=Vp_fn,
        Vpp=Vpp_fn,
        symbolic_V=expr,
        param_names=param_names,
    )


def build_scalar_model(pot: Potential) -> ScalarModel:
    """Public entrypoint — identical to :func:`compile_potential`."""
    return compile_potential(pot)
