"""W1 API3 (round-3A PHYS3 verifier NIT): M3's coupling coefficients A, B, C
against the definitions in ``m7_infer/couplings.py``'s docstring, computed
independently of the pipeline's splines.

The Born helper (``conftest.py``) integrates the same ``CouplingProfile``
splines the pipeline integrates, so an error in how ``coupling_profile`` turns
M2's trajectory into A, B, C (an overall sign of the GB coefficients, the
e-fold form of the operator, the conformal-time axis) would pass every
signal test. This test rebuilds them from M2's φ(N), H(N) alone, with
derivatives taken numerically in cosmic time and conformal time (not the
analytic e-fold identities the code uses), and its own conformal-time
quadrature:

    ξ(φ) = ξ·φ, f(φ) = θ_grav·φ/f̂_a,   ˙ = d/dt = H d/dN,   ′ = d/dτ,
    a = (a_end H_end / H_end)·e^(N − N_end),   dτ = dN/(aH),  τ(N_end) = −1/(a_end H_end),
    C = −4 (ξ̈ − H ξ̇),   δ_T = −4 H ξ̇,   B = −(½ δ_T″ + ℋ δ_T′),
    g = f′/a²,   A₊ = ½ g″ + ℋ g′,   ℋ = aH.

Negating B and C (or A) in ``coupling_profile`` fails it.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import cumulative_simpson

from ucgle_f1.domain import RunConfig
from ucgle_f1.m1_background.background import M_PL_GEV
from ucgle_f1.m7_infer.couplings import A_END_H_END, coupling_profile

_FIXTURE = (
    Path(__file__).resolve().parents[3] / "public" / "fixtures" / "runs" / "kawai-kim-natural.json"
)
# Inside M3's window τ ∈ [−5, −1e-3], away from the grid's ends.
PROBE_TAU = (-4.0, -3.0, -2.0, -1.0, -0.3, -0.1)


def _benchmark() -> RunConfig:
    """The Kawai–Kim natural benchmark (Decision 11) with the fixture's couplings."""
    blob = json.loads(_FIXTURE.read_text())
    return RunConfig.model_validate({**blob["config"], "agent": None})


def _independent(cfg: RunConfig, trajectory: object, n_end: float) -> dict[str, np.ndarray]:
    tr = trajectory
    m = tr.N <= n_end  # type: ignore[attr-defined]
    N, phi, H = tr.N[m], tr.phi[m], tr.H[m]  # type: ignore[attr-defined]
    xi = float(cfg.couplings.xi)
    f_phi = float(cfg.couplings.theta_grav) / (float(cfg.couplings.f_a) / M_PL_GEV)

    a = (A_END_H_END / H[-1]) * np.exp(N - N[-1])
    aH = a * H
    # τ(N) = −1/(a_end H_end) − ∫_N^{N_end} dN′/(aH), by Simpson from the end
    # (in u = −N, so the small late-time tail is not a difference of large sums).
    tail = cumulative_simpson((1.0 / aH)[::-1], x=-N[::-1], initial=0.0)[::-1]
    tau = -1.0 / A_END_H_END - tail

    def d_dt(y: np.ndarray) -> np.ndarray:
        return H * np.gradient(y, N, edge_order=2)

    def d_dtau(y: np.ndarray) -> np.ndarray:
        return np.gradient(y, tau, edge_order=2)

    xi_t = d_dt(xi * phi)
    xi_tt = d_dt(xi_t)
    C = -4.0 * (xi_tt - H * xi_t)
    delta_T = -4.0 * H * xi_t
    B = -(0.5 * d_dtau(d_dtau(delta_T)) + aH * d_dtau(delta_T))
    g = d_dtau(f_phi * phi) / a**2
    A = 0.5 * d_dtau(d_dtau(g)) + aH * d_dtau(g)
    return {"tau": tau, "a": a, "A": A, "B": B, "C": C}


@pytest.fixture(scope="module")
def benchmark() -> tuple[RunConfig, object, dict[str, np.ndarray]]:
    cfg = _benchmark()
    prof = coupling_profile(cfg.potential, cfg.couplings)
    return cfg, prof, _independent(cfg, prof.trajectory, prof.N_end)


def test_the_benchmark_has_both_couplings_on() -> None:
    cfg = _benchmark()
    assert cfg.couplings.xi > 0 and cfg.couplings.theta_grav > 0
    assert (cfg.potential.kind, cfg.potential.params["f_a"]) == ("natural", 8.7)


@pytest.mark.parametrize("name", ["A", "B", "C"])
def test_coupling_coefficients_match_their_definitions(
    name: str, benchmark: tuple[RunConfig, object, dict[str, np.ndarray]],
) -> None:
    _, prof, ind = benchmark
    of_tau = {"A": prof.A_of_tau, "B": prof.B_of_tau, "C": prof.C_of_tau}[name]  # type: ignore[attr-defined]
    order = np.argsort(ind["tau"])
    for t in PROBE_TAU:
        expected = float(np.interp(t, ind["tau"][order], ind[name][order]))
        got = float(of_tau(t)[0])  # helicity + (A₋ = −A₊; B, C helicity-blind)
        assert expected != 0.0, (name, t)
        assert np.sign(got) == np.sign(expected), f"{name}(τ={t}): sign {got:+.6e} vs {expected:+.6e}"
        assert got == pytest.approx(expected, rel=1e-4, abs=0), (name, t, got, expected)


def test_scale_factor_on_the_conformal_time_axis_matches(
    benchmark: tuple[RunConfig, object, dict[str, np.ndarray]],
) -> None:
    # a(τ) puts the coefficients on M3's axis: the profile's (trapezoid τ,
    # spline in ln a) against the Simpson quadrature above.
    _, prof, ind = benchmark
    order = np.argsort(ind["tau"])
    for t in PROBE_TAU:
        expected = float(np.exp(np.interp(t, ind["tau"][order], np.log(ind["a"][order]))))
        assert prof.a_of_tau(t) == pytest.approx(expected, rel=1e-5, abs=0), t  # type: ignore[attr-defined]
