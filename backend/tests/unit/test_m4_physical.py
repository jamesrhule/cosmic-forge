"""P1-04: M4's physical path (canonical tensor modes, V3 adiabatic subtraction, V4 cross-check).

* V4 cross-check on the Kawai–Kim configuration (the kawai-kim-natural
  fixture's config: Decision 11's benchmark potential f_a = 8.7, Λ from
  A_s = 2.207e-9 at N_e = 60, with UCGLE-F1's couplings), at the run's
  precision: n_L from the time-integrated anomaly (Kamada et al.
  arXiv:2007.08029 Eq. 2.24 with ⟨RR̃⟩ of Eq. 2.28, normalised by Eq. 2.29)
  and from the boundary form of Maleknejad arXiv:2412.09490 Eq. 7,
  Δ𝒦 ∝ Σ_s s ∫d³q q(|∂_τ h|² − q²|h|²)|_{τ_in}^{τ}, must agree within the
  run's uncertainty budget.
* ΔN_L is invariant under a → c·a, k → c·k, τ → τ/c (the PHYS3 routing:
  it scaled ∝ c before P1-04), both through M4's own probe and end to end
  through ``coupling_profile(a_end_H_end = c·A_END_H_END)``.
* Parity: θ_grav → −θ_grav flips ΔN_L; θ_grav = 0 gives exactly 0.
* The canonical modes reproduce the de Sitter Bunch–Davies limit
  |h|² → 2H²/k³ outside the horizon (V3 normalisation, Eq. 2.18, z² = a²/2).
* The result does not depend on where the adiabatic vacuum is imposed.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from ucgle_f1.domain import RunConfig
from ucgle_f1.m1_background.background import M_PL_GEV
from ucgle_f1.m4_anomaly.physical import (
    TensorBackground,
    lepton_number,
    solve_mode,
)
from ucgle_f1.m7_infer.couplings import (
    A_END_H_END,
    M3_TAU_START,
    CouplingArrays,
    coupling_profile,
)
from ucgle_f1.m7_infer.pipeline import PipelineResult, RunPipeline, _budget_total

_FIXTURE = (
    Path(__file__).resolve().parents[3] / "public" / "fixtures" / "runs" / "kawai-kim-natural.json"
)
K_FAST = np.logspace(-1.0, 1.0, 8)   # the pipeline's 'fast' k-grid


def _cfg(**couplings: float) -> RunConfig:
    blob = json.loads(_FIXTURE.read_text())
    cfg = {**blob["config"], "precision": "fast", "agent": None}
    if couplings:
        cfg["couplings"] = {**cfg["couplings"], **couplings}
    return RunConfig.model_validate(cfg)


T_REH = _cfg().reheating.T_reh_GeV / M_PL_GEV


@pytest.fixture(scope="module")
def pr() -> PipelineResult:
    return RunPipeline(seed=0).run(_cfg())


@pytest.fixture(scope="module")
def bg() -> TensorBackground:
    prof = coupling_profile(_cfg().potential, _cfg().couplings, tau_start=M3_TAU_START)
    assert prof.arrays is not None
    return TensorBackground(prof.arrays)


def test_v4_cross_check_agrees_within_the_run_budget_on_kawai_kim(pr: PipelineResult) -> None:
    an = pr.anomaly
    budget = _budget_total(pr).total
    assert an.adiabatic_subtraction_implemented is True  # type: ignore[attr-defined]
    assert an.adiabatic_order == 4  # type: ignore[attr-defined]
    assert an.delta_N_L != 0.0  # type: ignore[attr-defined]
    # Time-integrated (V3 Eq. 2.24) vs boundary form (V4 Eq. 7).
    assert an.v4_rel_disagreement <= budget  # type: ignore[attr-defined]
    assert an.delta_Q_A_V4 == pytest.approx(an.delta_N_L, rel=budget, abs=0)  # type: ignore[attr-defined]
    # Measured: ~1e-9, far inside the 2.45e-3 'fast' budget.
    assert an.v4_rel_disagreement < 1e-6  # type: ignore[attr-defined]


def test_delta_n_l_is_y_l_at_reheating(pr: PipelineResult) -> None:
    # Y_L = n_L(τ_end) T_reh / (4 H_end²) (w = 0 reheating, g_* cancels), T_reh in M_Pl.
    prof = coupling_profile(_cfg().potential, _cfg().couplings, tau_start=M3_TAU_START)
    H_end = float(prof.arrays.H[-1])  # type: ignore[union-attr]
    an = pr.anomaly
    assert an.delta_N_L == pytest.approx(  # type: ignore[attr-defined]
        an.n_L_end * T_REH / (4.0 * H_end**2), rel=1e-12, abs=0  # type: ignore[attr-defined]
    )


@pytest.mark.parametrize("c", [0.1, 10.0])
def test_delta_n_l_is_invariant_under_a_to_ca(bg: TensorBackground, c: float) -> None:
    base = lepton_number(bg, K_FAST, T_REH)
    probe = lepton_number(bg.rescaled(c), c * K_FAST, T_REH)
    assert probe.Y_L == pytest.approx(base.Y_L, rel=1e-6, abs=0)
    assert probe.n_L_time == pytest.approx(base.n_L_time, rel=1e-6, abs=0)

    # End to end: rebuild the background with a_end H_end → c a_end H_end (τ → τ/c).
    prof = coupling_profile(_cfg().potential, _cfg().couplings, tau_start=M3_TAU_START / c,
                            a_end_H_end=c * A_END_H_END)
    full = lepton_number(TensorBackground(prof.arrays), c * K_FAST, T_REH)  # type: ignore[arg-type]
    assert full.Y_L == pytest.approx(base.Y_L, rel=1e-6, abs=0)


def test_pipeline_normalisation_residual_is_below_policy(pr: PipelineResult) -> None:
    assert pr.anomaly.normalisation_residual <= 1e-6  # type: ignore[attr-defined]


def test_parity_flip_and_zero_cs_coupling() -> None:
    cpl = _cfg().couplings
    out = {}
    for th in (cpl.theta_grav, -cpl.theta_grav, 0.0):
        c = _cfg(theta_grav=th)
        prof = coupling_profile(c.potential, c.couplings, tau_start=M3_TAU_START)
        out[th] = lepton_number(TensorBackground(prof.arrays), K_FAST, T_REH)  # type: ignore[arg-type]
    assert out[cpl.theta_grav].Y_L != 0.0
    assert out[-cpl.theta_grav].Y_L == pytest.approx(-out[cpl.theta_grav].Y_L, rel=1e-9, abs=0)
    assert out[0.0].Y_L == 0.0 and out[0.0].Y_L_V4 == 0.0


def test_start_of_the_adiabatic_vacuum_does_not_matter(bg: TensorBackground) -> None:
    a = lepton_number(bg, K_FAST, T_REH, x_start=100.0)
    b = lepton_number(bg, K_FAST, T_REH, x_start=200.0)
    assert b.Y_L == pytest.approx(a.Y_L, rel=1e-5, abs=0)


def _de_sitter(theta: float, H: float = 1.0, n_end: float = 30.0) -> TensorBackground:
    N = np.linspace(0.0, n_end, 30001)
    a = np.exp(N - n_end)
    zero = np.zeros_like(N)
    # Kamada et al. Sec. 2.1: Θ = −8 H f′/a constant, g = f′/a² = −Θ/(8 H a).
    return TensorBackground(CouplingArrays(
        N=N, tau=-1.0 / (a * H), a=a, H=np.full_like(N, H), eps=zero, delta_T=zero, Delta=zero,
        g=-theta / (8.0 * H * a), a_end_H_end=H,
    ))


@pytest.mark.parametrize("k", [1e-2, 3e-2, 0.1])
def test_canonical_modes_reach_the_de_sitter_bunch_davies_limit(k: float) -> None:
    # u ≃ k^{−1/2} e^{−ikτ}(1 − i/(kτ)) (V3 Eq. 2.18 normalisation), z = a/√2:
    # |h|² = 2|u|²/a² → 2H²/k³ (1 + (kτ)²) at τ = −1/(aH).
    H = 1.0
    m = solve_mode(_de_sitter(0.0, H), k)
    tau = -1.0 / H
    exact = 2.0 * H**2 / k**3 * (1.0 + (k * tau) ** 2)
    assert abs(m.h_end) ** 2 == pytest.approx(exact, rel=1e-6, abs=0)
    assert m.dh_end == 0.0 and m.S_end == 0.0   # no CS coupling: no parity-odd part


def test_de_sitter_subtracted_source_has_the_kamada_uv_tail() -> None:
    """V3 Eq. 3.21: after the order-4 subtraction the per-mode source
    d𝒥/d ln k → a³H⁵κ̃/π² · (6 (k/aH)² − 10) — the slopes of the 3(Λ/H)²
    (order 6) and −10 ln Λ (order 8) terms — up to O((aH/k)²).

    Measured (k ≤ 30, 241 modes, recorded in evidence/P1-04.md): the
    remainder is ≲ 65/k² for k ≳ 5 (with an oscillating part: these modes
    are inside the horizon at the end), and integrating the whole band gives
    𝒥_sub(Λ) = 3Λ² − 10 ln Λ + 6.58, against V3 Eq. 3.13's finite part
    39/2 − 10γ − 10 ln 2 = 6.80 (3 %; V3 Sec. 3.1 notes that the finite part
    depends on the vacuum).
    """
    from ucgle_f1.m4_anomaly.adiabatic import AdiabaticJ

    theta = 1e-4
    bg = _de_sitter(theta)
    J = AdiabaticJ(4)
    end = bg.adiabatic_background(bg.N_end)
    unit = 1.0 / math.sqrt(256.0 / theta**2 - 3.0) / math.pi**2  # a³H⁵κ̃/π², a = H = 1
    for k in (8.0, 12.0, 16.0):
        # Inside the horizon at the end |h′|² − k²|h|² cancels to (aH/k)², so
        # these modes need a tighter tolerance than the pipeline's (whose
        # modes are all outside the horizon at the end of inflation).
        m = solve_mode(bg, k, rtol=1e-11)
        raw = m.S_end * k**3 / (2 * math.pi**2) / unit
        sub = (m.S_end - float(J.integrand(k, end))) * k**3 / (2 * math.pi**2) / unit
        assert raw - sub == pytest.approx(4.0 * k**4, rel=1e-9, abs=0)   # the Λ⁴ term removed
        assert abs(sub - (6.0 * k**2 - 10.0)) <= 80.0 / k**2


def test_a_trajectory_too_short_for_the_adiabatic_start_degrades_not_crashes(pr: PipelineResult) -> None:
    """Keep only the last 12 e-folds: the lowest 'fast' mode (k = 0.1) needs
    k/(aH) = 100, i.e. aH = 1e-3, ≈ 13.8 e-folds before the end. M4 must
    return NaN with a reason and η_B must be refused with it, not raise."""
    from dataclasses import replace as dc_replace

    from ucgle_f1.m4_anomaly import AnomalyInputs, delta_N_L
    from ucgle_f1.m7_infer.pipeline import eta_B_refusal

    ar = coupling_profile(_cfg().potential, _cfg().couplings, tau_start=M3_TAU_START).arrays
    assert ar is not None
    keep = ar.N >= ar.N[-1] - 12.0
    short = dc_replace(ar, **{f: getattr(ar, f)[keep] for f in
                              ("N", "tau", "a", "H", "eps", "delta_T", "Delta", "g")})
    an = delta_N_L(AnomalyInputs(
        tau_grid=np.linspace(-5.0, -1.0, 11), a_of_tau=lambda t: 1.0, modes=pr.modes,  # type: ignore[arg-type]
        T_reh=T_REH, background=short,
    ))
    assert an.physical_error is not None and "adiabatic vacuum" in an.physical_error
    assert math.isnan(an.delta_N_L) and an.quad_flag is True
    fake = PipelineResult(background=None, scalar_model=None, modes=pr.modes, anomaly=an,
                          sgwb=None, eta_B=float("nan"))
    reason = eta_B_refusal(fake)
    assert reason is not None and "could not evaluate" in reason


def test_a_short_inflation_run_completes_with_eta_b_refused() -> None:
    """End to end: φ₀ = 6.5 gives 11.1 e-folds of inflation, enough for M3's
    window (τ = −5 is 10.06 e-folds before the end) but not for M4's adiabatic
    start of k = 0.1 (≈ 13.8). The run completes and η_B is refused; before
    P1-04 such a run completed too (with η_B refused), so this is no regression."""
    from ucgle_f1.m7_infer.audit import run_audit
    from ucgle_f1.m7_infer.pipeline import build_run_result, eta_B_refusal

    blob = json.loads(_FIXTURE.read_text())
    cfg = dict(blob["config"])
    cfg["potential"] = {**cfg["potential"], "params": {**cfg["potential"]["params"], "phi0": 6.5}}
    rc = RunConfig.model_validate({**cfg, "precision": "fast", "agent": None})
    run = RunPipeline(seed=0).run(rc)
    assert run.anomaly.physical_error is not None  # type: ignore[attr-defined]
    rr = build_run_result("short", rc, run, audit_runner=run_audit)
    assert math.isnan(rr.eta_B.value)
    reason = eta_B_refusal(run)
    assert reason is not None and "could not evaluate" in reason
    rr.model_dump_json()  # serialisable (NaN fields included)
