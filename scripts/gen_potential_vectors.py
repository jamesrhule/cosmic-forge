#!/usr/bin/env python3
"""Backend-generated test vectors for the Configurator's two potential helpers.

Gate 1 round 4 (R4-FEOPS). The browser has a V(psi) preview
(``src/lib/potentialEvaluator.ts``) and a custom-snippet linter
(``src/lib/potentialValidator.ts``); both mirror backend behaviour, so both
are tested against what the backend itself computes:

- ``src/lib/__tests__/fixtures/potential-preview.m2.json``: V(psi) as M2
  computes it (``compile_potential`` on ``Potential.engine()``, the run's own
  GeV -> M_Pl conversion) on the preview's psi grid, for the Configurator's
  default parameters and every other built-in parameter set the bundled
  configs carry.
- ``src/lib/__tests__/fixtures/potential-snippets.backend.json``: custom
  snippets (the shape cases below) with the backend parser's verdict, accept
  or refuse (``m2_scalar.potentials._custom_expr``, the parser behind every
  custom potential).

``backend/tests/test_potential_vectors.py`` recomputes both and fails when a
committed file no longer matches the backend; the vitests
``potentialEvaluator.test.ts`` and ``potentialValidator.test.ts`` check the
browser against the files. A backend change therefore fails a backend test
until this script is re-run, and the re-run fails the vitest until the
browser follows, so the two sides cannot drift.

Usage: ``uv run python scripts/gen_potential_vectors.py [--check]``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import sympy as sp
from ucgle_f1.domain import Potential
from ucgle_f1.m2_scalar import compile_potential
from ucgle_f1.m2_scalar.potentials import _custom_expr
from ucgle_f1.m2_scalar.trajectory import potential_args

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "lib" / "__tests__" / "fixtures"
PREVIEW = OUT / "potential-preview.m2.json"
SNIPPETS = OUT / "potential-snippets.backend.json"
DEFAULTS = ROOT / "src" / "lib" / "configDefaults.json"
FIXTURES = ROOT / "public" / "fixtures"

# The preview's psi grid (potentialEvaluator.ts samplePotential: 80 points
# on [-2, 4] M_Pl). The vitest checks the browser builds the same grid.
PREVIEW_POINTS = 80

# Shape cases for the linter. Each is a snippet the Configurator's editor can
# hold; the backend decides the verdict. A case belongs here when its verdict
# follows from the snippet's shape (statements, operators, names, calls,
# lines), which the linter can see without evaluating anything; the size and
# magnitude bounds stay backend-only.
SNIPPET_CASES: list[str] = [
    # The canonical form (D17): one expression in phi.
    "0.5 * m**2 * phi**2",
    "Lambda**4 * (1 - cos(phi / f_a))",
    "exp(-phi) + Rational(1, 2) * sqrt(phi**2)",
    "pi * phi**2 - tanh(phi) + sinh(phi) * cosh(phi) + log(1 + phi**2)",
    "# comments are ignored, even with ^ ; = in them\n0.5 * phi**2  # trailing ^ = ;\n",
    "(0.5 * phi**2\n + 1e-3 * phi**4)",
    "0.5 * phi**2 + \\\n    1e-3 * phi**4",
    "1e-10",
    # The accepted legacy shape: def V(<name>) with one return.
    "def V(psi): return 0.5 * psi**2",
    "def V(x):\n    return 1e-10 * (1 - cos(x / 8.7))",
    'def V(psi):\n    """Starobinsky."""\n'
    "    return 0.75 * (1.3e-5)**2 * (1 - exp(-0.8164965809 * psi))**2",
    "def V(psi):\n    return (0.5 * psi**2\n            + 1e-3 * psi**4)",
    # Refused: statements, assignments, a second line.
    "import os\nphi",
    "m = 2\nm * phi",
    "phi; phi",
    "1e-10 * phi\n2 * phi",
    "0.5 *\nphi**2",
    "(m := 2) * phi",
    # Refused: operators and constructs outside the allow-list.
    "phi ^ 2",
    "phi % 2",
    "phi // 2",
    "phi << 2",
    "phi & 1",
    "~phi",
    "lambda phi: phi**2",
    "phi**2 if phi > 0 else 0",
    "phi > 0",
    "phi == 1",
    "phi and 1",
    "not phi",
    "[phi, phi]",
    "phi[0]",
    "{phi: 1}",
    "'phi'",
    # Refused: names and calls outside the allow-list.
    "open(phi)",
    "math.exp(phi)",
    "phi.real",
    "exp",
    "exp(x=phi)",
    "__import__('os')",
    # Refused: any other function shape (D17).
    "def V(psi):\n    M = 1.3e-5\n"
    "    return 0.75 * M**2 * (1.0 - 2.718281828 ** (-0.8164965809 * psi)) ** 2",
    'def V(psi):\n    """doc"""\n    M = 1\n    return M * psi',
    "def V(a, b): return a * b",
    "def W(psi): return psi**2",
    "def V(psi):\n    return psi\nphi",
    "def V(psi):\n    return psi**2\n    psi = 1",
    "",
]


# Beyond the bundled configs: a hilltop whose power is not the default and
# whose width is of order M_Pl, so p and mu's conversion are both exercised.
EXTRA_PREVIEW_CASES: list[dict[str, Any]] = [
    {"kind": "hilltop", "params": {"V0": 2e-9, "mu": 5e18, "p": 2}},
]


def _preview_cases() -> list[dict[str, Any]]:
    """The Configurator's defaults, then every other built-in parameter set
    the bundled configs carry (benchmarks.json, runs/*.json), then
    ``EXTRA_PREVIEW_CASES``, without repeats."""
    defaults = json.loads(DEFAULTS.read_text(encoding="utf-8"))["potentialParams"]
    potentials = [{"kind": k, "params": p} for k, p in defaults.items() if k != "custom"]
    bench = json.loads((FIXTURES / "benchmarks.json").read_text(encoding="utf-8"))
    potentials += [b["config"]["potential"] for b in bench["benchmarks"]]
    for path in sorted((FIXTURES / "runs").glob("*.json")):
        potentials.append(json.loads(path.read_text(encoding="utf-8"))["config"]["potential"])
    potentials += EXTRA_PREVIEW_CASES
    cases: list[dict[str, Any]] = []
    for pot in potentials:
        case = {"kind": pot["kind"], "params": dict(pot["params"])}
        if case["kind"] != "custom" and case not in cases:
            cases.append(case)
    return cases


def psi_grid() -> list[float]:
    return [-2 + (i / (PREVIEW_POINTS - 1)) * 6 for i in range(PREVIEW_POINTS)]


def m2_values(kind: str, params: dict[str, float], psi: list[float]) -> list[float]:
    pot = Potential(kind=kind, params=params)  # type: ignore[arg-type]
    model = compile_potential(pot)
    args = potential_args(model, pot.engine().params)
    return [float(model.V(x, *args)) for x in psi]


def preview_vectors() -> dict[str, Any]:
    psi = psi_grid()
    return {
        "generatedBy": "scripts/gen_potential_vectors.py",
        "what": "V(psi) [M_Pl^4] as M2 computes it: compile_potential(Potential(kind, params))",
        "psi": psi,
        "cases": [
            {**case, "V": m2_values(case["kind"], case["params"], psi)}
            for case in _preview_cases()
        ],
    }


def backend_verdict(snippet: str) -> dict[str, str]:
    try:
        _custom_expr(snippet, {"phi": sp.Symbol("phi", real=True)})
    except ValueError as exc:
        return {"verdict": "refuse", "reason": str(exc)}
    return {"verdict": "accept", "reason": ""}


def snippet_vectors() -> dict[str, Any]:
    return {
        "generatedBy": "scripts/gen_potential_vectors.py",
        "what": "custom snippets with the backend parser's verdict (m2_scalar.potentials)",
        "cases": [
            {"snippet": s, **{f"backend_{k}": v for k, v in backend_verdict(s).items()}}
            for s in SNIPPET_CASES
        ],
    }


def render(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if a file is stale")
    args = parser.parse_args()
    stale = []
    for path, data in ((PREVIEW, preview_vectors()), (SNIPPETS, snippet_vectors())):
        text = render(data)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    if stale:
        print(f"stale: {', '.join(stale)}; run scripts/gen_potential_vectors.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
