"""M5 — Boltzmann / sphaleron transport via ULYSSES.

Reuses ULYSSES v2 (github.com/earlyuniverse/ulysses, MIT;
arXiv:2007.09150, 2301.05722). We never reimplement the flavor
density matrix or sphaleron decoupling — we only convert the M4
output ΔN_L(T_reh) into initial conditions for the ULYSSES
``ULSBase`` subclass defined here.
"""

from __future__ import annotations

from .ulysses_bridge import AsymmetryInputs, UCGLE_F1, eta_B_from_delta_N_L

__all__ = ["AsymmetryInputs", "UCGLE_F1", "eta_B_from_delta_N_L"]
