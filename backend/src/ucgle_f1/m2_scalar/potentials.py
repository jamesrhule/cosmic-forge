"""Scalar potentials + safe ``custom`` compiler.

The ``custom`` kind takes one sympy expression in ``phi`` and its
parameters, the canonical form (LEDGER, JAMES DECISION 17), using only the
functions in ``_SAFE_FUNCTIONS``. A ``def V(<name>): return <expr>``
snippet (the shape main's Configurator saved) is also accepted: its one
return expression is extracted and ``<name>`` renamed to ``phi``. Any other
snippet is refused with a message that names the canonical form.

Either way the expression is parsed with :mod:`ast` (never ``exec``, never
sympy's string parser), checked and bounded node by node, and only then
evaluated with sympy (SEC-L3). The bounds cover exact numbers (digits) and
Floats (magnitude, with Float cancellation), keep every subexpression within
float64 (the physics lambdifies to it), and keep ``exp``/``sinh``/``cosh``
(and ``sin``/``cos``/``tanh`` of a possibly complex argument) within
float64's exponent range (W1 API3, round-2 WORKER verifier).
"""

from __future__ import annotations

import ast
import math
import sys
from dataclasses import dataclass, replace
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
# arithmetic and Floats eagerly, so ``phi**(9**9**9)`` (or ``Rational(9)**…``,
# a power hidden behind a cancelling symbol, ``exp(k*log(9))``,
# ``sin(exp(1e30))``, ``9**(1/(1.0000001 - 1.0))``…) would hang the process
# computing a huge number before any physics runs. Real potentials are a few
# dozen nodes with small powers and Planck-unit constants.
MAX_CUSTOM_SOURCE_CHARS = 4096
MAX_CUSTOM_AST_NODES = 512
MAX_CUSTOM_DEPTH = 32
MAX_CUSTOM_EXPONENT = 64
MAX_CUSTOM_LITERAL = 1e30
MAX_CUSTOM_CONSTANT_DIGITS = 1000
# The physics lambdifies V to float64: no subexpression may exceed float64's
# largest finite value, and exp (sinh, cosh) overflows it beyond this argument.
FLOAT64_MAX = sys.float_info.max
MAX_CUSTOM_LOG10_MAGNITUDE = math.log10(FLOAT64_MAX)
MAX_CUSTOM_EXP_ARGUMENT = math.log(FLOAT64_MAX)

# The canonical form, named in every refusal of the snippet's shape (D17).
CANONICAL_FORM = (
    "customPython must be one expression in phi, the canonical form "
    "(e.g. 'm**2*phi**2/2' or 'Lambda**4*(1 - cos(phi/f_a))'); "
    "'def V(<name>): return <expression>' is also accepted"
)

_LOG10_MAX_EXPONENT = math.log10(MAX_CUSTOM_EXPONENT)
_LOG10_MAX_EXP_ARGUMENT = math.log10(MAX_CUSTOM_EXP_ARGUMENT)
_LOG10_E = math.log10(math.e)
_LOG10_2 = math.log10(2.0)
_LN_10 = math.log(10.0)
# Rounding of one Float operation, in log10 (generous: 2**-50 relative).
_FLOAT_SLACK = 0.01
# How close a non-zero p-bit Float x comes to a zero of sin/cos (a multiple
# of pi/2): |x - k*pi/2| >= 2**-(2p + 16). The proven worst case over every
# double (p = 53, the whole exponent range) is about 2**-61, the known worst
# case for argument reduction; 2p + 16 bits leaves a wide margin for any p.
_TRIG_ZERO_BITS = (2, 16)
# An upper bound on the irrationality exponent of pi (Salikhov 2008: 7.6063),
# rounded up: |pi - N/D| > D**-8, so an exact argument with d digits is at
# least about 10**-(8*d) from a pole of tan (W1 R4-API, Decision-by-build).
_PI_IRRATIONALITY = 8.0
# log10(tanh(1)): |tanh x| >= tanh(1)*min(|x|, 1) for real x.
_LOG10_TANH_1 = math.log10(math.tanh(1.0))
# log10(2/pi): |sin x| >= (2/pi)*|x| for |x| <= pi/2.
_LOG10_2_OVER_PI = math.log10(2.0 / math.pi)
# Dominance margin of a sum, in log10 (the dominant term is >= 1.12x the rest).
_DOMINANCE = 0.05
_FAMILY = {ast.Add: "add", ast.Sub: "add", ast.Mult: "mul", ast.Div: "mul", ast.Pow: "pow"}


