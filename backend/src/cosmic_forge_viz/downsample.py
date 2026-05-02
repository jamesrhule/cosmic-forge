"""Frame decimation for the visualisation timeline.

Bakery output is dense (one frame per integration step); the WS /
SSE channel streams a downsampled view so the frontend keeps up
on a 60 Hz draw loop. Two modes:

  - ``stride`` — keep every Nth frame.
  - ``target_count`` — pick a stride so the output ≈ N frames.
"""

from __future__ import annotations

from typing import Iterable, Sequence


def stride_decimate(frames: Sequence[dict], stride: int) -> list[dict]:
    """Return ``frames[::stride]``; a stride of 0 / 1 returns the input."""
    if stride <= 1:
        return list(frames)
    return list(frames[::stride])


def target_count_decimate(
    frames: Sequence[dict], target: int,
) -> list[dict]:
    """Return ≈ ``target`` frames evenly sampled from the input."""
    n = len(frames)
    if target <= 0 or n == 0:
        return []
    if target >= n:
        return list(frames)
    # Use ceiling so we always overshoot rather than under-shoot.
    stride = max(1, n // target)
    out = list(frames[::stride])
    # Trim to at most ``target`` frames; first + last always preserved.
    if len(out) > target:
        out = out[:target]
    if frames and out and out[-1] is not frames[-1]:
        out.append(frames[-1])
    return out


def adaptive_decimate(
    frames: Iterable[dict],
    *,
    target_bytes_per_frame: int = 2048,
    target_total_kb: int = 256,
) -> list[dict]:
    """Decimate based on serialised-size estimate.

    Picks a stride that targets ``target_total_kb`` of payload
    assuming ``target_bytes_per_frame`` per kept frame. Useful for
    one-shot REST snapshots.
    """
    materialised = list(frames)
    n = len(materialised)
    if n == 0:
        return []
    keep = max(1, (target_total_kb * 1024) // max(1, target_bytes_per_frame))
    return target_count_decimate(materialised, keep)
