"""M3 Bogoliubov extraction (PH-H2): free waves have β = 0 and |α|² − |β|² = 1.

With h = (α e^{-ikτ} + β e^{+ikτ})/√(2k) and h′ = −ik(α e^{-ikτ} − β e^{+ikτ})/√(2k),
α e^{-ikτ} = ½(√(2k) h + i√(2/k) h′) and β e^{+ikτ} = ½(√(2k) h − i√(2/k) h′).
The shipped extraction used i√(k/2) in place of i√(2/k), which gives a free
wave |β|² = ¼(1 − k/2)² and drift |k/2 − 1|: that artefact was the whole of
the default-path F_GB (its mean over logspace(−1, 1, 8) is 0.6727340798362142).
"""

from __future__ import annotations

import numpy as np
import pytest

from ucgle_f1.m3_modes import ChiralSpectrumInputs, solve_chiral_modes
from ucgle_f1.m3_modes.chiral import _bogoliubov

K_VALUES = [1.0e-3, 0.1, 0.5, 1.0, 3.7, 10.0, 1.0e3]
TAU_VALUES = [-5.0, -1.0, -0.37, -1.0e-3]


def _wave(alpha: complex, beta: complex, k: float, tau: float) -> tuple[complex, complex]:
    e = np.exp(-1j * k * tau)
    h = (alpha * e + beta * np.conj(e)) / np.sqrt(2.0 * k)
    hp = -1j * k * (alpha * e - beta * np.conj(e)) / np.sqrt(2.0 * k)
    return complex(h), complex(hp)


@pytest.mark.parametrize("tau", TAU_VALUES)
@pytest.mark.parametrize("k", K_VALUES)
def test_free_wave_has_no_beta(k: float, tau: float) -> None:
    h, hp = _wave(1.0, 0.0, k, tau)
    a, b = _bogoliubov(h, hp, k)
    artefact = 0.25 * (1 - k / 2) ** 2
    assert abs(b) ** 2 < 1e-12, f"|β|² = {abs(b) ** 2} (artefact ¼(1−k/2)² = {artefact})"
    assert abs(abs(a) ** 2 - abs(b) ** 2 - 1.0) < 1e-12


@pytest.mark.parametrize("tau", TAU_VALUES)
@pytest.mark.parametrize("k", K_VALUES)
def test_mixed_state_recovers_alpha_beta(k: float, tau: float) -> None:
    # |α|² − |β|² = 1 with a non-trivial β: cosh/sinh of r = 0.3, with phases.
    r = 0.3
    alpha = np.cosh(r) * np.exp(0.4j)
    beta = np.sinh(r) * np.exp(-1.1j)
    h, hp = _wave(alpha, beta, k, tau)
    a, b = _bogoliubov(h, hp, k)
    assert abs(a) == pytest.approx(abs(alpha), rel=1e-12, abs=0)
    assert abs(b) == pytest.approx(abs(beta), rel=1e-12, abs=0)
    # The returned values carry the e^{∓ikτ} phases (τ is not an argument).
    assert a == pytest.approx(alpha * np.exp(-1j * k * tau), rel=1e-12, abs=0)
    assert b == pytest.approx(beta * np.exp(1j * k * tau), rel=1e-12, abs=0)


def test_solver_with_no_coupling_stays_in_the_vacuum() -> None:
    # A = B = C = 0: ω² = k², so Bunch–Davies stays a free wave and M3 must
    # report β = 0 and unitarity drift at the integrator's tolerance.
    zero = lambda _t: np.zeros(2)  # noqa: E731
    k = np.logspace(-1.0, 1.0, 8)
    res = solve_chiral_modes(ChiralSpectrumInputs(
        tau_grid=np.linspace(-5.0, -1.0, 501), A=zero, B=zero, C=zero, k_modes=k,
        rtol=1e-12, atol=1e-14, unitarity_tol=1e-6, use_diffrax=False,
    ))
    assert float(np.max(res.F_GB_per_mode())) < 1e-12
    assert float(np.max(res.unitarity_drift)) < 1e-8
