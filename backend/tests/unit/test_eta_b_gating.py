"""W1 merge (round-3A verifier, HIGH): every place a pipeline η_B reaches a user
applies ``eta_B_refusal``, the rule ``RunResult.eta_B`` uses.

After the Bogoliubov fix the uncertainty budget is under 0.5 %, and M4 divides
by T_reh in M_Pl, so the raw η_B is no longer ~1e-42. On 3737f6a the worker's
V2 validation row and the agent's scan cells still used the raw value. A run
whose ``RunResult.eta_B`` is refused (NaN) could then store a V2 "Kawai-Kim
1702.07689" row with status "match" when the raw number happened to fall in the
band, or publish it in a scan cell.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from ucgle_f1.domain import RunConfig
from ucgle_f1.m7_infer import pipeline as pipeline_mod
from ucgle_f1.m7_infer.pipeline import RunPipeline, eta_B_refusal
from ucgle_f1.m8_agent.runs import validation_benchmarks_for
from ucgle_f1.m8_agent.tools.simulator import _scan_cell

_FIXTURE = (
    Path(__file__).resolve().parents[3] / "public" / "fixtures" / "runs" / "kawai-kim-natural.json"
)
_IN_BAND = 6.1e-10  # exactly the V2 target: a raw value here would read "match"


def _stub_pr(eta_b: float) -> SimpleNamespace:
    return SimpleNamespace(eta_B=eta_b, modes=SimpleNamespace(F_GB_per_mode=lambda: [1.0, 3.0]))


def test_a_refused_eta_b_never_yields_a_validation_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline_mod, "eta_B_refusal", lambda pr: "budget above 0.5 %")
    assert validation_benchmarks_for(_stub_pr(_IN_BAND)) == []


def test_a_publishable_eta_b_still_yields_the_v2_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline_mod, "eta_B_refusal", lambda pr: None)
    (row,) = validation_benchmarks_for(_stub_pr(_IN_BAND))
    assert (row.id, row.observed, row.relativeError, row.status) == ("V2", _IN_BAND, 0.0, "match")


def test_a_refused_eta_b_is_nan_in_a_scan_cell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline_mod, "eta_B_refusal", lambda pr: "budget above 0.5 %")
    cell = _scan_cell({"xi": 0.01}, _stub_pr(_IN_BAND))
    assert math.isnan(cell.eta_B)
    assert cell.F_GB == 2.0
    assert json.loads(cell.model_dump_json())["eta_B"] is None  # NaN goes out as null


def test_a_publishable_eta_b_is_kept_in_a_scan_cell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline_mod, "eta_B_refusal", lambda pr: None)
    assert _scan_cell({"xi": 0.01}, _stub_pr(_IN_BAND)).eta_B == _IN_BAND


def test_the_fixture_run_is_refused_everywhere() -> None:
    """End to end on the real pipeline: today every run is refused (M4 normalisation, P1-04)."""
    blob = json.loads(_FIXTURE.read_text())
    cfg = RunConfig.model_validate({**blob["config"], "precision": "fast", "agent": None})
    pr = RunPipeline(seed=0).run(cfg)
    assert eta_B_refusal(pr) is not None
    assert math.isfinite(pr.eta_B)  # a raw number exists; it must not leak
    assert validation_benchmarks_for(pr) == []
    assert math.isnan(_scan_cell({}, pr).eta_B)
