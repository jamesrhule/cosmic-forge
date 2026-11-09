"""W1 round 4, lane R4-API: the custom-potential caps (items 1 and 2).

Item IDs match ``docs/build/lanes/W1-r4-api.md`` and
``docs/build/evidence/W1-r4-api.md``.

* R4-1 (round-3B API3 verifier, MEDIUM regression): the caps of ``0c4848f``
  refused ordinary potentials that ``15e4e3c`` accepted, with a misleading
  float64-overflow message. A Float sin/cos/tanh/log/sinh subtree had a lower
  bound of -inf (so dividing by it looked unbounded), and a Float sum's
  cancellation bound fed ``exp``'s argument cap. Realistic potentials must be
  accepted and compile to the values their formula gives.
* R4-2 (same verifier, MEDIUM bypass): a complex power of a non-positive base
  ignored ``e**(-arg(a)*Im b)``, and ``tanh`` of an exact imaginary argument
  had no pole bound; sympy then hung building the expression.
"""

from __future__ import annotations

import math
import subprocess
import sys

import pytest
import sympy as sp

from ucgle_f1.domain import Potential
from ucgle_f1.m2_scalar import compile_potential
from ucgle_f1.m2_scalar.potentials import _custom_expr

_PARAMS = {
    "m": 1.0e-6, "lam": 1.0e-12, "M": 1.3e-5, "L": 0.0071, "f": 8.7, "V0": 1.0e-10,
    "mu": 2.0, "alpha": 1.5, "A": 2.0e-10, "B": 3.0e-11, "phi0": 5.5,
}
_PHIS = (0.6, 1.3, 2.7)

# The formula of each potential, evaluated independently of sympy and of the
# checker: Python's math functions on the same source (test constants only).
_MATH = {"sqrt": math.sqrt, "log": math.log, "exp": math.exp, "sin": math.sin, "cos": math.cos,
         "tanh": math.tanh, "cosh": math.cosh, "sinh": math.sinh, "pi": math.pi,
         "Rational": lambda p, q=1: p / q}

# Realistic custom potentials (the kinds the item names), all accepted.
_CORPUS = [
    # polynomials
    "m**2*phi**2/2", "lam*phi**4/4", "m**2*phi**2/2 + lam*phi**4/4",
    "0.5*m**2*phi**2 - 0.25*lam*phi**4 + 1e-10", "V0*(1 - phi**2/mu**2)**2",
    "1e-10*phi**4 + 1.3e-5",
    # Starobinsky
    "0.75*M**2*(1 - exp(-sqrt(2/3)*phi))**2", "(1-exp(-sqrt(2/3)*phi))**2",
    "Rational(3, 4)*M**2*(1 - exp(-sqrt(Rational(2, 3))*phi))**2",
    "0.75 * (1.3e-5)**2 * (1.0 - 2.718281828 ** (-0.8164965809 * phi)) ** 2",
    # natural
    "L**4*(1 - cos(phi/f))", "1 - cos(phi/f)", "L**4*(1 + cos(phi/f))", "L**4*(1.0 - cos(phi/8.7))",
    # hilltop
    "V0*(1 - (phi/mu)**4)", "V0*(1 - (phi/mu)**2)", "V0*(1.0 - (phi/3.5)**6)",
    # log
    "V0*log(phi)", "lam*phi**4*(log(phi/mu) - 0.25)", "V0*(1 + 0.01*log(phi/mu))",
    "V0*log(1 + phi**2)", "V0*log(1.0 + phi**2/0.3)",
    # tanh
    "V0*tanh(phi/sqrt(6*alpha))**2", "V0*tanh(phi/2.449)**2", "V0*(1 - tanh(phi)**2)",
    "V0*tanh(phi**2/mu**2)",
    # sqrt
    "V0*(sqrt(1 + phi**2) - 1)", "m**2*(sqrt(phi**2 + mu**2) - mu)", "V0*sqrt(1.0 + (phi/mu)**2)",
    "V0*sqrt(phi)",
    # rational functions with positive denominators
    "V0*phi**2/(1 + phi**2)", "V0*phi**4/(mu**4 + phi**4)", "V0/(1.0 + phi**2)",
    "V0*phi**2/(1.0 + 0.5*phi**2)**2", "V0*(phi**2 + 0.1)/(phi**2 + 2.5)",
    # sums of exponentials
    "V0*(exp(-phi) + exp(-2*phi))", "V0*(1 - 2*exp(-phi) + exp(-2*phi))",
    "A*exp(-0.5*phi) + B*exp(-1.5*phi)", "V0*(exp(phi/mu) + exp(-phi/mu))",
    "V0*(1 - exp(-0.8164965809*phi))**2 + 1e-3*V0*exp(-3.0*phi)",
]

