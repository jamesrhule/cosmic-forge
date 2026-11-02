"""W1 PHYS3: M4 units (Decision 11), ΔN_L normalisation, the η_B refusal rule, M6 placeholder.

* M4 divides the M_Pl-unit source ∫dτ a³⟨RR̃⟩ by T_reh³ with T_reh in M_Pl
  (converted at the API boundary). On 9c6bf4c it divided by T_reh in GeV³,
  off by M_PL_GEV³ ≈ 1.44e55.
* ΔN_L is not yet invariant under the scale-factor normalisation a → c·a
  (P1-04): M4 measures that on every run, and ``eta_B_refusal`` refuses η_B
  while it is not, so the Bogoliubov fix (which brought the uncertainty
  budget under 0.5 %) does not turn a convention-dependent number into a
  published η_B.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ucgle_f1.domain import RunConfig
from ucgle_f1.m1_background.background import M_PL_GEV
from ucgle_f1.m3_modes import ChiralSpectrumInputs, solve_chiral_modes
from ucgle_f1.m4_anomaly import AnomalyInputs, delta_N_L
from ucgle_f1.m4_anomaly.anomaly import NORMALISATION_PROBE_C
from ucgle_f1.m7_infer.audit import run_audit
from ucgle_f1.m7_infer.couplings import A_END_H_END, M3_TAU_END, M3_TAU_START, coupling_profile
from ucgle_f1.m7_infer.pipeline import (
    ETA_B_MAX_REL_UNCERTAINTY,
    PipelineResult,
    RunPipeline,
    _budget_total,
    build_run_result,
    eta_B_refusal,
)

_FIXTURE = (
    Path(__file__).resolve().parents[3] / "public" / "fixtures" / "runs" / "kawai-kim-natural.json"
)


def _cfg() -> RunConfig:
    """The kawai-kim-natural fixture's config at precision='fast' (as the adapter tests)."""
    blob = json.loads(_FIXTURE.read_text())
    return RunConfig.model_validate({**blob["config"], "precision": "fast", "agent": None})


KK = _cfg().potential
T_REH_GEV = _cfg().reheating.T_reh_GeV


@pytest.fixture(scope="module")
def pr() -> PipelineResult:
    return RunPipeline(seed=0).run(_cfg())


def _independent_source(modes: object, a_of_tau: object, tau: np.ndarray) -> float:
    # ⟨RR̃⟩(τ) = ∫ dln k (k³/2π²)(|β₊|² − |β₋|²)/a⁴, source = ∫ dτ a³⟨RR̃⟩.
    k = np.asarray(modes.k)  # type: ignore[attr-defined]
    chi = np.abs(modes.beta_plus) ** 2 - np.abs(modes.beta_minus) ** 2  # type: ignore[attr-defined]
    per_mode = k**3 * chi / (2.0 * np.pi**2)
    a = np.array([a_of_tau(float(t)) for t in tau])  # type: ignore[operator]
    rr = np.array([np.trapezoid(per_mode / ai**4, np.log(k)) for ai in a])
    return float(np.trapezoid(a**3 * rr, tau))


def test_delta_n_l_divides_by_t_reh_in_reduced_planck_units(pr: PipelineResult) -> None:
    tau = np.linspace(M3_TAU_START, M3_TAU_END["fast"], 501)
    prof = coupling_profile(KK, _cfg().couplings, tau_start=M3_TAU_START)
    source = _independent_source(pr.modes, prof.a_of_tau, tau)
    assert source != 0.0
    expected = source / (16.0 * np.pi**2 * (T_REH_GEV / M_PL_GEV) ** 3)
    assert pr.anomaly.delta_N_L == pytest.approx(expected, rel=1e-10, abs=0)  # type: ignore[attr-defined]


def test_normalisation_residual_matches_a_full_rescaled_run(pr: PipelineResult) -> None:
    # M4's in-run residual vs an end-to-end M3 + M4 run with a → c·a, τ → τ/c,
    # k → c·k (the reviewers' gauge check): ΔN_L scales by c, so the residual
    # is c − 1. P1-04 must make it 0 (then η_B is no longer refused on it).
    c = NORMALISATION_PROBE_C
    resid = pr.anomaly.normalisation_residual  # type: ignore[attr-defined]
    assert resid == pytest.approx(c - 1.0, rel=1e-9, abs=0)

    cpl, k0 = _cfg().couplings, np.asarray(pr.modes.k)  # type: ignore[attr-defined]
    out = []
    for cc in (1.0, c):
        prof = coupling_profile(KK, cpl, tau_start=M3_TAU_START / cc, a_end_H_end=cc * A_END_H_END)
        tg = np.linspace(M3_TAU_START / cc, M3_TAU_END["fast"] / cc, 501)
        modes = solve_chiral_modes(ChiralSpectrumInputs(
            tau_grid=tg, A=prof.A_of_tau, B=prof.B_of_tau, C=prof.C_of_tau, k_modes=cc * k0,
            rtol=1e-10, atol=1e-14, unitarity_tol=1.0, use_diffrax=False,
        ))
        out.append(delta_N_L(AnomalyInputs(
            tau_grid=tg, a_of_tau=prof.a_of_tau, modes=modes, T_reh=T_REH_GEV / M_PL_GEV,
        )).delta_N_L)
    assert out[1] / out[0] == pytest.approx(1.0 + resid, rel=1e-2, abs=0)


