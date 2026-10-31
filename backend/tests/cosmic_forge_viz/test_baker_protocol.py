"""Baker, downsample, and protocol tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cosmic_forge_viz.baker import bake_from_provenance, bake_synthetic
from cosmic_forge_viz.downsample import (
    adaptive_decimate,
    stride_decimate,
    target_count_decimate,
)
from cosmic_forge_viz.protocol import decode, encode, envelope, sse_format


# ── baker ──────────────────────────────────────────────────────────


def test_bake_synthetic_writes_json_snapshot(tmp_path: Path) -> None:
    info = bake_synthetic(
        "cosmology", "kawai-kim-natural",
        out_dir=tmp_path, n_frames=10, tau_max=10.0,
        couplings={"alpha_GB": 1.0, "beta_CS": 1.5},
    )
    json_path = Path(info["json_path"])
    assert json_path.exists()
    raw = json.loads(json_path.read_text())
    assert raw["run_id"] == "kawai-kim-natural"
    assert raw["domain"] == "cosmology"
    assert len(raw["frames"]) == 10
    assert info["n_frames"] == 10


def test_bake_from_provenance_reads_couplings(tmp_path: Path) -> None:
    payload = {
        "manifest": {
            "problem": {
                "couplings": {"alpha_GB": 1.0, "beta_CS": 0.5},
            }
        },
        "model_domain": None,
    }
    info = bake_from_provenance(
        "cosmology", "starobinsky-standard", payload,
        out_dir=tmp_path, n_frames=4, tau_max=4.0,
    )
    assert info["domain"] == "cosmology"
    assert info["n_frames"] == 4
    raw = json.loads(Path(info["json_path"]).read_text())
    # First frame's active_terms reflect the couplings.
    assert raw["frames"][0]["active_terms"]


# ── downsample ─────────────────────────────────────────────────────


def test_stride_decimate_passthrough_when_stride_le_one() -> None:
    frames = [{"i": i} for i in range(10)]
    assert stride_decimate(frames, 0) == frames
    assert stride_decimate(frames, 1) == frames


def test_stride_decimate_keeps_every_nth() -> None:
    frames = [{"i": i} for i in range(10)]
    assert stride_decimate(frames, 3) == [{"i": 0}, {"i": 3}, {"i": 6}, {"i": 9}]


def test_target_count_decimate_returns_at_most_target() -> None:
    frames = [{"i": i} for i in range(100)]
    out = target_count_decimate(frames, 10)
    assert 1 <= len(out) <= 11   # last-frame pin can add 1


def test_target_count_decimate_zero_returns_empty() -> None:
    assert target_count_decimate([{"i": 0}], 0) == []


def test_adaptive_decimate_targets_kb_budget() -> None:
    frames = [{"i": i, "blob": "x" * 256} for i in range(200)]
    out = adaptive_decimate(
        frames, target_bytes_per_frame=512, target_total_kb=4,
    )
    # Budget = 4 KB / 512 B = 8 frames.
    assert len(out) <= 9


# ── protocol ───────────────────────────────────────────────────────


def test_envelope_shape() -> None:
    msg = envelope("frame", seq=3, tau=1.5, payload={"x": 1})
    assert msg == {"type": "frame", "seq": 3, "tau": 1.5, "payload": {"x": 1}}


def test_encode_decode_round_trip() -> None:
    msg = envelope("header", seq=0, payload={"run_id": "abc"})
    blob = encode(msg)
    assert isinstance(blob, bytes)
    out = decode(blob)
    assert out == msg


def test_sse_format_emits_data_block() -> None:
    msg = envelope("frame", seq=1, tau=0.5, payload={"k": "v"})
    text = sse_format(msg)
    assert text.startswith("data: ")
    assert text.endswith("\n\n")
    payload = text[len("data: "):-2]
    assert json.loads(payload) == msg
