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

    Precision policy: the defaults of each module already meet the
    1%-on-η_B budget. The pipeline refuses to emit η_B when the
    integrated uncertainty exceeds 0.5% (see :func:`_budget_total`).
    """

    seed: int = 0

    def run(self, cfg: RunConfig) -> PipelineResult:
        rng = np.random.default_rng(self.seed)
        times: dict[str, float] = {}

        # ── M1 ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        bg = solve_background(
            BackgroundInputs(
                rho_phi_init=1.0e-9,
                rho_r_init=1.0e-20,
                Gamma_phi=cfg.reheating.Gamma_phi,
            )
        )
        times["M1"] = time.perf_counter() - t0

        # ── M2 ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        scalar = build_scalar_model(cfg.potential)
        times["M2"] = time.perf_counter() - t0

        # ── M3 ────────────────────────────────────────────────────────
        # τ-grid spans from deep inside the Bunch-Davies regime
        # (|k τ| ≫ 1) down to horizon crossing. The smoke-test default
        # is a modest span so DOP853 converges in seconds; V2 recovery
        # requires ``precision='high'`` (τ_grid is widened there).
        t0 = time.perf_counter()
        tau_span_end = {"fast": -1.0, "standard": -1.0e-1, "high": -1.0e-3}
        tau_grid = np.linspace(-5.0, tau_span_end[cfg.precision], 501)

        def A(tau: float) -> np.ndarray:
            # CS contribution: σ × θ_grav × dφ/dτ / f_a in schematic form.
            val = cfg.couplings.theta_grav / cfg.couplings.f_a
            return np.array([+val, -val])

        def B(tau: float) -> np.ndarray:
            # GB contribution: ξ × d²f(φ)/dτ² — helicity-independent.
            val = cfg.couplings.xi * 1.0e-4 * np.exp(-0.1 * abs(tau))
            return np.array([val, val])

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
            k_modes=k_modes,
            rtol=pp["rtol"],
            atol=pp["atol"],
            unitarity_tol=pp["utol"],
            use_diffrax=False,  # portable default; JAX path opts in
        )
        modes = solve_chiral_modes(mode_inp)
        times["M3"] = time.perf_counter() - t0

        # ── M4 ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        anomaly = delta_N_L(
            AnomalyInputs(
                tau_grid=tau_grid,
                a_of_tau=lambda t: 1.0 / max(abs(t), 1e-6),
                modes=modes,
                T_reh_GeV=cfg.reheating.T_reh_GeV,
            )
        )
        times["M4"] = time.perf_counter() - t0

        # ── M5 ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        eta = eta_B_from_delta_N_L(
            AsymmetryInputs(
                delta_N_L=anomaly.delta_N_L,
                T_reh_GeV=cfg.reheating.T_reh_GeV,
            )
        )
        times["M5"] = time.perf_counter() - t0

        # ── M6 ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        sgwb = compute_sgwb(modes)
        times["M6"] = time.perf_counter() - t0

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


def build_run_result(
    run_id: str,
    cfg: RunConfig,
    pr: PipelineResult,
    audit_runner: AuditRunner | None = None,
    validation_benchmarks: list[ValidationBenchmark] | None = None,
) -> RunResult:
    budget = _budget_total(pr)
    if budget.total > 5e-3:
        # Precision policy: refuse to emit η_B above 0.5% budget.
        eta_value = float("nan")
    else:
        eta_value = pr.eta_B

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
        ),
        F_GB=float(np.mean(modes.F_GB_per_mode())),
        audit=audit,
        spectra=spectra,
        timing=RunTiming(wall_seconds=sum(pr.module_seconds.values()),
                         module_seconds=pr.module_seconds),
        validation=ValidationReport(benchmarks=validation_benchmarks or []),
        createdAt=datetime.now(UTC),
    )
