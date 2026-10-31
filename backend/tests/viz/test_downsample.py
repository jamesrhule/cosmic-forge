"""Downsample helpers."""

from __future__ import annotations

from cosmic_forge_viz.downsample import (
    downsample_frames,
    downsample_indices,
    fps_to_target,
)


def test_downsample_indices_basic() -> None:
    idx = downsample_indices(60, 10)
    assert len(idx) == 10
    assert idx[0] == 0
    assert idx[-1] == 59
    assert idx == sorted(idx) == list(dict.fromkeys(idx))  # monotonic + unique


def test_downsample_indices_target_geq_total() -> None:
    assert downsample_indices(5, 10) == [0, 1, 2, 3, 4]


def test_downsample_indices_zero_or_negative() -> None:
    assert downsample_indices(10, 0) == []
    assert downsample_indices(0, 5) == []
    assert downsample_indices(10, -1) == []


def test_downsample_indices_target_one() -> None:
    assert downsample_indices(60, 1) == [0]


def test_downsample_frames() -> None:
    seq = list(range(20))
    out = downsample_frames(seq, 5)
    assert out[0] == 0
    assert out[-1] == 19
    assert len(out) == 5


def test_fps_to_target() -> None:
    assert fps_to_target(60, 10.0, 6.0) == 60
    assert fps_to_target(60, 5.0, 6.0) == 30
    assert fps_to_target(60, 0.0, 6.0) == 60
    assert fps_to_target(60, 10.0, 0.0) == 60
    assert fps_to_target(0, 10.0, 6.0) == 0