# The round-3B API3 verifier's examples: accepted and compiled on 15e4e3c,
# refused on 0c4848f ("a subexpression may exceed 1.798e+308" or "exp() of
# argument up to 10**19").
_VERIFIER_REFUSED = [
    "1/sin(0.5*phi)", "V0/sin(phi/2.0)", "1/cos(0.5*phi)",
    "1/tanh(phi/0.1)", "1/sinh(0.5*phi)", "V0*(1 - 1/tanh(phi/0.7))", "tanh(0.5*phi)**-2",
    "1/log(2.0*phi)", "V0/log(phi/0.5)", "log(log(2.0*phi))",
    "log(sin(0.5*phi))", "log(cos(phi/2.0))", "log(tanh(0.5*phi))",
    "1/sqrt(sin(0.5*phi))", "log(1.0 + log(1.0 + phi))", "cos(0.5*phi)/sin(0.5*phi)",
    "V0*(1 + 0.1/sin(phi/0.3))",
    "V0*exp(-1/(phi**2 + 0.1))", "V0*(1 - exp(-1/(1.0 + phi**2)))", "V0*exp(-1/(phi - 0.5))",
    "V0*cosh(1/(1.0 + phi**2))", "V0*exp(-1/(phi**2 + 1/10))",
]


def _reference(source: str, phi: float) -> float:
    return float(eval(source, {"__builtins__": {}}, {**_MATH, **_PARAMS, "phi": phi}))


@pytest.mark.parametrize("source", _CORPUS + _VERIFIER_REFUSED)
def test_r4_1_ordinary_potentials_are_accepted_and_compile_to_their_formula(source: str) -> None:
    pot = Potential(kind="custom", params=_PARAMS, customPython=source)
    model = compile_potential(pot)
    phi = sp.Symbol("phi", real=True)
    assert phi in model.symbolic_V.free_symbols
    args = [_PARAMS[n] for n in model.param_names]
    for x in _PHIS:
        got = float(model.V(x, *args))
        want = _reference(source, x)
        assert math.isclose(got, want, rel_tol=1e-12, abs_tol=1e-300), (source, x, got, want)
        # V' agrees with a central difference of the formula.
        h = 1e-6 * max(1.0, abs(x))
        fd = (_reference(source, x + h) - _reference(source, x - h)) / (2 * h)
        tol = 1e-6 * abs(want) + 1e-300
        assert math.isclose(float(model.Vp(x, *args)), fd, rel_tol=1e-5, abs_tol=tol), (source, x)


def _refused_in_a_child(source: str, limit: float = 20.0) -> str:
    code = (
        "import sys\n"
        "from ucgle_f1.m2_scalar.potentials import _custom_expr\n"
        "try:\n"
        "    _custom_expr(sys.argv[1])\n"
        "except ValueError as exc:\n"
        "    print('rejected:', exc)\n"
        "else:\n"
        "    print('accepted')\n"
    )
    try:
        return subprocess.run(
            [sys.executable, "-c", code, source],
            capture_output=True, text=True, timeout=limit, check=True,
        ).stdout
    except subprocess.TimeoutExpired:
        pytest.fail(f"parsing {source!r} did not finish within {limit:g} s: "
                    "sympy built an unbounded number")


# The verifier's bypasses: (-1)**(-64*sqrt(-1)) is e**(64*pi) ~ 1.9e87, bounded
# as ~1; tanh(i*y) with y a rational next to pi/2 is i*tan(y) ~ 1e16*i,
# bounded as ~4.8. On 0c4848f the first four hang in _custom_expr and the last
# passes the caps and hangs in compile_potential.
_BYPASSES = [
    "log(sin(exp((-1)**(-64*sqrt(-1)))))",
    "sin(sin(exp((-1)**(-64*sqrt(-1)))))",
    "phi**2 + log(sin(exp((-1)**(-64*sqrt(-1)))))",
    "log(sin(sin(tanh(sqrt(-1)*Rational(5920787228742393, 3769290217798865)))))",
    "phi*sin(exp((-1)**(-64*sqrt(-1))))",
    # Variants of the same two holes.
    "sin(exp((-1.0)**(-64*sqrt(-1))))", "sin(exp((-2)**(64*sqrt(-1.0))))",
    "sin(exp(log(-1)**(-64*sqrt(-1))))", "sin(exp((sqrt(-1)*3)**(-60*sqrt(-1))))",
    "sin(sin(tanh(sqrt(-1)*Rational(355, 226))))",
    "sin(sin(tanh(sqrt(-1)*(pi/2 + Rational(1, 10**30)))))",
]


@pytest.mark.parametrize("source", _BYPASSES)
def test_r4_2_complex_power_and_tanh_pole_bypasses_are_refused_quickly(source: str) -> None:
    out = _refused_in_a_child(source)
    assert out.startswith("rejected: custom potential:"), f"{source!r}: {out}"


def test_r4_2_the_complex_power_bound_holds_its_value() -> None:
    """The widened bound covers the true magnitude: e**(64*pi) is 10**87.3."""
    exact = sp.Integer(-1) ** (-64 * sp.sqrt(-1))
    assert abs(float(sp.log(abs(exact), 10)) - 64 * math.pi * math.log10(math.e)) < 1e-9
    # Its square root is still accepted (a real potential may use a complex
    # exponent of a symbol) and stays symbolic.
    assert _custom_expr("phi**sqrt(phi)", {"phi": sp.Symbol("phi", real=True)}).free_symbols


def test_r4_2_exp_of_the_complex_power_is_refused_with_its_true_size() -> None:
    with pytest.raises(ValueError, match=r"exp\(\) of argument up to 10\*\*87"):
        _custom_expr("exp((-1)**(-64*sqrt(-1)))")
