"""PH-H1: a resolvable Gauss–Bonnet signal on the default (physical) path.

The frozen ``audit/physics/test_parity_hypothesis.py::test_gb_to_zero_decoupling``
asserts f0 ≤ f + 1e-9 on a Starobinsky config at ``precision='fast'``, where
the GB signal F(ξ) − F(0) is ≲ 3e-27 (ξ ≤ 1e-2): its 1e-9 slack is ~10¹⁸ times
the signal, so it holds literally but cannot see the GB term. This test uses
the Kawai–Kim natural benchmark potential (LEDGER Decision 11: f_a = 8.7 M_Pl,
Λ from A_s), whose window τ ∈ [−5, −1] (10.06 → 8.35 e-folds before the end)
carries a larger ξ̇, and the same UCGLE-F1 couplings as the frozen test
(θ_grav = 1e-3, f_a = 1e17 GeV) with ξ = ±1e-2, 2e-2.

Physics of the sign. To first order in the couplings β_λ = β_GB + λ β_CS
(GB parity-even: B, C helicity-independent; CS parity-odd: A_+ = −A_−), so the
helicity average F = ½(|β₊|² + |β₋|²) = |β_GB|² + |β_CS|²: the GB–CS
interference cancels, and F(ξ) − F(0) = |β_GB|² ≥ 0, even and quadratic in ξ.
The tests check that sign on every mode, check the size against an independent
first-order (Born) integral of the coupling profile, and require the signal to
exceed the integrator floor (free waves, ξ = θ = 0, where the exact answer is 0)
by three orders of magnitude.

On 9c6bf4c (the i√(k/2) Bogoliubov extraction) these fail: F(0) is the artefact
0.6727 and ΔF has no definite sign or size.
"""

from __future__ import annotations

import numpy as np
import pytest

from ucgle_f1.domain import AgentTrace, Couplings, Potential, Reheating, RunConfig
from ucgle_f1.m2_scalar.natural import kawai_kim_natural_params
from ucgle_f1.m7_infer.couplings import M3_TAU_END, M3_TAU_START, coupling_profile
from ucgle_f1.m7_infer.pipeline import PipelineResult, RunPipeline

KK = Potential(kind="natural", params=kawai_kim_natural_params())
THETA = 1.0e-3
XI = 1.0e-2


def _cfg(xi: float, theta: float) -> RunConfig:
    return RunConfig(
        potential=KK,
        couplings=Couplings(
            xi=xi, theta_grav=theta, f_a=1.0e17, M_star=1.0e18, M1=1.0e12, S_E2=1.0,
        ),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13),
        precision="fast",
        agent=AgentTrace(conversationId="c", hypothesisId="h"),
    )


@pytest.fixture(scope="module")
def runs() -> dict[tuple[float, float], PipelineResult]:
    # Default pipeline (physical couplings), as the frozen test runs it.
    pts = [(0.0, 0.0), (0.0, THETA), (XI, THETA), (-XI, THETA), (2 * XI, THETA)]
    return {p: RunPipeline(seed=0).run(_cfg(*p)) for p in pts}


def _f_gb(r: PipelineResult) -> np.ndarray:
    return np.asarray(r.modes.F_GB_per_mode())  # type: ignore[attr-defined]


def _d_f(runs: dict[tuple[float, float], PipelineResult], xi: float) -> np.ndarray:
    return _f_gb(runs[(xi, THETA)]) - _f_gb(runs[(0.0, THETA)])


def test_integrator_floor_is_far_below_the_signal(
    runs: dict[tuple[float, float], PipelineResult],
) -> None:
    floor = float(np.mean(_f_gb(runs[(0.0, 0.0)])))  # exact answer: 0 (free waves)
    signal = float(np.mean(_d_f(runs, XI)))
    assert floor < 1e-28
    assert signal > 1e3 * floor, f"GB signal {signal:.3e} vs floor {floor:.3e}"


@pytest.mark.parametrize("xi", [XI, -XI, 2 * XI])
def test_gb_raises_f_gb_on_every_mode(
    runs: dict[tuple[float, float], PipelineResult], xi: float,
) -> None:
    d_f = _d_f(runs, xi)
    assert np.all(d_f > 0.0), f"F(ξ) − F(0) per mode: {d_f}"


def test_gb_signal_is_even_and_quadratic_in_xi(
    runs: dict[tuple[float, float], PipelineResult],
) -> None:
    d1, dm, d2 = (float(np.mean(_d_f(runs, x))) for x in (XI, -XI, 2 * XI))
    # abs=0 throughout: pytest.approx otherwise adds abs=1e-12, far above the signal.
    assert dm == pytest.approx(d1, rel=1e-2, abs=0)        # |β_GB|² is even in ξ
    assert d2 == pytest.approx(4.0 * d1, rel=1e-2, abs=0)  # and quadratic


def test_gb_signal_matches_first_order_perturbation_theory(
    runs: dict[tuple[float, float], PipelineResult], first_order_beta2,  # type: ignore[no-untyped-def]
) -> None:
    r = runs[(XI, THETA)]
    k = np.asarray(r.modes.k)  # type: ignore[attr-defined]
    tau1 = M3_TAU_END["fast"]
    prof = coupling_profile(KK, _cfg(XI, THETA).couplings, tau_start=M3_TAU_START)
    born_gb = first_order_beta2(prof, k, M3_TAU_START, tau1, +1, cs=False)
    d_f = _d_f(runs, XI)
    np.testing.assert_allclose(d_f, born_gb, rtol=3e-2)
    assert float(np.mean(d_f)) == pytest.approx(float(np.mean(born_gb)), rel=1e-2, abs=0)
    # The full per-helicity first-order |β_λ|² (GB and CS together) matches too.
    for lam, beta in ((+1, r.modes.beta_plus), (-1, r.modes.beta_minus)):  # type: ignore[attr-defined]
        born = first_order_beta2(prof, k, M3_TAU_START, tau1, lam)
        np.testing.assert_allclose(np.abs(beta) ** 2, born, rtol=3e-2)
