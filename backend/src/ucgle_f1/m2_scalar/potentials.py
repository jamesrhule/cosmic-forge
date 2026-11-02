"""Scalar potentials + safe ``custom`` compiler.

The ``custom`` kind accepts one Python expression in ``phi`` and its
parameters, using only the functions in ``_SAFE_FUNCTIONS``. It is parsed
with :mod:`ast` (never ``exec``, never sympy's string parser), checked and
bounded node by node, and only then evaluated with sympy (SEC-L3).
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
import sympy as sp

from ..domain import HILLTOP_P_DEFAULT, Potential

# Functions a custom potential may call (one positional argument each), and
# its one named constant. ``Rational(p, q)`` is also allowed, with integer
# literals only. Nothing else is callable and no other name means anything
# but a parameter symbol (SEC-L3).
_SAFE_FUNCTIONS: dict[str, Callable[[sp.Expr], sp.Expr]] = {
    "sqrt": sp.sqrt,
    "log": sp.log,
    "exp": sp.exp,
    "sin": sp.sin,
    "cos": sp.cos,
    "tanh": sp.tanh,
    "cosh": sp.cosh,
    "sinh": sp.sinh,
}
_SAFE_CONSTANTS: dict[str, sp.Expr] = {"pi": sp.pi}
_RATIONAL = "Rational"
# The whole namespace a snippet can refer to (kept for callers that list it).
_SAFE_SYMPY_NS: dict[str, object] = {**_SAFE_FUNCTIONS, **_SAFE_CONSTANTS, _RATIONAL: sp.Rational}


@dataclass
class ScalarModel:
    """Compiled scalar sector for a given potential."""

    V: Callable[..., np.ndarray]
    Vp: Callable[..., np.ndarray]
    Vpp: Callable[..., np.ndarray]
    symbolic_V: sp.Expr
    param_names: tuple[str, ...]


# Size limits on a custom potential (SEC-L3). Sympy evaluates exact
# arithmetic eagerly, so ``phi**(9**9**9)`` (or ``Rational(9)**…``, a power
# hidden behind a cancelling symbol, ``exp(k*log(9))``…) would hang the
# process computing a huge integer before any physics runs. Real potentials
# are a few dozen nodes with small powers and Planck-unit constants.
MAX_CUSTOM_SOURCE_CHARS = 4096
MAX_CUSTOM_AST_NODES = 512
MAX_CUSTOM_DEPTH = 32
MAX_CUSTOM_EXPONENT = 64
MAX_CUSTOM_LITERAL = 1e30
MAX_CUSTOM_CONSTANT_DIGITS = 1000

_LOG10_MAX_EXPONENT = math.log10(MAX_CUSTOM_EXPONENT)
_LOG10_E = math.log10(math.e)
_LN_10 = math.log(10.0)
_FAMILY = {ast.Add: "add", ast.Sub: "add", ast.Mult: "mul", ast.Div: "mul", ast.Pow: "pow"}


def _reject(why: str) -> ValueError:
    return ValueError(f"custom potential: {why}")


def _finite_or_inf(x: float) -> float:
    return math.inf if math.isnan(x) else x


@dataclass(frozen=True)
class _Bound:
    """What evaluating a subtree can produce, bounded before anything is evaluated.

    ``digits``: decimal digits of any exact (Integer/Rational) number sympy may
    build from it. ``hi``/``lo``: bounds on log10|v| of any non-zero number it
    may evaluate to. A symbol counts as 0 digits and |v| = 1, which covers the
    numbers a cancelling symbol leaves behind (``phi - phi``, ``phi/phi``), so
    the bounds hold even where a symbolic-looking subtree turns out constant.
    ``has_log``: a ``log`` call occurs below (``exp(k*log(x))`` is ``x**k``).
    """

    digits: float
    hi: float
    lo: float
    has_log: bool = False


def _within_digits(bound: _Bound) -> _Bound:
    if _finite_or_inf(bound.digits) > MAX_CUSTOM_CONSTANT_DIGITS:
        raise _reject(f"a constant subexpression may exceed {MAX_CUSTOM_CONSTANT_DIGITS} digits")
    return bound


def _int_digits(value: int) -> int:
    return len(str(abs(value)))


def _literal_bound(value: object) -> _Bound:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _reject(f"literal {value!r} not allowed")
    if not math.isfinite(value) or abs(value) > MAX_CUSTOM_LITERAL:
        raise _reject(f"numeric literals must satisfy |x| <= {MAX_CUSTOM_LITERAL:g}")
    if value == 0:
        return _Bound(digits=1, hi=0.0, lo=0.0)
    mag = math.log10(abs(value))
    # A float literal is a sympy Float: inexact, so it never grows exact digits.
    return _Bound(digits=_int_digits(value) if isinstance(value, int) else 0, hi=mag, lo=mag)


def _rational_arg(node: ast.AST) -> int:
    inner, sign = node, 1
    if isinstance(inner, ast.UnaryOp) and isinstance(inner.op, ast.USub | ast.UAdd):
        sign = -1 if isinstance(inner.op, ast.USub) else 1
        inner = inner.operand
    if not (isinstance(inner, ast.Constant) and type(inner.value) is int):
        raise _reject("Rational() takes integer literals only")
    if abs(inner.value) > MAX_CUSTOM_LITERAL:
        raise _reject(f"numeric literals must satisfy |x| <= {MAX_CUSTOM_LITERAL:g}")
    return sign * inner.value


def _chain(node: ast.BinOp) -> tuple[ast.AST, list[tuple[ast.operator, ast.AST]]]:
    """Unroll a left-nested run of one family (``a + b - c``, ``a*b/c``) without recursion.

    Sympy flattens these into one Add/Mul, so a long sum is one level deep.
    """
    family = _FAMILY[type(node.op)]
    rest: list[tuple[ast.operator, ast.AST]] = []
    cur: ast.AST = node
    while isinstance(cur, ast.BinOp) and family != "pow" and _FAMILY.get(type(cur.op)) == family:
        rest.append((cur.op, cur.right))
        cur = cur.left
    if not rest:  # a power: one operation
        return node.left, [(node.op, node.right)]
    rest.reverse()
    return cur, rest


def _check_shape(tree: ast.Expression) -> None:
    """Node count and nesting depth, iteratively (no recursion on hostile input).

    The left spine of a sum or product (``a + b + c``) is one level, as in
    sympy; every other nesting (a power, a call, parentheses around a
    different operation) is one more.
    """
    count = 0
    stack: list[tuple[ast.AST, int]] = [(tree.body, 1)]
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > MAX_CUSTOM_AST_NODES:
            raise _reject(f"expression too large (> {MAX_CUSTOM_AST_NODES} nodes)")
        if depth > MAX_CUSTOM_DEPTH:
            raise _reject(f"expression nested deeper than {MAX_CUSTOM_DEPTH} levels")
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr_context | ast.operator | ast.unaryop):
                continue
            same_run = (
                isinstance(node, ast.BinOp) and isinstance(child, ast.BinOp) and child is node.left
                and _FAMILY.get(type(node.op)) in ("add", "mul")
                and _FAMILY.get(type(child.op)) == _FAMILY.get(type(node.op))
            )
            stack.append((child, depth if same_run else depth + 1))


class _Checker:
    """Walk the parsed, unevaluated tree: allow-list every node and bound it (SEC-L3).

    Nothing is evaluated here; :func:`_build` evaluates the same tree only
    after every node passed.
    """

    def __init__(self, symbols: dict[str, sp.Symbol]) -> None:
        self.symbols = symbols

    def visit(self, node: ast.AST) -> _Bound:
        return _within_digits(self._visit(node))

    def _visit(self, node: ast.AST) -> _Bound:
        if isinstance(node, ast.Constant):
            return _literal_bound(node.value)
        if isinstance(node, ast.Name):
            if node.id in _SAFE_FUNCTIONS or node.id == _RATIONAL:
                raise _reject(f"'{node.id}' must be called")
            if node.id in _SAFE_CONSTANTS and node.id not in self.symbols:
                return _Bound(digits=1, hi=0.5, lo=0.49)
            return _Bound(digits=0, hi=0.0, lo=0.0)
        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, ast.USub | ast.UAdd):
                raise _reject(f"operator {type(node.op).__name__} not allowed")
            return self.visit(node.operand)
        if isinstance(node, ast.BinOp):
            return self._binop(node)
        if isinstance(node, ast.Call):
            return self._call(node)
        if isinstance(node, ast.Attribute):
            raise _reject("imports / attributes not allowed")
        raise _reject(f"{type(node).__name__} not allowed")

    def _binop(self, node: ast.BinOp) -> _Bound:
        for sub in (node, node.left, node.right):
            if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitXor):
                raise _reject("'^' is not allowed; write powers with '**'")
            if isinstance(sub, ast.BinOp) and type(sub.op) not in _FAMILY:
                raise _reject(f"operator {type(sub.op).__name__} not allowed")
        first, rest = _chain(node)
        acc = self.visit(first)
        for op, rhs in rest:
            acc = _within_digits(self._combine(acc, op, self.visit(rhs)))
        return acc

    @staticmethod
    def _combine(a: _Bound, op: ast.operator, b: _Bound) -> _Bound:
        log = a.has_log or b.has_log
        if isinstance(op, ast.Add | ast.Sub):
            digits = a.digits + b.digits + 1
            return _Bound(digits, max(a.hi, b.hi) + math.log10(2.0), -digits, log)
        if isinstance(op, ast.Mult):
            return _Bound(a.digits + b.digits, a.hi + b.hi, a.lo + b.lo, log)
        if isinstance(op, ast.Div):
            hi, lo = _finite_or_inf(a.hi - b.lo), _finite_or_inf(a.lo - b.hi)
            return _Bound(a.digits + b.digits, hi, lo, log)
        # Pow: every exponent is bounded, whether or not it looks constant.
        if not _finite_or_inf(b.hi) <= _LOG10_MAX_EXPONENT + 1e-12:
            raise _reject(f"exponents must satisfy |x| <= {MAX_CUSTOM_EXPONENT}")
        e_max = 10.0 ** b.hi
        size = _finite_or_inf(max(abs(a.hi), abs(a.lo)) * e_max)
        return _Bound(a.digits * e_max + b.digits, size, -size, log)

    def _call(self, node: ast.Call) -> _Bound:
        func = node.func
        allowed = isinstance(func, ast.Name) and (func.id in _SAFE_FUNCTIONS or func.id == _RATIONAL)
        if not allowed or not isinstance(func, ast.Name):
            raise _reject(f"call to '{ast.dump(func)}' not allowed")
        if node.keywords:
            raise _reject(f"{func.id}() takes no keyword arguments")
        if func.id == _RATIONAL:
            if not 1 <= len(node.args) <= 2:
                raise _reject("Rational() takes one or two integer literals")
            p, q = (_rational_arg(a) for a in (*node.args, ast.Constant(1))[:2])
            if q == 0:
                raise _reject("Rational() with a zero denominator")
            if p == 0:
                return _Bound(digits=1 + _int_digits(q), hi=0.0, lo=0.0)
            mag = math.log10(abs(p)) - math.log10(abs(q))
            return _Bound(_int_digits(p) + _int_digits(q), mag, mag)
        if len(node.args) != 1 or isinstance(node.args[0], ast.Starred):
            raise _reject(f"{func.id}() takes exactly one argument")
        c = self.visit(node.args[0])
        size = max(abs(c.hi), abs(c.lo))
        if func.id == "sqrt":
            return _Bound(2 * c.digits + 1, c.hi / 2, c.lo / 2, c.has_log)
        if func.id == "log":
            mag = math.log10(_LN_10 * size + 1.0)
            return _Bound(c.digits + 1, mag, -math.inf, True)
        # Of a log, sympy rewrites these algebraically (tanh(log(x)) is
        # (x**2 - 1)/(x**2 + 1), exp(k*log(x)) is x**k): bound them as such.
        digits = 2 * c.digits + 2 if c.has_log else c.digits + 1
        if func.id in ("sin", "cos", "tanh"):
            return _Bound(digits, 0.0, -math.inf, c.has_log)
        # exp, sinh, cosh: the factor k of a log below is an exponent.
        if c.has_log and not _finite_or_inf(c.hi) <= _LOG10_MAX_EXPONENT + 1e-12:
            raise _reject(f"exp() of a log: the factor must satisfy |x| <= {MAX_CUSTOM_EXPONENT}")
        mag = _LOG10_E * 10.0 ** min(c.hi, 300.0)
        grow = MAX_CUSTOM_EXPONENT if c.has_log else 1
        return _Bound(digits * grow, mag, min(-mag, c.lo), c.has_log)


def _build(node: ast.AST, source: str, symbols: dict[str, sp.Symbol]) -> sp.Expr:
    """Evaluate a checked tree with sympy, node by node as ``sympify`` would."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int):
            return sp.Integer(node.value)
        text = ast.get_source_segment(source, node) or repr(node.value)
        return sp.Float(text.replace("_", ""))
    if isinstance(node, ast.Name):
        if node.id in symbols:
            return symbols[node.id]
        if node.id in _SAFE_CONSTANTS:
            return _SAFE_CONSTANTS[node.id]
        return sp.Symbol(node.id)
    if isinstance(node, ast.UnaryOp):
        operand = _build(node.operand, source, symbols)
        return -operand if isinstance(node.op, ast.USub) else +operand
    if isinstance(node, ast.BinOp):
        first, rest = _chain(node)
        acc = _build(first, source, symbols)
        for op, rhs in rest:
            b = _build(rhs, source, symbols)
            if isinstance(op, ast.Add):
                acc = acc + b
            elif isinstance(op, ast.Sub):
                acc = acc - b
            elif isinstance(op, ast.Mult):
                acc = acc * b
            elif isinstance(op, ast.Div):
                acc = acc / b
            else:
                acc = acc**b
        return acc
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == _RATIONAL:
            return sp.Rational(*(_rational_arg(a) for a in node.args))
        return _SAFE_FUNCTIONS[node.func.id](_build(node.args[0], source, symbols))
    raise _reject(f"{type(node).__name__} not allowed")  # unreachable after _Checker


