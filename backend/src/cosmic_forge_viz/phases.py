"""Phase-tag helpers.

Each domain has an ordered phase progression; frames are tagged with
the phase their position falls in. The cosmology progression matches
`Phase` in src/types/visualizer.ts.
"""

from __future__ import annotations

from collections.abc import Sequence

_PROGRESSION: dict[str, Sequence[str]] = {
    "cosmology": ("inflation", "gb_window", "reheating", "radiation", "sphaleron"),
    "chemistry": ("warmup", "scf", "post_scf"),
    "condmat": ("thermalize", "quench", "equilibrium"),
    "hep": ("vacuum", "string_break", "equilibrium"),
    "nuclear": ("ground", "decay"),
    "amo": ("load", "rydberg", "measure"),
    "gravity": ("ground", "quench", "thermalize", "measure"),
    "statmech": ("warmup", "equilibrium", "measure"),
}

_FALLBACK = ("equilibrium",)


def progression(domain: str) -> tuple[str, ...]:
    """Ordered phase progression for ``domain`` (empty for unknown domains)."""
    return tuple(_PROGRESSION.get(domain, ()))


def phases_for_domain(domain: str) -> Sequence[str]:
    """Like :func:`progression` but never empty."""
    return _PROGRESSION.get(domain, _FALLBACK)


def phase_for(domain: str, frame_index: int, total_frames: int) -> str:
    """Phase tag for ``frame_index`` out of ``total_frames`` (even split)."""
    if total_frames <= 0:
        raise ValueError("total_frames must be positive")
    if frame_index < 0 or frame_index >= total_frames:
        raise IndexError(
            f"frame_index {frame_index} out of range for total_frames={total_frames}"
        )
    phases = _PROGRESSION.get(domain)
    if not phases:
        return _FALLBACK[0]
    n = len(phases)
    return phases[min(n - 1, (frame_index * n) // total_frames)]


def phase_for_tau(domain: str, tau: float, tau_max: float) -> str:
    """Phase for a fractional position ``tau`` in ``[0, tau_max]``."""
    phases = phases_for_domain(domain)
    if tau_max <= 0 or len(phases) <= 1:
        return phases[0]
    fraction = max(0.0, min(1.0, tau / tau_max))
    return phases[min(len(phases) - 1, int(fraction * len(phases)))]
