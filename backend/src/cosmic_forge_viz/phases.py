"""Phase-tag helpers.

Maps a (domain, frame_index, total_frames) triplet to the right
`phase` tag for the frame's `BaseFrame.phase` field. The bake step
calls `phase_for(...)` for synthetic / fixture data; live runs pass
their own phase tag through and skip this.
"""

from __future__ import annotations

from typing import Sequence

# Per-domain ordered phase progression. The bake step distributes
# `total_frames` across the listed phases evenly; the last phase
# absorbs any rounding remainder.
_PROGRESSION: dict[str, Sequence[str]] = {
    "cosmology": (
        "inflation",
        "gb_window",
        "reheating",
        "radiation",
        "sphaleron",
    ),
    "chemistry": ("warmup", "scf", "post_scf"),
    "condmat": ("thermalize", "quench", "equilibrium"),
    "hep": ("vacuum", "string_break", "equilibrium"),
    "nuclear": ("ground", "decay"),
    "amo": ("load", "rydberg", "measure"),
}


def progression(domain: str) -> tuple[str, ...]:
    return tuple(_PROGRESSION.get(domain, ()))


def phase_for(domain: str, frame_index: int, total_frames: int) -> str:
    """Return the phase tag for `frame_index` out of `total_frames`."""
    if total_frames <= 0:
        raise ValueError("total_frames must be positive")
    if frame_index < 0 or frame_index >= total_frames:
        raise IndexError(
            f"frame_index {frame_index} out of range for total_frames={total_frames}"
        )
    progression = _PROGRESSION.get(domain)
    if not progression:
        return "equilibrium"
    n = len(progression)
    bucket = min(n - 1, (frame_index * n) // total_frames)
    return progression[bucket]
