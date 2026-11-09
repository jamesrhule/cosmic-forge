"""Gate 1 round 4 (R4-FEOPS): the browser's potential helpers are tested
against vectors the backend generates, and this test keeps those vectors
equal to what the backend computes now.

- ``src/lib/configDefaults.json`` ``units.M_PL_GEV`` is the M_Pl the
  Configurator's V(psi) preview converts GeV with; it must be the engine's
  ``M_PL_GEV`` (m1_background), the one ``Potential.engine()`` uses.
- ``src/lib/__tests__/fixtures/potential-preview.m2.json``: V(psi) from M2
  for the Configurator's defaults and every bundled built-in parameter set
  (``potentialEvaluator.test.ts`` checks the preview against it).
- ``src/lib/__tests__/fixtures/potential-snippets.backend.json``: the backend
  parser's verdict on each shape case (``potentialValidator.test.ts`` checks
  the linter against it).

Both files are written by ``scripts/gen_potential_vectors.py``; a failure
here means the backend changed and the script must be re-run (and then the
vitests say whether the browser still agrees).
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from types import ModuleType
from typing import Any

from ucgle_f1.m1_background.background import M_PL_GEV

REPO = Path(__file__).resolve().parents[2]


def _gen() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "gen_potential_vectors", REPO / "scripts" / "gen_potential_vectors.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_configurator_converts_with_the_engine_s_m_pl() -> None:
    units = _load(REPO / "src" / "lib" / "configDefaults.json")["units"]
    assert units == {"M_PL_GEV": M_PL_GEV}


def test_preview_vectors_are_what_m2_computes() -> None:
    gen = _gen()
    committed = _load(gen.PREVIEW)
    assert committed["psi"] == gen.psi_grid()
    want = gen.preview_vectors()["cases"]
    assert [(c["kind"], c["params"]) for c in committed["cases"]] == [
        (c["kind"], c["params"]) for c in want
    ], "the cases changed: re-run scripts/gen_potential_vectors.py"
    for got, exp in zip(committed["cases"], want, strict=True):
        scale = max(abs(v) for v in exp["V"])
        for x, a, b in zip(committed["psi"], got["V"], exp["V"], strict=True):
            assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-15 * scale), (got["kind"], x, a, b)


def test_preview_vectors_cover_every_built_in_kind_with_its_configurator_default() -> None:
    gen = _gen()
    cases = _load(gen.PREVIEW)["cases"]
    defaults = _load(REPO / "src" / "lib" / "configDefaults.json")["potentialParams"]
    for kind in ("starobinsky", "natural", "hilltop"):
        assert {"kind": kind, "params": defaults[kind]} in [
            {"kind": c["kind"], "params": c["params"]} for c in cases
        ], kind


def test_snippet_vectors_are_the_backend_parser_s_verdicts() -> None:
    gen = _gen()
    committed = _load(gen.SNIPPETS)["cases"]
    assert [c["snippet"] for c in committed] == gen.SNIPPET_CASES
    for case in committed:
        now = gen.backend_verdict(case["snippet"])
        committed_verdict = (case["backend_verdict"], case["backend_reason"])
        assert committed_verdict == (now["verdict"], now["reason"]), case["snippet"]
    verdicts = {c["backend_verdict"] for c in committed}
    assert verdicts == {"accept", "refuse"}, "both verdicts are covered"
