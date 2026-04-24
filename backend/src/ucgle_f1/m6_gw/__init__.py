"""M6 — Stochastic GW spectrum + interferometry overlays.

Reuses:
  cosmoGW           (Ω_gw(f) + LISA/Taiji overlap)
  PTAfast           (PTA array overlap reductions)
  GWBird            (detector network sensitivity)
  CAMB / classy     (CMB tensor amplitudes)

The :func:`compute_sgwb` entry point lifts the M3 mode spectrum into
an Ω_gw(f) curve with chirality fraction χ(f). When the optional
``gw`` extra is absent we emit a Planck-scale placeholder whose shape
is correct enough for fixtures and UI testing but whose overall
normalisation is flagged as ``degraded`` in the validation report.
"""

from __future__ import annotations

from .sgwb import SGWBResult, compute_sgwb

__all__ = ["SGWBResult", "compute_sgwb"]