def _custom_expr(source: str, symbols: dict[str, sp.Symbol] | None = None) -> sp.Expr:
    """Parse a user-supplied ``V(phi, ...)`` body into a sympy Expr.

    The string must contain a single Python expression (no statements, no
    imports). Sympy never parses or evaluates the raw string (SEC-L3):
    Python's ``ast`` parses it once (``^`` stays XOR and is refused), the
    unevaluated tree is allow-listed and bounded node by node (literals,
    every exponent, the digits any exact subexpression can reach, the
    ``exp``/``log`` rewrite, node count and depth), and only then is that
    same tree evaluated with sympy's operators.
    """
    if len(source) > MAX_CUSTOM_SOURCE_CHARS:
        raise _reject(f"source longer than {MAX_CUSTOM_SOURCE_CHARS} characters")
    text = source.strip()
    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, ValueError, MemoryError, RecursionError) as exc:
        # A statement (``def V(psi): ...``, an assignment) is not an expression.
        detail = type(exc).__name__
        if isinstance(exc, SyntaxError):
            detail = f"{exc.msg}, line {exc.lineno}"
        msg = f"custom potential: customPython must be one expression in phi ({detail})"
        raise ValueError(msg) from exc
    # Parse into the *same* symbols compile_potential differentiates and
    # lambdifies with (``real=True``). Distinct assumption-free Symbols
    # would make V′ ≡ V″ ≡ 0 and leave parameters unbound (P1-02 found this).
    names = dict(symbols or {})
    _check_shape(tree)
    _Checker(names).visit(tree.body)
    return _build(tree.body, text, names)


def compile_potential(pot: Potential) -> ScalarModel:
    """Compile ``pot`` in M2's units (W1-PARAMS: API units are converted
    once, by :meth:`Potential.engine`; a converted potential is not touched)."""
    pot = pot.engine()
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
        # V0 (1 − (φ/μ)^p). p is an integer exponent baked into the expression
        # (not a lambdify argument); p = 4, the default, is the original
        # hilltop expression, symbol for symbol.
        p = int(pot.params.get("p", HILLTOP_P_DEFAULT))
        expr = V0 * (1 - (phi / mu) ** p)
        param_names = ("V0", "mu")
        params = (V0, mu)
    elif pot.kind == "custom":
        if not pot.customPython:
            raise ValueError("custom potential requires customPython body")
        expr = _custom_expr(
            pot.customPython,
            {"phi": phi, **{str(p): p for p in params}},
        )
        unbound = sorted(
            str(s) for s in expr.free_symbols if s != phi and str(s) not in pot.params
        )
        if unbound:
            # Unbound names would only fail when V is first evaluated.
            msg = f"custom potential: unbound parameter(s) {unbound}; add them to params"
            raise ValueError(msg)
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