def _reject(why: str) -> ValueError:
    return ValueError(f"custom potential: {why}")


def _not_canonical(why: str) -> ValueError:
    return ValueError(f"custom potential: {CANONICAL_FORM}; {why}")


def _hi(x: float) -> float:
    """An upper bound: NaN (from ∞ − ∞) means unbounded."""
    return math.inf if math.isnan(x) else x


def _lo(x: float) -> float:
    """A lower bound: NaN (from ∞ − ∞) means unbounded below."""
    return -math.inf if math.isnan(x) else x


@dataclass(frozen=True)
class _Bound:
    """What evaluating a subtree can produce, bounded before anything is evaluated.

    ``digits``: decimal digits of any exact (Integer/Rational) number sympy may
    build from it. ``hi``/``lo``: bounds on log10|v| of any non-zero number it
    may evaluate to. A symbol counts as 0 digits and |v| = 1, which covers the
    numbers a cancelling symbol leaves behind (``phi - phi``, ``phi/phi``), so
    the bounds hold even where a symbolic-looking subtree turns out constant.
    ``has_log``: a ``log`` call occurs below (``exp(k*log(x))`` is ``x**k``).
    ``prec``: bits of the most precise Float below (0: exact or symbolic
    only); sympy evaluates Float arithmetic and functions of Floats eagerly.
    ``cplx``: it may be non-real (``sqrt``/``log``/a fractional power of a
    possibly negative number); ``sin(i·y)`` is ``i·sinh(y)``.
    ``nonneg``: it is real and ≥ 0 for every value of its symbols.
    """

    digits: float
    hi: float
    lo: float
    has_log: bool = False
    prec: int = 0
    cplx: bool = False
    nonneg: bool = False


def _within(bound: _Bound) -> _Bound:
    if _hi(bound.digits) > MAX_CUSTOM_CONSTANT_DIGITS:
        raise _reject(f"a constant subexpression may exceed {MAX_CUSTOM_CONSTANT_DIGITS} digits")
    if not _hi(bound.hi) <= MAX_CUSTOM_LOG10_MAGNITUDE:
        raise _reject(f"a subexpression may exceed {FLOAT64_MAX:.4g}, the largest float64")
    return bound


def _floor(b: _Bound) -> float:
    """A lower bound on log10|v| of any non-zero *number* sympy builds from ``b``.

    Without a Float below, sympy only builds Integers and Rationals of at most
    ``digits`` digits (|v| ≥ 10**-digits); everything else stays symbolic and
    is never evaluated. A Float subtree has its tracked ``lo``.
    """
    if b.prec:
        return _lo(b.lo)
    return max(_lo(b.lo), -(b.digits + 1.0))


def _int_digits(value: int) -> int:
    return len(str(abs(value)))


def _log10_abs(f: sp.Float) -> float:
    _sign, man, exp, _bc = f._mpf_
    return math.log10(man) + exp * _LOG10_2


def _literal_bound(value: object, text: str) -> _Bound:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _reject(f"literal {value!r} not allowed")
    if not math.isfinite(value) or abs(value) > MAX_CUSTOM_LITERAL:
        raise _reject(f"numeric literals must satisfy |x| <= {MAX_CUSTOM_LITERAL:g}")
    if isinstance(value, int):
        if value == 0:
            return _Bound(digits=1, hi=0.0, lo=0.0, nonneg=True)
        mag = math.log10(value)
        return _Bound(digits=_int_digits(value), hi=mag, lo=mag, nonneg=True)
    # A float literal is the sympy Float :func:`_build` makes from its text
    # (``1e-1000`` is 0.0 to Python but 1.0e-1000 to sympy): inexact, so it
    # never grows exact digits, at the precision its digits imply.
    f = sp.Float(text)
    if f.is_zero:
        return _Bound(digits=0, hi=0.0, lo=0.0, prec=f._prec, nonneg=True)
    mag = _log10_abs(f)
    if mag > math.log10(MAX_CUSTOM_LITERAL) + 1e-9:  # (1e30's text rounds a hair above)
        raise _reject(f"numeric literals must satisfy |x| <= {MAX_CUSTOM_LITERAL:g}")
    return _Bound(digits=0, hi=mag, lo=mag, prec=f._prec, nonneg=True)


