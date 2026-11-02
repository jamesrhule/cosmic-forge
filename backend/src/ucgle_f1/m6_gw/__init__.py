"""M6 — Stochastic GW spectrum + interferometry overlays.

Reuses:
  cosmoGW           (Ω_gw(f) + LISA/Taiji overlap)
  PTAfast           (PTA array overlap reductions)
  GWBird            (detector network sensitivity)
  CAMB / classy     (CMB tensor amplitudes)

The :func:`compute_sgwb` entry point lifts the M3 mode spectrum into
an Ω_gw(f) curve with chirality fraction χ(f). Today every path (with
or without the optional ``gw`` extra) emits a placeholder: f_Hz is a
fixed 1e-19·k conversion and Ω_gw is unnormalised. ``SGWBResult``
carries ``f_Hz_is_placeholder=True`` and a ``note`` (see ``sgwb.py``);
no validation report flags it.
"""

from __future__ import annotations

from .sgwb import SGWBResult, compute_sgwb

__all__ = ["SGWBResult", "compute_sgwb"]
