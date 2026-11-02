"""The retained ``coupling_model="schematic"`` path still runs (R2: the option stays).

It is diagnostic only (``RunPipeline.coupling_model``): since the f_a/M_PL_GEV
unit fix its CS term is the constant ±θ_grav/f̂_a, which for the
kawai-kim-natural fixture's couplings (θ_grav = 0.78, f_a = 1e16 GeV) is ±189.9,
so one helicity has ω² < 0 and grows exponentially (F_GB ≈ 2e146 there). No
run path selects it. These tests only check that it completes and that its
output is never published as an η_B.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ucgle_f1.domain import AgentTrace, Couplings, Potential, Reheating, RunConfig
from ucgle_f1.m7_infer.audit import run_audit
from ucgle_f1.m7_infer.pipeline import RunPipeline, build_run_result

_FIXTURE = (
    Path(__file__).resolve().parents[3] / "public" / "fixtures" / "runs" / "kawai-kim-natural.json"
)


def _run(cfg: RunConfig) -> None:
    pr = RunPipeline(seed=0, coupling_model="schematic").run(cfg)
    for m in ("M1", "M2", "M3", "M4", "M5", "M6"):
        assert m in pr.module_seconds
    rr = build_run_result("schematic", cfg, pr, audit_runner=run_audit)
    assert rr.audit.summary.total == 15
    assert np.isnan(rr.eta_B.value)  # never published


def test_schematic_path_runs_to_completion() -> None:
    _run(RunConfig(
        potential=Potential(kind="starobinsky", params={"M": 1.0e-5}),
        couplings=Couplings(xi=1e-3, theta_grav=1e-3, f_a=1e17, M_star=1e18, M1=1e12, S_E2=1.0),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13), precision="fast",
        agent=AgentTrace(conversationId="c", hypothesisId="h"),
    ))


@pytest.mark.slow
def test_schematic_path_completes_on_the_fixture_couplings() -> None:
    # The blow-up case: every mode escalates to mpmath (≈ 70 s), but it ends.
    blob = json.loads(_FIXTURE.read_text())
    _run(RunConfig.model_validate({**blob["config"], "precision": "fast", "agent": None}))