def _float_text(node: ast.Constant, source: str) -> str:
    return (ast.get_source_segment(source, node) or repr(node.value)).replace("_", "")


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


def _int_literal(node: ast.AST) -> int | None:
    """The value of ``n``, ``-n`` or ``+n`` for an integer literal ``n``, else None."""
    sign = 1
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
        sign = -1 if isinstance(node.op, ast.USub) else 1
        node = node.operand
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return sign * node.value
    return None


def _nonneg_literal(node: ast.AST) -> bool:
    """A literal exponent that is ≥ 0: ``2``, ``0.5``, ``1/2``, ``Rational(3, 4)``."""
    if isinstance(node, ast.Constant):
        return type(node.value) in (int, float) and node.value >= 0
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return _nonneg_literal(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult | ast.Div):
        return _nonneg_literal(node.left) and _nonneg_literal(node.right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == _RATIONAL:
        return all(_int_literal(a) is not None and _int_literal(a) >= 0 for a in node.args)  # type: ignore[operator]
    return False


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


def _log10_sum(his: list[float]) -> float:
    """log10 of the sum of 10**h (an upper bound on a sum of terms bounded by ``his``)."""
    top = max(his)
    if not math.isfinite(top):
        return top
    return top + math.log10(sum(10.0 ** (h - top) for h in his))


def _sum_floor(terms: list[_Bound], signs: list[int]) -> float:
    """A lower bound on log10|s| for every non-zero sum s of a subset of ``terms``.

    Sympy groups an Add's numbers (and the coefficients of like terms), so any
    subset of the terms can be summed, including the parts of a child Add or
    of a number times an Add, which flatten into this one (a child's ``hi``
    bounds each part and its floor every sum of parts). ``signs`` is +1 for a
    term known to be ≥ 0, -1 for one known to be ≤ 0, 0 if unknown.

    * Terms of one sign cannot cancel: a non-zero sum is at least its largest
      term, so at least the smallest floor (``phi**2 + 0.1``).
    * A dominant term, whose floor exceeds the sum of every other term's
      bound, cannot be cancelled by them (``phi - 0.5``): any subset holding
      it is at least the difference; peel it and bound the rest the same way.
    * Otherwise the terms can cancel; the caller's generic bound applies
      (returned as -inf here).
    """
    floors = [_floor(t) for t in terms]
    his = [_hi(t.hi) for t in terms]
    live = list(range(len(terms)))
    lo = math.inf
    while live:
        if len(live) == 1 or all(signs[i] == 1 for i in live) or all(signs[i] == -1 for i in live):
            return min(lo, *(floors[i] for i in live))
        top = max(live, key=lambda i: floors[i])
        rest = [i for i in live if i != top]
        others = _log10_sum([his[i] for i in rest])
        if not (math.isfinite(floors[top]) and floors[top] - others > _DOMINANCE):
            return -math.inf
        lo = min(lo, floors[top] + math.log10(1.0 - 10.0 ** (others - floors[top])) - _FLOAT_SLACK)
        live = rest
    return lo


def _sum(terms: list[_Bound], *, subtracts: bool, signs: list[int] | None = None) -> _Bound:
    """One flattened Add of ``terms`` (sympy sums its numbers in one Add)."""
    n = len(terms)
    digits = sum(t.digits for t in terms) + (n - 1)
    hi = _hi(max(t.hi for t in terms) + math.log10(n))
    prec = max(t.prec for t in terms)
    if prec:
        # Float addition: each term (an exact number converted to a Float, or
        # a Float) is a multiple of its ulp, ulp(x) ≥ |x|·2**-prec, so every
        # partial sum is a multiple of the smallest one and a non-zero sum is
        # at least that ulp. ``1.0000001 - 1.0`` is ~1e-7, not ~1e-1.
        lo = min(-digits, *(_floor(t) for t in terms)) - prec * _LOG10_2 - 1.0
        hi += _FLOAT_SLACK
    else:
        lo = -digits  # a non-zero sum of Rationals with these digits
    # Where the terms provably cannot cancel, a tighter bound (W1 R4-API: the
    # generic one refused ``exp(-1/(phi**2 + 0.1))`` as exp of 10**19).
    lo = max(lo, _sum_floor(terms, signs if signs is not None else [0] * n))
    return _Bound(
        digits, hi, lo, any(t.has_log for t in terms), prec, any(t.cplx for t in terms),
        not subtracts and all(t.nonneg for t in terms),
    )


def _product(a: _Bound, op: ast.operator, b: _Bound) -> _Bound:
    prec = max(a.prec, b.prec)
    slack = _FLOAT_SLACK if prec else 0.0
    if isinstance(op, ast.Mult):
        hi, lo = a.hi + b.hi, _floor(a) + _floor(b)
    else:  # Div
        hi, lo = a.hi - _floor(b), _floor(a) - b.hi
    return _Bound(
        a.digits + b.digits, _hi(hi + slack), _lo(lo - slack), a.has_log or b.has_log, prec,
        a.cplx or b.cplx, a.nonneg and b.nonneg,
    )


def _power(a: _Bound, b: _Bound, exponent: ast.AST) -> _Bound:
    # Every exponent is bounded, whether or not it looks constant.
    if not _hi(b.hi) <= _LOG10_MAX_EXPONENT + 1e-12:
        raise _reject(f"exponents must satisfy |x| <= {MAX_CUSTOM_EXPONENT}")
    e_max = 10.0 ** b.hi
    fa = _floor(a)
    if _nonneg_literal(exponent):
        hi, lo = e_max * max(a.hi, 0.0), e_max * min(fa, 0.0)
    else:
        size = e_max * max(abs(a.hi), abs(fa))
        hi, lo = size, -size
    if b.cplx and (a.cplx or not a.nonneg):
        # |a**b| = |a|**Re(b) * e**(-arg(a)*Im(b)), and |arg(a)| <= pi for a
        # negative or complex base: (-1)**(-64*sqrt(-1)) is e**(64*pi), ~1.9e87
        # (W1 R4-API, the round-3B API3 verifier's bypass).
        widen = math.pi * e_max * _LOG10_E
        hi, lo = hi + widen, lo - widen
    prec = max(a.prec, b.prec)
    slack = _FLOAT_SLACK if prec else 0.0
    n = _int_literal(exponent)
    real_base = not a.cplx
    return _Bound(
        a.digits * e_max + b.digits, _hi(hi + slack), _lo(lo - slack), a.has_log or b.has_log, prec,
        cplx=a.cplx or b.cplx or (not a.nonneg and n is None),
        nonneg=real_base and not b.cplx and (a.nonneg or (n is not None and n % 2 == 0)),
    )


class _Checker:
    """Walk the parsed, unevaluated tree: allow-list every node and bound it (SEC-L3).

    Nothing is evaluated here; :func:`_build` evaluates the same tree only
    after every node passed.
    """

    def __init__(self, symbols: dict[str, sp.Symbol], source: str) -> None:
        self.symbols = symbols
        self.source = source

    def visit(self, node: ast.AST) -> _Bound:
        return _within(self._visit(node))

    def _visit(self, node: ast.AST) -> _Bound:
        if isinstance(node, ast.Constant):
            return _literal_bound(node.value, _float_text(node, self.source))
        if isinstance(node, ast.Name):
            if node.id in _SAFE_FUNCTIONS or node.id == _RATIONAL:
                raise _reject(f"'{node.id}' must be called")
            if node.id in _SAFE_CONSTANTS and node.id not in self.symbols:
                return _Bound(digits=1, hi=0.5, lo=0.49, nonneg=True)
            return _Bound(digits=0, hi=0.0, lo=0.0)
        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, ast.USub | ast.UAdd):
                raise _reject(f"operator {type(node.op).__name__} not allowed")
            operand = self.visit(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else replace(operand, nonneg=False)
        if isinstance(node, ast.BinOp):
            return self._binop(node)
        if isinstance(node, ast.Call):
            return self._call(node)
        if isinstance(node, ast.Attribute):
            raise _reject("imports / attributes not allowed")
        if isinstance(node, ast.Lambda):
            raise _not_canonical("a lambda is not accepted; write its expression in phi")
        raise _reject(f"{type(node).__name__} not allowed")

    def _binop(self, node: ast.BinOp) -> _Bound:
        for sub in (node, node.left, node.right):
            if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitXor):
                raise _reject("'^' is not allowed; write powers with '**'")
            if isinstance(sub, ast.BinOp) and type(sub.op) not in _FAMILY:
                raise _reject(f"operator {type(sub.op).__name__} not allowed")
        first, rest = _chain(node)
        family = _FAMILY[type(node.op)]
        if family == "add":
            terms = [self.visit(first)] + [self.visit(rhs) for _, rhs in rest]
            # +1: known ≥ 0, -1: known ≤ 0 (a subtracted term ≥ 0), 0: unknown.
            signs = [1 if terms[0].nonneg else 0] + [
                (-1 if isinstance(op, ast.Sub) else 1) if t.nonneg else 0
                for (op, _), t in zip(rest, terms[1:], strict=True)
            ]
            subtracts = any(isinstance(op, ast.Sub) for op, _ in rest)
            return _within(_sum(terms, subtracts=subtracts, signs=signs))
        if family == "pow":
            return _within(_power(self.visit(node.left), self.visit(node.right), node.right))
        acc = self.visit(first)
        for op, rhs in rest:
            acc = _within(_product(acc, op, self.visit(rhs)))
        return acc

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
                return _Bound(digits=1 + _int_digits(q), hi=0.0, lo=0.0, nonneg=True)
            mag = math.log10(abs(p)) - math.log10(abs(q))
            return _Bound(_int_digits(p) + _int_digits(q), mag, mag, nonneg=p * q > 0)
        if len(node.args) != 1 or isinstance(node.args[0], ast.Starred):
            raise _reject(f"{func.id}() takes exactly one argument")
        c = self.visit(node.args[0])
        fc = _floor(c)
        size = max(abs(c.hi), abs(fc))
        slack = _FLOAT_SLACK if c.prec else 0.0
        real_arg = not c.cplx
        if func.id == "sqrt":
            return _Bound(2 * c.digits + 1, _hi(c.hi / 2 + slack), _lo(fc / 2 - slack), c.has_log,
                          c.prec, cplx=c.cplx or not c.nonneg, nonneg=real_arg and c.nonneg)
        if func.id == "log":
            mag = _LN_10 * size + 1.0
            if c.prec and (c.cplx or not c.nonneg):
                mag += math.pi  # log(-x) = log(x) + i·pi, evaluated for a Float
            lo = -math.inf
            if c.prec and real_arg:
                # |log x| for a real p-bit Float x != 1: at least 2**-(p+1) near
                # 1 (its neighbours are 1 -/+ 2**-p), pi for x < 0; an exact
                # value (Floats cancelled) has at most ``digits`` (W1 R4-API).
                lo = min(-(c.prec + 1) * _LOG10_2, -(c.digits + 2.0)) - slack - _FLOAT_SLACK
            return _Bound(c.digits + 1, _hi(math.log10(mag) + slack), lo, True, c.prec,
                          cplx=c.cplx or not c.nonneg)
        # Of a log, sympy rewrites these algebraically (tanh(log(x)) is
        # (x**2 - 1)/(x**2 + 1), exp(k*log(x)) is x**k): bound them as such.
        digits = 2 * c.digits + 2 if c.has_log else c.digits + 1
        if func.id in ("sin", "cos", "tanh") and real_arg:
            # A finite floor for a non-zero value (W1 R4-API: -inf refused
            # ``1/sin(0.5*phi)`` and ``log(tanh(0.5*phi))`` as beyond float64).
            if func.id == "tanh":
                lo = min(fc, 0.0) + _LOG10_TANH_1  # |tanh x| >= tanh(1)*min(|x|, 1)
            elif c.prec:
                # Zeros at multiples of pi/2: a p-bit Float is at least
                # 2**-(2p+16) from one; a small x keeps |sin x| >= (2/pi)|x|;
                # an exact value (Floats cancelled) has at most ``digits``.
                scale, extra = _TRIG_ZERO_BITS
                lo = min(-(scale * c.prec + extra) * _LOG10_2, -(digits + 1.0))
                if func.id == "sin":
                    lo = min(lo, fc + _LOG10_2_OVER_PI)
            else:
                lo = -math.inf  # exact: _floor bounds it by its digits
            return _Bound(digits, 0.0, _lo(lo - slack), c.has_log, c.prec)
        # exp, sinh, cosh, or sin/cos/tanh of a complex argument (sin(i·y) is
        # i·sinh(y)): they grow like exp of the argument's size.
        if c.has_log and not _hi(c.hi) <= _LOG10_MAX_EXPONENT + 1e-12:
            raise _reject(f"{func.id}() of a log: the factor must satisfy |x| <= {MAX_CUSTOM_EXPONENT}")
        if not _hi(c.hi) <= _LOG10_MAX_EXP_ARGUMENT:
            kind = "" if func.id in ("exp", "sinh", "cosh") else "a complex "
            raise _reject(
                f"{func.id}() of {kind}argument up to 10**{c.hi:.3g}: it must satisfy "
                f"|x| <= {MAX_CUSTOM_EXP_ARGUMENT:.6g} (float64 overflows beyond it)",
            )
        mag = _LOG10_E * 10.0 ** c.hi
        grow = MAX_CUSTOM_EXPONENT if c.has_log else 1
        hi = mag
        if func.id == "tanh":
            # tanh of a complex argument can sit next to a pole (tanh(i*y) is
            # i*tan(y), y near pi/2): a Float is at least ~2**-prec from one,
            # an exact number with d digits at least ~10**-(8*(d + log10|y|))
            # (pi's irrationality exponent). W1 R4-API: the exact case had no
            # pole term, so tanh(sqrt(-1)*Rational(...)) ~ 1e16*I passed as ~4.8.
            pole = _PI_IRRATIONALITY * (c.digits + max(_hi(c.hi), 0.0) + 1.0)
            hi = mag + (c.prec * _LOG10_2 if c.prec else 0.0) + pole + 6.0
        if func.id == "exp":
            lo = -mag  # |exp(z)| = exp(Re z) ≥ exp(-|z|): never zero
        elif func.id == "cosh" and real_arg:
            lo = 0.0  # cosh(x) ≥ 1
        elif func.id == "sinh" and real_arg:
            lo = fc - slack  # |sinh x| ≥ |x| (W1 R4-API: was -inf)
        else:
            lo = -math.inf  # sinh(0) = 0, sin(i·y) and friends can vanish
        nonneg = real_arg and func.id in ("exp", "cosh")
        return _Bound(digits * grow, _hi(hi + slack), lo, c.has_log, c.prec, c.cplx, nonneg)