def test_run_result_refuses_eta_b_on_the_normalisation(pr: PipelineResult) -> None:
    # After the Bogoliubov fix the budget is under 0.5 %, so the budget alone
    # would now publish the convention-dependent raw η_B; the normalisation
    # rule keeps it refused.
    assert _budget_total(pr).total <= ETA_B_MAX_REL_UNCERTAINTY
    assert np.isfinite(pr.eta_B) and pr.eta_B != 0.0
    reason = eta_B_refusal(pr)
    assert reason is not None and "normalisation" in reason
    rr = build_run_result("r", _cfg(), pr, audit_runner=run_audit)
    assert np.isnan(rr.eta_B.value) and np.isnan(rr.eta_B.uncertainty)


def _fake(drift: float, resid: float, *, subtracted: bool | None = True) -> PipelineResult:
    """A PipelineResult with only what eta_B_refusal reads. ``subtracted`` is
    M4's adiabatic-subtraction flag (None: an AnomalyResult without it)."""
    anomaly = SimpleNamespace(normalisation_residual=resid)
    if subtracted is not None:
        anomaly.adiabatic_subtraction_implemented = subtracted
    return PipelineResult(
        background=None, scalar_model=None, sgwb=None, eta_B=6.1e-10,
        modes=SimpleNamespace(unitarity_drift=np.array([drift])), anomaly=anomaly,
    )


def test_eta_b_refusal_rule() -> None:
    assert eta_B_refusal(_fake(1e-6, 0.0)) is None
    assert eta_B_refusal(_fake(1e-6, 1e-3)) is None
    assert "normalisation" in (eta_B_refusal(_fake(1e-6, 9.0)) or "")
    assert "normalisation" in (eta_B_refusal(_fake(1e-6, float("nan"))) or "")  # fail closed
    assert "budget" in (eta_B_refusal(_fake(4.0, 0.0)) or "")
    assert "budget" in (eta_B_refusal(_fake(float("nan"), 0.0)) or "")
    # W1 API3: the fourth condition, M4's adiabatic-subtraction flag (P1-04).
    assert "adiabatic subtraction" in (eta_B_refusal(_fake(1e-6, 0.0, subtracted=False)) or "")
    assert "adiabatic subtraction" in (eta_B_refusal(_fake(1e-6, 0.0, subtracted=None)) or "")  # fail closed
    # The first three keep their own reasons when M4 has not subtracted either.
    assert "normalisation" in (eta_B_refusal(_fake(1e-6, 9.0, subtracted=False)) or "")
    assert "budget" in (eta_B_refusal(_fake(4.0, 0.0, subtracted=False)) or "")


def test_m4_reports_that_it_has_not_applied_the_adiabatic_subtraction(pr: PipelineResult) -> None:
    # The flag is M4's report on every run (a module constant P1-04 sets with
    # the scheme), not a value eta_B_refusal hard-codes.
    from ucgle_f1.m4_anomaly import anomaly as m4

    assert m4.ADIABATIC_SUBTRACTION_IMPLEMENTED is False
    assert pr.anomaly.adiabatic_subtraction_implemented is False  # type: ignore[attr-defined]
    assert np.all(m4._adiabatic_subtraction(np.asarray(pr.modes.k)) == 0.0)  # type: ignore[attr-defined]


def test_a_zero_source_run_does_not_publish_eta_b_zero() -> None:
    """W1 API3 (round-3A PHYS3 verifier LOW): θ_grav = 0 makes M4's source
    exactly 0, so the normalisation residual is 0 and the budget is small; on
    15e4e3c RunResult.eta_B was then published as 0.0 ± 0.0. Until P1-04 every
    η_B is refused."""
    blob = json.loads(_FIXTURE.read_text())
    cfg = RunConfig.model_validate({
        **blob["config"], "precision": "fast", "agent": None,
        "couplings": {**blob["config"]["couplings"], "xi": 1.0e-2, "theta_grav": 0.0},
    })
    pr0 = RunPipeline(seed=0).run(cfg)
    rr = build_run_result("r0", cfg, pr0, audit_runner=run_audit)
    assert np.isnan(rr.eta_B.value) and np.isnan(rr.eta_B.uncertainty), (
        f"published eta_B = {rr.eta_B.value} ± {rr.eta_B.uncertainty} for a zero source"
    )
    reason = eta_B_refusal(pr0)
    assert reason is not None and "adiabatic subtraction" in reason
    for c in run_audit(pr0):
        if c.id in ("S8", "S14"):
            assert c.verdict == "FAIL" and c.value is None, (c.id, c.value)


def test_m6_frequencies_are_flagged_as_placeholder(pr: PipelineResult) -> None:
    sg = pr.sgwb
    assert sg.f_Hz_is_placeholder is True  # type: ignore[attr-defined]
    assert "placeholder" in sg.note  # type: ignore[attr-defined]
    # The values themselves (and so the API spectra and R19 pages) are unchanged.
    np.testing.assert_array_equal(sg.f_Hz, 1.0e-19 * np.asarray(pr.modes.k))  # type: ignore[attr-defined]


def test_s8_s14_do_not_publish_a_refused_eta_b(pr: PipelineResult) -> None:
    checks = {c.id: c for c in run_audit(pr)}
    for cid in ("S8", "S14"):
        c = checks[cid]
        assert c.verdict == "FAIL" and c.value is None
        assert "normalisation" in c.notes
        assert c.references == ["1702.07689"]
