"""Shared helpers for the M3/M7 unit tests."""

from __future__ import annotations

from typing import Protocol

import numpy as np
import pytest
from numpy.typing import NDArray

from ucgle_f1.m7_infer.couplings import CouplingProfile


class FirstOrderBeta2(Protocol):
    def __call__(
        self, profile: CouplingProfile, k: NDArray[np.float64], tau0: float, tau1: float,
        helicity: int, *, gb: bool = True, cs: bool = True,
    ) -> NDArray[np.float64]: ...


def _first_order_beta2(
    profile: CouplingProfile, k: NDArray[np.float64], tau0: float, tau1: float,
    helicity: int, *, gb: bool = True, cs: bool = True,
) -> NDArray[np.float64]:
    """First-order (Born) |β_k|² for h″ + [k² + δω²(τ)] h = 0 from a free wave at τ0.

    Variation of parameters in M3's basis h = (α e^{-ikτ} + β e^{ikτ})/√(2k)
    gives β(τ1) = (i/2k) ∫_{τ0}^{τ1} δω²(τ) e^{-2ikτ} dτ · α + O(δω²)², with
    δω²_λ = k² C + λ A k + B (``m7_infer/couplings.py``). ``gb`` and ``cs``
    switch the parity-even (B, C) and parity-odd (A) parts on or off. The
    integral is a trapezoid on 2·10⁵ points of the profile's splines, which
    resolves both e^{-2ikτ} (k ≤ 10 on [−5, −1]) and the splines' knots.
    """
    t = np.linspace(tau0, tau1, 200_001)
    a_part = profile._A(t) if cs else np.zeros_like(t)
    b_part = profile._B(t) if gb else np.zeros_like(t)
    c_part = profile._C(t) if gb else np.zeros_like(t)
    out = np.empty_like(k)
    for i, kk in enumerate(k):
        dw2 = kk * kk * c_part + helicity * a_part * kk + b_part
        out[i] = abs(np.trapezoid(dw2 * np.exp(-2j * kk * t), t) / (2.0 * kk)) ** 2
    return out


@pytest.fixture(scope="session")
def first_order_beta2() -> FirstOrderBeta2:
    return _first_order_beta2
