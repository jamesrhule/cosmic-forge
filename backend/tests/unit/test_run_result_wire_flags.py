"""W1 FE3: what a refused η_B and M6's placeholder frequencies look like on the wire.

* ``RunResult.eta_B.value`` is NaN whenever ``eta_B_refusal`` refuses it.
  FastAPI's JSON carries that as ``null``; the worker's stored result (what
  the platform route ``GET /api/qcompass/domains/…/runs/{id}`` serves) as the
  string ``"NaN"`` (``jobs._finite``). The reason travels with it as
  ``eta_B.refusal`` so the UI can say "η_B not published — <reason>"
  instead of showing nothing or "NaN".
* M6's ``SGWBResult.f_Hz_is_placeholder`` and ``note`` reach
  ``RunResult.spectra.sgwb``, so the API, SDK and UI can label the
  frequency axis as placeholder (R6).

Both tests read only the JSON dump (dict keys), so they run unchanged on a
tree without the new fields and fail there for the missing information.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ucgle_f1.domain import RunConfig, RunResult
from ucgle_f1.jobs import _dumps
from ucgle_f1.m6_gw.sgwb import PLACEHOLDER_NOTE
from ucgle_f1.m7_infer.audit import run_audit
from ucgle_f1.m7_infer.pipeline import PipelineResult, RunPipeline, build_run_result, eta_B_refusal

_FIXTURE = (
    Path(__file__).resolve().parents[3] / "public" / "fixtures" / "runs" / "kawai-kim-natural.json"
)


def _cfg() -> RunConfig:
    blob = json.loads(_FIXTURE.read_text())
    return RunConfig.model_validate({**blob["config"], "precision": "fast", "agent": None})


@pytest.fixture(scope="module")
def pr() -> PipelineResult:
    return RunPipeline(seed=0).run(_cfg())


@pytest.fixture(scope="module")
def result(pr: PipelineResult) -> RunResult:
    return build_run_result("fe3-wire", _cfg(), pr, audit_runner=run_audit)


@pytest.fixture(scope="module")
def wire(result: RunResult) -> dict:
    """FastAPI's JSON for a RunResult response (``GET /api/runs/{id}``)."""
    return json.loads(result.model_dump_json())


@pytest.fixture(scope="module")
def stored(result: RunResult) -> dict:
    """The worker's stored result, as the platform route serves it."""
    return json.loads(_dumps(result.model_dump(mode="json")))


def test_refused_eta_b_carries_its_reason_on_the_wire(
    pr: PipelineResult, wire: dict, stored: dict,
) -> None:
    reason = eta_B_refusal(pr)
    assert reason, "the default config's η_B is refused today (P1-04)"
    assert wire["eta_B"]["value"] is None and wire["eta_B"]["uncertainty"] is None
    assert stored["eta_B"]["value"] == "NaN"
    for body in (wire, stored):
        assert body["eta_B"].get("refusal") == reason
        # Both round-trip through the model.
        assert RunResult.model_validate(body).eta_B.refusal == reason


def test_sgwb_spectrum_carries_the_m6_placeholder_flag(
    pr: PipelineResult, wire: dict, stored: dict,
) -> None:
    assert pr.sgwb.f_Hz_is_placeholder is True  # type: ignore[attr-defined]
    for body in (wire, stored):
        sgwb = body["spectra"]["sgwb"]
        assert sgwb.get("f_Hz_is_placeholder") is True
        assert sgwb.get("note") == PLACEHOLDER_NOTE
        # The values are unchanged: still M6's placeholder conversion.
        assert sgwb["f_Hz"] == [float(f) for f in pr.sgwb.f_Hz]  # type: ignore[attr-defined]


def test_a_stored_result_without_the_new_fields_still_validates(wire: dict) -> None:
    # Results stored before this change (and the bundled fixtures) lack both
    # fields; they stay valid and read as "unknown", never as "not a placeholder".
    legacy = json.loads(json.dumps(wire))
    legacy["eta_B"].pop("refusal")
    for k in ("f_Hz_is_placeholder", "note"):
        legacy["spectra"]["sgwb"].pop(k)
    rr = RunResult.model_validate(legacy)
    assert rr.eta_B.refusal is None
    assert rr.spectra.sgwb.f_Hz_is_placeholder is None and rr.spectra.sgwb.note is None
