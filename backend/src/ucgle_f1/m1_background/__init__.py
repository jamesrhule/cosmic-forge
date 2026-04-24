"""M1 — Friedmann background cosmology.

Reheating → radiation-dominated transition, continuous H(τ),
ρ_φ(τ), ρ_r(τ). Integrator: scipy.integrate.solve_ivp with LSODA
(rtol=1e-10, atol=1e-12). Radau is used automatically when the
solver reports stiffness.

The module produces a :class:`Background` object holding interpolants
that M2–M6 consume. CosmoGW helpers are used when available (via the
``cosmo`` optional extra); otherwise the pure-scipy path runs.
"""

from __future__ import annotations

from .background import (
    Background,
    BackgroundInputs,
    solve_background,
)

__all__ = ["Background", "BackgroundInputs", "solve_background"]
