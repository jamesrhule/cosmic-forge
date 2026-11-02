"""End-to-end M1→M6 pipeline producing a ``RunResult``.

This is the single integration point every agent-initiated run
passes through. It is deterministic given a seed: the module times
and unitarity drift may vary, but η_B, F_GB, and the spectra are
reproducible to within the configured tolerance.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Callable

import numpy as np

from ..domain import (
    AuditCheck,
    AuditReport,
    AuditSummary,
    EtaB,
    ModeSpectrum,
    RunConfig,
    RunResult,
    RunSpectra,
    RunTiming,
    SgwbSpectrum,
    UncertaintyBudget,
    ValidationBenchmark,
    ValidationReport,
)
from ..m1_background import BackgroundInputs, solve_background
from ..m2_scalar import build_scalar_model
from ..m3_modes import ChiralSpectrumInputs, solve_chiral_modes
from ..m4_anomaly import AnomalyInputs, delta_N_L
from ..m5_boltzmann import AsymmetryInputs, eta_B_from_delta_N_L
from ..m6_gw import compute_sgwb
from ..m1_background.background import M_PL_GEV
from .couplings import M3_TAU_END, M3_TAU_START, coupling_profile

# Hook point for the S1–S15 audit harness, imported lazily to avoid a
# cycle (audit imports domain types from here).
AuditRunner = Callable[["PipelineResult"], list[AuditCheck]]


@dataclass
class PipelineResult:
    """Raw outputs from each module — pre-translation to RunResult."""

    background: object
    scalar_model: object
    modes: object
    anomaly: object
    sgwb: object
    eta_B: float
    module_seconds: dict[str, float] = field(default_factory=dict)
    config: RunConfig | None = None


@dataclass
class RunPipeline:
    """Orchestrates the M1→M6 chain.

    Precision policy: the pipeline refuses to emit η_B when the
    integrated uncertainty exceeds 0.5% (see :func:`_budget_total`) or
    when ΔN_L still depends on the scale-factor normalisation (see
    :func:`eta_B_refusal`).
    """

    seed: int = 0
    # P1-03 / JAMES DECISION 11: "physical" (the default) uses
    # m7_infer/couplings.py, the CS/GB couplings on the inflaton trajectory.
    # "schematic" keeps the original placeholder A/B and a(τ) = 1/|τ|. It is
    # DIAGNOSTIC ONLY (kept under R2, never selected by a run path): since
    # the f_a/M_PL_GEV unit fix its CS term is the constant ±θ_grav/f̂_a
    # (±189.9 for the kawai-kim-natural fixture's couplings), so one
    # helicity has ω² < 0 and grows exponentially (that fixture: F_GB ≈ 2e146).
    # ``tests/unit/test_schematic_smoke.py`` only checks it still runs.
    coupling_model: str = "physical"

    def run(
        self,
        cfg: RunConfig,
        on_module: Callable[[str, float], None] | None = None,
    ) -> PipelineResult:
        """Run M1→M6. ``on_module(module, seconds)`` is called as each module
        finishes (P3-02: real per-module progress, never pre-emitted)."""
        rng = np.random.default_rng(self.seed)
        times: dict[str, float] = {}

        # ── M1 ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        bg = solve_background(
            BackgroundInputs(
                rho_phi_init=1.0e-9,
                rho_r_init=1.0e-20,
                # API boundary: Γ_φ arrives in GeV (UI: "inflaton decay
                # rate [GeV]"); M1 works in reduced-Planck units.
                Gamma_phi=cfg.reheating.Gamma_phi / M_PL_GEV,
            )
        )
        times["M1"] = time.perf_counter() - t0
        if on_module is not None:
            on_module("M1", times["M1"])

        # ── M2 ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        # API boundary, as for Γ_φ above (W1-PARAMS): the potential's
        # parameters arrive in API units (natural f and hilltop μ in GeV);
        # ``engine()`` converts them once, with M_PL_GEV, into M2's units.
        potential = cfg.potential.engine()
        scalar = build_scalar_model(potential)
        times["M2"] = time.perf_counter() - t0
        if on_module is not None:
            on_module("M2", times["M2"])

        # ── M3 ────────────────────────────────────────────────────────
        # τ-grid spans from deep inside the Bunch-Davies regime
        # (|k τ| ≫ 1) down to horizon crossing. The smoke-test default
        # is a modest span so DOP853 converges in seconds; V2 recovery
        # requires ``precision='high'`` (τ_grid is widened there).
        t0 = time.perf_counter()
        tau_grid = np.linspace(M3_TAU_START, M3_TAU_END[cfg.precision], 501)

        if self.coupling_model == "physical":
            # Physical CS / GB couplings on the inflaton trajectory (P1-03,
            # m7_infer/couplings.py): A_± (parity-odd, Chern–Simons),
            # B and C = c_T² − 1 (parity-even, Gauss–Bonnet).
            profile = coupling_profile(potential, cfg.couplings, tau_start=float(tau_grid[0]))
            A, B, C = profile.A_of_tau, profile.B_of_tau, profile.C_of_tau
            a_of_tau = profile.a_of_tau
        elif self.coupling_model == "schematic":
            # Diagnostic only (see ``coupling_model`` above): not physical.

            def A(tau: float) -> np.ndarray:
                # CS contribution: σ × θ_grav × dφ/dτ / f_a in schematic form
                # (the dφ/dτ factor was never implemented: A is constant).
                # f_a arrives in GeV (API boundary); M3 works in M_Pl units.
                val = cfg.couplings.theta_grav / (cfg.couplings.f_a / M_PL_GEV)
                return np.array([+val, -val])

            def B(tau: float) -> np.ndarray:
                # GB contribution: ξ × d²f(φ)/dτ² — helicity-independent.
                val = cfg.couplings.xi * 1.0e-4 * np.exp(-0.1 * abs(tau))
                return np.array([val, val])

            C = None

            def a_of_tau(t: float) -> float:
                return 1.0 / max(abs(t), 1e-6)

        else:
            msg = f"unknown coupling_model {self.coupling_model!r}"
            raise ValueError(msg)

        # Precision ladder: fast → coarse k-grid + relaxed unitarity
        # tolerance; high → fine grid + mpmath escalation at 1e-12.
        # k-range is also ladder-scaled: fast runs cap |k τ_end| so the
        # DOP853 path finishes in a few seconds; high precision widens
        # to the V2 band [1e-3, 1e3] M_Pl.
        precision_ladder = {
            "fast":     {"nk": 8,  "k_lo": -1.0, "k_hi": 1.0,
                         "utol": 1e-4,  "rtol": 1e-6,  "atol": 1e-8},
            "standard": {"nk": 16, "k_lo": -2.0, "k_hi": 2.0,
                         "utol": 1e-4,  "rtol": 1e-8,  "atol": 1e-10},
            "high":     {"nk": 64, "k_lo": -3.0, "k_hi": 3.0,
                         "utol": 1e-12, "rtol": 1e-10, "atol": 1e-12},
        }
        pp = precision_ladder[cfg.precision]
        k_modes = np.logspace(pp["k_lo"], pp["k_hi"], pp["nk"])
        mode_inp = ChiralSpectrumInputs(
            tau_grid=tau_grid,
            A=A,
            B=B,
            C=C,
            k_modes=k_modes,
            rtol=pp["rtol"],
            atol=pp["atol"],
            unitarity_tol=pp["utol"],
            use_diffrax=False,  # portable default; JAX path opts in
        )
        modes = solve_chiral_modes(mode_inp)
        times["M3"] = time.perf_counter() - t0
        if on_module is not None:
            on_module("M3", times["M3"])

        # ── M4 ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        anomaly = delta_N_L(
            AnomalyInputs(
                tau_grid=tau_grid,
                a_of_tau=a_of_tau,
                modes=modes,
                # API boundary, as for Γ_φ: T_reh arrives in GeV; M4 works
                # in reduced-Planck units like M3's source (Decision 11).
                T_reh=cfg.reheating.T_reh_GeV / M_PL_GEV,
            )
        )
        times["M4"] = time.perf_counter() - t0
        if on_module is not None:
            on_module("M4", times["M4"])

        # ── M5 ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        eta = eta_B_from_delta_N_L(
            AsymmetryInputs(
                delta_N_L=anomaly.delta_N_L,
                T_reh_GeV=cfg.reheating.T_reh_GeV,
            )
        )
        times["M5"] = time.perf_counter() - t0
        if on_module is not None:
            on_module("M5", times["M5"])

        # ── M6 ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        sgwb = compute_sgwb(modes)
        times["M6"] = time.perf_counter() - t0
        if on_module is not None:
            on_module("M6", times["M6"])

        _ = rng  # reserved for Monte-Carlo subcycles

        return PipelineResult(
            background=bg,
            scalar_model=scalar,
            modes=modes,
            anomaly=anomaly,
            sgwb=sgwb,
            eta_B=eta,
            module_seconds=times,
            config=cfg,
        )


def _budget_total(result: PipelineResult) -> UncertaintyBudget:
    # Per-module quadrature budget; values scaled to the chiral drift.
    drift = float(np.max(result.modes.unitarity_drift)) if hasattr(  # type: ignore[attr-defined]
        result.modes, "unitarity_drift"
    ) else 0.0
    stat = 1e-4
    grid = 2e-3
    scheme = max(1e-3, drift)
    inputs = 1e-3
    total = float(np.sqrt(stat**2 + grid**2 + scheme**2 + inputs**2))
    return UncertaintyBudget(
        statistical=stat,
        gridSystematic=grid,
        schemeSystematic=scheme,
        inputPropagation=inputs,
        total=total,
    )


# Precision policy: η_B is refused above a 0.5 % budget.
ETA_B_MAX_REL_UNCERTAINTY = 5e-3


def eta_B_refusal(pr: PipelineResult) -> str | None:
    """Why this run's η_B must not be emitted, or ``None`` when it may be.

    The one refusal rule for every place a pipeline η_B reaches a user:
    ``RunResult.eta_B`` here, and the worker's / agent's validation rows
    and scan cells, which must apply the same rule. Three reasons:

    * the unitarity drift is not finite (the budget is then undefined);
    * the uncertainty budget (:func:`_budget_total`) exceeds 0.5 %;
    * ΔN_L depends on the scale-factor normalisation, i.e. M4's
      ``normalisation_residual`` exceeds the same 0.5 % (P1-04 gap; it is
      c − 1 = 9 for every run today, so η_B is always refused until P1-04
      matches a to reheating, as LEDGER Decision 13(b) anticipates).
    """
    drift = np.asarray(getattr(pr.modes, "unitarity_drift", np.nan), dtype=float)
    if not np.all(np.isfinite(drift)):
        # _budget_total's max(1e-3, nan) would read a NaN drift as 1e-3.
        return "uncertainty budget undefined: non-finite unitarity drift"
    budget = _budget_total(pr)
    if not budget.total <= ETA_B_MAX_REL_UNCERTAINTY:
        return f"uncertainty budget {budget.total:.3g} exceeds {ETA_B_MAX_REL_UNCERTAINTY:g}"
    resid = float(getattr(pr.anomaly, "normalisation_residual", float("nan")))
    if not resid <= ETA_B_MAX_REL_UNCERTAINTY:
        return (
            f"ΔN_L depends on the scale-factor normalisation (residual {resid:.3g}); "
            "M4 does not yet match a to reheating (P1-04)"
        )
    return None


def build_run_result(
    run_id: str,
    cfg: RunConfig,
    pr: PipelineResult,
    audit_runner: AuditRunner | None = None,
    validation_benchmarks: list[ValidationBenchmark] | None = None,
) -> RunResult:
    budget = _budget_total(pr)
    # Precision policy (:func:`eta_B_refusal`): refuse to emit η_B, and say why.
    refusal = eta_B_refusal(pr)
    eta_value = float("nan") if refusal is not None else pr.eta_B

    modes = pr.modes  # type: ignore[assignment]
    sgwb = pr.sgwb  # type: ignore[assignment]

    audit_checks = audit_runner(pr) if audit_runner is not None else []
    passed = sum(1 for c in audit_checks if c.verdict.startswith("PASS"))
    audit = AuditReport(
        checks=audit_checks,
        summary=AuditSummary(
            passed=passed,
            total=len(audit_checks),
            blocking=any(c.verdict == "FAIL" for c in audit_checks),
        ),
    )

    spectra = RunSpectra(
        sgwb=SgwbSpectrum(
            f_Hz=list(map(float, sgwb.f_Hz)),
            Omega_gw=list(map(float, sgwb.Omega_gw)),
            chirality=list(map(float, sgwb.chirality)),
            # M6's placeholder flag and note reach the API (R6).
            f_Hz_is_placeholder=bool(sgwb.f_Hz_is_placeholder),
            note=sgwb.note,
        ),
        modes=ModeSpectrum(
            k=list(map(float, modes.k)),
            h_plus=list(map(float, np.abs(modes.beta_plus))),
            h_minus=list(map(float, np.abs(modes.beta_minus))),
        ),
    )

    return RunResult(
        id=run_id,
        config=cfg,
        status="completed",
        eta_B=EtaB(
            value=eta_value,
            uncertainty=eta_value * budget.total if np.isfinite(eta_value) else float("nan"),
            budget=budget,
            refusal=refusal,
        ),
        F_GB=float(np.mean(modes.F_GB_per_mode())),
        audit=audit,
        spectra=spectra,
        timing=RunTiming(wall_seconds=sum(pr.module_seconds.values()),
                         module_seconds=pr.module_seconds),
        validation=ValidationReport(benchmarks=validation_benchmarks or []),
        createdAt=datetime.now(UTC),
    )
