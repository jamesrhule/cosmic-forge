"""M3 — Chiral tensor modes h_± + F_GB transient amplification.

Solves (per mode k, per helicity σ = ±1):

    h''_σ(τ, k) + [k² + A_σ(τ) k + B_σ(τ)] h_σ(τ, k) = 0

with ``A_σ`` from the Chern-Simons coupling and ``B_σ`` from the
Gauss-Bonnet coupling. We track Bogoliubov coefficients (α_k, β_k)
at each sign change of the effective frequency squared, and escalate
to mpmath (dps=50) if unitarity drift ``||α|² − |β|² − 1|`` exceeds
the precision budget.

Preferred integrator: diffrax.Kvaerno5 + PIDController.
CPU fallback: scipy.integrate.solve_ivp with LSODA.
"""

from __future__ import annotations

from .chiral import (
    ChiralModeResult,
    ChiralSpectrumInputs,
    F_GB,
    solve_chiral_modes,
)

__all__ = [
    "ChiralModeResult",
    "ChiralSpectrumInputs",
    "F_GB",
    "solve_chiral_modes",
]
