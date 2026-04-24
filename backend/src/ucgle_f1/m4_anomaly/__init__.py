"""M4 — Gravitational chiral anomaly → ΔN_L.

Written from scratch (no upstream module reused). Implements the
adiabatic / minimal-subtraction regularization of V3 (Kamada et al.,
arXiv:2007.08029) and cross-checks against V4 Eqs. 7–16
(arXiv:2412.09490).

The output ΔN_L at T_reh feeds M5 as the initial B−L asymmetry.
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
