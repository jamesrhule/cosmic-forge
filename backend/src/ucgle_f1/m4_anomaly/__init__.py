"""M4 — Gravitational chiral anomaly → ΔN_L.

Written from scratch (no upstream module reused). P1-04: canonical tensor
modes on M2's background (``physical.py``), ⟨RR̃⟩ as the total derivative of
V3 (Kamada et al., arXiv:2007.08029) Eq. 2.28 with V3's adiabatic
subtraction to fourth adiabatic order (``adiabatic.py``, Sec. 3.2), the
lepton number of V3 Eq. 2.29, and the V4 cross-check (arXiv:2412.09490,
Eq. 7, boundary form; Eqs. 9–15 tested on V4's own mode model).

The output ΔN_L ≡ Y_L = n_L/s at T_reh feeds M5 as the initial B−L asymmetry.
"""

from __future__ import annotations

from .anomaly import (
    AnomalyInputs,
    AnomalyResult,
    delta_N_L,
    rr_dual_density,
)

__all__ = [
    "AnomalyInputs",
    "AnomalyResult",
    "delta_N_L",
    "rr_dual_density",
]
