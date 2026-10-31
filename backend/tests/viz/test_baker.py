"""Zarr 3 round-trip (skipped when zarr>=3 unavailable)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cosmic_forge_viz.baker import bake_timeline, read_manifest
from cosmic_forge_viz.fixtures import synthesize_frames, synthesize_manifest


def test_bake_chemistry(tmp_path: Path) -> None:
    pytest.importorskip("zarr", minversion="3.0")
    frames = synthesize_frames("chemistry", total_frames=12, seed=0)
    manifest = synthesize_manifest(domain="chemistry", run_id="chem-1", total_frames=12)
    uri = bake_timeline(frames, tmp_path / "store", manifest)

    # Manifest sidecar reads back equal.
    again = read_manifest(uri)
    assert again == manifest

    # Zarr group has the expected scalar arrays.
    import zarr  # type: ignore[import-not-found]

    group = zarr.open_group(uri, mode="r", zarr_format=3)
    assert group.attrs["domain"] == "chemistry"
    assert group.attrs["frame_count"] == 12
    assert "tau" in list(group.array_keys())
    assert group["tau"].shape == (12,)
    assert "phase" in list(group.array_keys())
    assert "payloads" in list(group.array_keys())


def test_bake_cosmology_marks_variant(tmp_path: Path) -> None:
    pytest.importorskip("zarr", minversion="3.0")
    frames = synthesize_frames("cosmology", total_frames=8, seed=0, formula_variant="F3")
    manifest = synthesize_manifest(
        domain="cosmology", run_id="ucgle-f3-test", total_frames=8, formula_variant="F3"
    )
    uri = bake_timeline(frames, tmp_path / "cosmo", manifest)
    assert read_manifest(uri).formula_variant == "F3"
