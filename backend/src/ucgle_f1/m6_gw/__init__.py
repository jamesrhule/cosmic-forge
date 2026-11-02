"""M6 — Stochastic GW spectrum + interferometry overlays.

Today :func:`compute_sgwb` always returns a placeholder: it lifts the M3
mode spectrum into an Ω_gw(f) curve with chirality fraction χ(f), using a
single placeholder k→f conversion (``sgwb._K_TO_HZ``) and a rough spectral
slope. Its shape is good enough for fixtures and UI testing; its overall
normalisation is not physical, and nothing in the validation report flags
it yet.

Planned integrations (PLAN P1-06), none of them wired today:
  cosmoGW           (Ω_gw(f) + LISA/Taiji overlap)
  PTAfast           (PTA array overlap reductions)
  GWBird            (detector network sensitivity)
  CAMB              (CMB tensor amplitudes; classy optional)

Every path emits that placeholder: f_Hz is a fixed 1e-19·k conversion
and Ω_gw is unnormalised. ``SGWBResult`` carries
``f_Hz_is_placeholder=True`` and a ``note`` (see ``sgwb.py``).

Nothing in this package imports PTAfast, GWBird, CAMB or classy. The
``gw`` extra is empty and no extra installs classy (see
``backend/pyproject.toml`` and docs/qcompass/optional-backends.md).
``sgwb`` soft-imports ``CosmoGW``: a copy you install yourself is imported
into your own process, and that branch still returns the placeholder.
"""

from __future__ import annotations

from .sgwb import SGWBResult, compute_sgwb

__all__ = ["SGWBResult", "compute_sgwb"]
