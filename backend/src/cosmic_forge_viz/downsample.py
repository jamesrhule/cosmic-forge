"""Frame-level decimation for low-bandwidth clients.

``downsample_indices`` is the single evenly-spaced selector; the other
helpers are thin conveniences over it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TypeVar

T = TypeVar("T")


def downsample_indices(total: int, target: int) -> list[int]:
    """Up to ``target`` indices evenly spaced in ``[0, total)``.

    ``target <= 0`` → empty; ``target >= total`` → every index;
    otherwise monotonic, unique, and includes ``0`` and ``total - 1``
    whenever ``target >= 2``.
    """
    if total <= 0 or target <= 0:
        return []
    if target >= total:
        return list(range(total))
    if target == 1:
        return [0]
    step = (total - 1) / (target - 1)
    out: list[int] = []
    last = -1
    for i in range(target):
        idx = int(round(i * step))
        if idx <= last:
            idx = last + 1
        if idx >= total:
            idx = total - 1
        out.append(idx)
        last = idx
    return out


def downsample_frames(frames: Sequence[T], target: int) -> list[T]:
    """At most ``target`` frames, evenly spaced, first and last kept."""
    return [frames[i] for i in downsample_indices(len(frames), target)]


def target_count_decimate(frames: Sequence[T], target: int) -> list[T]:
    """Alias kept for the M8 qcompass routes; see :func:`downsample_frames`."""
    return downsample_frames(frames, target)


def stride_decimate(frames: Sequence[T], stride: int) -> list[T]:
    """``frames[::stride]``; a stride of 0 or 1 returns the input."""
    if stride <= 1:
        return list(frames)
    return list(frames[::stride])


def adaptive_decimate(
    frames: Iterable[T],
    *,
    target_bytes_per_frame: int = 2048,
    target_total_kb: int = 256,
) -> list[T]:
    """Decimate to roughly ``target_total_kb`` of payload."""
    materialised = list(frames)
    if not materialised:
        return []
    keep = max(1, (target_total_kb * 1024) // max(1, target_bytes_per_frame))
    return downsample_frames(materialised, keep)


def fps_to_target(total_frames: int, fps_cap: float, run_seconds: float) -> int:
    """Translate an FPS cap into a target frame count."""
    if fps_cap <= 0 or run_seconds <= 0:
        return total_frames
    return min(total_frames, max(1, int(fps_cap * run_seconds)))


__all__ = [
    "adaptive_decimate",
    "downsample_frames",
    "downsample_indices",
    "fps_to_target",
    "stride_decimate",
    "target_count_decimate",
]