def _build(node: ast.AST, source: str, symbols: dict[str, sp.Symbol]) -> sp.Expr:
    """Evaluate a checked tree with sympy, node by node as ``sympify`` would."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int):
            return sp.Integer(node.value)
        return sp.Float(_float_text(node, source))
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


def _syntax_detail(exc: BaseException) -> str:
    if isinstance(exc, SyntaxError):
        return f"{exc.msg}, line {exc.lineno}"
    return type(exc).__name__


_PARSE_ERRORS = (SyntaxError, ValueError, MemoryError, RecursionError)


def _function_return(text: str) -> ast.expr:
    """D17: the expression of ``def V(<name>): return <expr>``, with ``<name>`` renamed to phi.

    Exactly one top-level ``def V`` with exactly one positional parameter (no
    default, annotation, decorator, ``*args``/``**kwargs`` or keyword-only
    parameter), whose body is exactly one ``return <expression>``, optionally
    preceded by a docstring. Anything else is refused with the canonical form.
    """
    try:
        module = ast.parse(text, mode="exec")
    except _PARSE_ERRORS as exc:
        raise _not_canonical(f"it does not parse ({_syntax_detail(exc)})") from exc
    if len(module.body) != 1 or not isinstance(module.body[0], ast.FunctionDef):
        found = ", ".join(type(s).__name__ for s in module.body) or "nothing"
        raise _not_canonical(f"a snippet is one expression or one 'def V(<name>)', not {found}")
    fn = module.body[0]
    if fn.name != "V":
        raise _not_canonical(f"the function must be named V, not {fn.name!r}")
    if fn.decorator_list:
        raise _not_canonical("V takes no decorators")
    if getattr(fn, "type_params", None):
        raise _not_canonical("V takes no type parameters")
    args = fn.args
    positional = [*args.posonlyargs, *args.args]
    if args.vararg or args.kwarg or args.kwonlyargs:
        raise _not_canonical("V takes exactly one positional parameter (no *args, **kwargs or "
                             "keyword-only parameters)")
    if len(positional) != 1:
        raise _not_canonical(f"V takes exactly one positional parameter, not {len(positional)}")
    if args.defaults or args.kw_defaults:
        raise _not_canonical("V's parameter takes no default value")
    if positional[0].annotation is not None or fn.returns is not None:
        raise _not_canonical("V takes no annotations")
    body = list(fn.body)
    if (len(body) > 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]  # a docstring first is allowed
    if len(body) != 1 or not isinstance(body[0], ast.Return) or body[0].value is None:
        kinds = ", ".join(type(s).__name__ for s in body)
        if not any(isinstance(s, ast.Return) for s in ast.walk(fn)):
            raise _not_canonical(f"V has no 'return <expression>' (its body is {kinds})")
        raise _not_canonical(
            f"V's body must be exactly one 'return <expression>' (a docstring may precede it), "
            f"not {kinds}",
        )
    expr = body[0].value
    name = positional[0].arg
    if name != "phi":
        if any(isinstance(n, ast.Name) and n.id == "phi" for n in ast.walk(expr)):
            raise _not_canonical(
                f"V's body uses the name 'phi' besides its parameter {name!r}, which is renamed "
                "to phi; rename one of them",
            )
        for n in ast.walk(expr):
            if isinstance(n, ast.Name) and n.id == name:
                n.id = "phi"
    return expr


def _custom_expr(source: str, symbols: dict[str, sp.Symbol] | None = None) -> sp.Expr:
    """Parse a user-supplied custom potential into a sympy Expr.

    The canonical form is one Python expression in ``phi`` (no statements,
    no imports); ``def V(<name>): return <expr>`` is also accepted
    (:func:`_function_return`, D17). Sympy never parses or evaluates the
    raw string (SEC-L3): Python's ``ast`` parses it once (``^`` stays XOR
    and is refused), the unevaluated tree is allow-listed and bounded node
    by node (literals, every exponent, the digits any exact subexpression
    can reach, Float magnitudes and cancellation, float64's range, the
    ``exp``/``log`` rewrite, node count and depth), and only then is that
    same tree evaluated with sympy's operators.
    """
    if len(source) > MAX_CUSTOM_SOURCE_CHARS:
        raise _reject(f"source longer than {MAX_CUSTOM_SOURCE_CHARS} characters")
    text = source.strip()
    try:
        expr = ast.parse(text, mode="eval").body
    except _PARSE_ERRORS:
        # Not an expression: a ``def V(<name>)`` snippet, or a refusal that
        # names the canonical form.
        expr = _function_return(text)
    # Parse into the *same* symbols compile_potential differentiates and
    # lambdifies with (``real=True``). Distinct assumption-free Symbols
    # would make V′ ≡ V″ ≡ 0 and leave parameters unbound (P1-02 found this).
    names = dict(symbols or {})
    tree = ast.Expression(body=expr)
    _check_shape(tree)
    _Checker(names, text).visit(expr)
    return _build(expr, text, names)


def compile_potential(pot: Potential) -> ScalarModel:
    """Compile ``pot`` in M2's units (W1-PARAMS: API units are converted
    once, by :meth:`Potential.engine`; a converted potential is not touched)."""
    pot = pot.engine()
    phi = sp.symbols("phi", real=True)
    # One Symbol per name: sympy.symbols would parse a name ('a:9999999' is a
    # range of ten million Symbols, 'a b' two); Potential only admits
    # identifiers, for which the two are the same (W1 R4-API).
    params = tuple(sp.Symbol(name, real=True) for name in sorted(pot.params) or ("_unused",))
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
        if "phi" in pot.params:
            # phi is the field; as a parameter it would be a second lambdify
            # argument named phi (a SyntaxError, which used to be a 500).
            raise ValueError("custom potential: 'phi' is the field, not a parameter; remove it from params")
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
    if pot.kind == "custom" and any(e.has(sp.zoo, sp.oo, -sp.oo, sp.nan) for e in (expr, Vp, Vpp)):
        # ``log(0)``, ``1/0``…: lambdify cannot print them (a KeyError, which
        # used to be a 500), and V would not be a finite number anyway.
        raise ValueError("custom potential: V or its derivatives are not finite (zoo, oo or nan)")

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
