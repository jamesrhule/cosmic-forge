"""Scalar potentials + safe ``custom`` compiler.

The ``custom`` kind accepts a Python snippet that defines a
``V(phi, **params)`` function using only the symbols exposed in
``_SAFE_SYMPY_NS``. We parse with sympy (NOT exec) to avoid arbitrary
code execution on the server.
"""

from __future__ import annotations

import ast
import math
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


# Size limits on a custom potential (SEC-L3). ``sympify`` evaluates constant
# arithmetic eagerly, so ``phi**(9**9**9)`` would hang the worker computing
# 9**9**9 before any physics runs. Real potentials are a few dozen nodes with
# small powers and Planck-unit constants.
MAX_CUSTOM_SOURCE_CHARS = 4096
MAX_CUSTOM_AST_NODES = 512
MAX_CUSTOM_EXPONENT = 64
MAX_CUSTOM_LITERAL = 1e30
MAX_CUSTOM_CONSTANT_DIGITS = 1000

_LOG10_MAX_EXPONENT = math.log10(MAX_CUSTOM_EXPONENT)


def _constant_digits(node: ast.AST) -> float | None:
    """Upper bound on log10|value| of a constant-only subtree; None if it has a name or call."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return math.log10(max(abs(node.value), 1.0))
    if isinstance(node, ast.UnaryOp):
        return _constant_digits(node.operand)
    if isinstance(node, ast.BinOp):
        left, right = _constant_digits(node.left), _constant_digits(node.right)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Pow):
            # |b**e| <= |b|**|e|; the exponent bound itself is checked separately.
            return left * 10.0 ** min(right, 308.0)
        if isinstance(node.op, ast.Add | ast.Sub):
            return max(left, right) + 1.0
        return left + right  # Mult, Div, FloorDiv, Mod: digits add at most
    return None


def _check_custom_size(tree: ast.Expression) -> None:
    """Reject expressions whose evaluation could blow up before physics runs."""
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_CUSTOM_AST_NODES:
        raise ValueError(f"custom potential: expression too large (> {MAX_CUSTOM_AST_NODES} nodes)")
    for node in nodes:
        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValueError(f"custom potential: literal {value!r} not allowed")
            if abs(value) > MAX_CUSTOM_LITERAL:
                raise ValueError(f"custom potential: numeric literals must satisfy |x| <= {MAX_CUSTOM_LITERAL:g}")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            exponent = _constant_digits(node.right)
            if exponent is not None and exponent > _LOG10_MAX_EXPONENT:
                raise ValueError(f"custom potential: constant exponents must satisfy |x| <= {MAX_CUSTOM_EXPONENT}")
        digits = _constant_digits(node)
        if digits is not None and digits > MAX_CUSTOM_CONSTANT_DIGITS:
            raise ValueError(
                f"custom potential: a constant subexpression exceeds {MAX_CUSTOM_CONSTANT_DIGITS} digits"
            )


def _custom_expr(source: str, symbols: dict[str, sp.Symbol] | None = None) -> sp.Expr:
    """Parse a user-supplied ``V(phi, ...)`` body into a sympy Expr.

    The string must contain a single Python expression (no statements,
    no imports). We validate with ``ast`` before handing to
    ``sympy.sympify`` so arbitrary calls cannot leak in, and cap its size,
    literal magnitudes and exponents so parsing can't hang (SEC-L3).
    """
    if len(source) > MAX_CUSTOM_SOURCE_CHARS:
        raise ValueError(f"custom potential: source longer than {MAX_CUSTOM_SOURCE_CHARS} characters")
    tree = ast.parse(source.strip(), mode="eval")
    _check_custom_size(tree)
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
    # Parse into the *same* symbols compile_potential differentiates and
    # lambdifies with (``real=True``). Plain sympify would create distinct
    # assumption-free Symbols, making V′ ≡ V″ ≡ 0 and leaving parameters
    # unbound (P1-02 found this).
    return sp.sympify(source, locals={**_SAFE_SYMPY_NS, **(symbols or {})})


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
        expr = _custom_expr(
            pot.customPython,
            {"phi": phi, **{str(p): p for p in params}},
        )
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
