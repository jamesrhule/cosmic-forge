"""Synthetic-frame generators are deterministic and respect phases."""

from __future__ import annotations

import pytest

from cosmic_forge_viz.fixtures import synthesize_frames, synthesize_manifest
from cosmic_forge_viz.phases import progression

DOMAINS = ("cosmology", "chemistry", "condmat", "hep", "nuclear", "amo")


@pytest.mark.parametrize("domain", DOMAINS)
def test_synthesize_frames_is_deterministic(domain: str) -> None:
    a = synthesize_frames(domain, total_frames=20, seed=7)
    b = synthesize_frames(domain, total_frames=20, seed=7)
    assert [f.model_dump() for f in a] == [f.model_dump() for f in b]


@pytest.mark.parametrize("domain", DOMAINS)
def test_phases_cover_progression(domain: str) -> None:
    frames = synthesize_frames(domain, total_frames=24, seed=0)
    seen = {f.phase for f in frames}
    expected = set(progression(domain))
    if expected:
        # Every phase in the progression should appear at least once
        # for total_frames=24.
        assert expected.issubset(seen), f"missing phases for {domain}: {expected - seen}"


def test_manifest_includes_progression() -> None:
    m = synthesize_manifest(domain="hep", run_id="hep-test", total_frames=30)
    assert m.metadata["phases"] == list(progression("hep"))
    assert m.frame_count == 30
    assert m.metadata["synthetic"] is True


def test_synthesize_unknown_domain() -> None:
    with pytest.raises(ValueError):
        synthesize_frames("phantom", total_frames=4)
