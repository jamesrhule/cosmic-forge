"""Frame-level decimation for low-bandwidth clients.

The visualizer's WS / SSE clients can request a max frames-per-second
or a maximum frame count. `downsample_frames` returns evenly-spaced
indices so the bake or server side can ship a sparser timeline
without changing the wire schema.
"""

from __future__ import annotations

from typing import Iterable, Sequence, TypeVar

T = TypeVar("T")


def downsample_indices(total: int, target: int) -> list[int]:
    """Return up to `target` indices evenly spaced in `[0, total)`.

    Edge cases:
      - `target <= 0`  → empty
      - `target >= total` → every index
      - otherwise: monotonic, includes 0 and `total - 1` whenever
        `target >= 2`.
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
    """Return at most `target` frames, evenly spaced through `frames`."""
    return [frames[i] for i in downsample_indices(len(frames), target)]


def fps_to_target(total_frames: int, fps_cap: float, run_seconds: float) -> int:
    """Translate an FPS cap into a target frame count for a run.

    Used by the server when the client requests a max FPS rather than
    a target count. Returns 1 when the math collapses.
    """
    if fps_cap <= 0 or run_seconds <= 0:
        return total_frames
    target = max(1, int(fps_cap * run_seconds))
    return min(total_frames, target)


__all__ = ["downsample_frames", "downsample_indices", "fps_to_target"]
