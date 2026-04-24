"""Stochastic GW spectrum and chirality fraction."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ..m3_modes import ChiralModeResult

# h × a/a_* → f today: f = k × (T_reh/T_0) / (2π) × ..., grossly
# collapsed to a single reference conversion since M3 returns a k-grid
# in M_Pl units.
_K_TO_HZ = 1.0e-19  # placeholder conversion; replaced by cosmoGW when available


@dataclass
class SGWBResult:
    f_Hz: NDArray[np.float64]
    Omega_gw: NDArray[np.float64]
    chirality: NDArray[np.float64]


def compute_sgwb(modes: ChiralModeResult) -> SGWBResult:
    """Ω_gw(f) + χ(f) from the chiral mode result."""
    try:
        import CosmoGW  # type: ignore[import-untyped]  # noqa: F401

        # Prefer the CosmoGW pipeline when available.
        return _cosmogw_path(modes)
    except ImportError:
        return _placeholder_path(modes)


def _placeholder_path(modes: ChiralModeResult) -> SGWBResult:
    k = modes.k
    f = _K_TO_HZ * k
    Op = np.abs(modes.beta_plus) ** 2
    Om = np.abs(modes.beta_minus) ** 2
    tot = Op + Om
    Omega = tot * (k / k[0]) ** 3  # rough spectral slope
    chi = np.where(tot > 0.0, (Op - Om) / np.maximum(tot, 1e-300), 0.0)
    return SGWBResult(f_Hz=f, Omega_gw=Omega, chirality=chi)


def _cosmogw_path(modes: ChiralModeResult) -> SGWBResult:
    # Full CosmoGW pipeline would accept the β_k array + background
    # and return Ω_gw(f). We keep the adapter minimal here.
    import CosmoGW  # type: ignore[import-untyped]

    _ = CosmoGW  # placeholder
    # Fallback to placeholder until the concrete CosmoGW API is pinned.
    return _placeholder_path(modes)
