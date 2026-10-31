"""Phase progression rules (PROMPT 7 v2 §PART B).

Each domain emits a sequence of frames; the phase string is the
narrative segment the frame belongs to. The frontend uses the
phase to colour-code the timeline scrubber.

Cosmology phases align with UCGLE-F1's M-module flow:
  inflation → reheating → leptogenesis → freeze-out

Other domains use their own canonical phase labels.
"""

from __future__ import annotations

from typing import Sequence


_DOMAIN_PHASES: dict[str, Sequence[str]] = {
    "cosmology": ("inflation", "reheating", "leptogenesis", "freeze-out"),
    "chemistry": ("init", "iter", "converged"),
    "condmat": ("ground_state", "quench", "thermalisation"),
    "hep": ("vacuum", "evolution", "measurement"),
    "nuclear": ("init", "ed", "measurement"),
    "amo": ("loading", "drive", "measurement"),
}


def phases_for_domain(domain: str) -> Sequence[str]:
    return _DOMAIN_PHASES.get(domain, ("init", "running", "complete"))


def phase_for_tau(domain: str, tau: float, tau_max: float) -> str:
    """Pick the phase for a given fractional tau in [0, tau_max].

    Splits the [0, tau_max] interval evenly across the domain's
    phase list. ``tau_max`` of 0 / negative returns the first phase.
    """
    phases = phases_for_domain(domain)
    if tau_max <= 0 or len(phases) <= 1:
        return phases[0]
    fraction = max(0.0, min(1.0, tau / tau_max))
    idx = min(len(phases) - 1, int(fraction * len(phases)))
    return phases[idx]
