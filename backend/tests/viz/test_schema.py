"""Per-domain frame schema round-trips."""

from __future__ import annotations

import pytest

from cosmic_forge_viz import (
    AmoFrame,
    ChemistryFrame,
    CondmatFrame,
    CosmologyFrame,
    HepFrame,
    NuclearFrame,
    VisualizationManifest,
    frame_for_domain,
)
from cosmic_forge_viz.fixtures import synthesize_frames

DOMAINS = ("cosmology", "chemistry", "condmat", "hep", "nuclear", "amo")


@pytest.mark.parametrize("domain", DOMAINS)
def test_frame_roundtrip(domain: str) -> None:
    frames = synthesize_frames(domain, total_frames=4, seed=42)
    cls = frame_for_domain(domain)
    for f in frames:
        assert isinstance(f, cls)
        clone = cls.model_validate(f.model_dump())
        assert clone == f


def test_frame_for_domain_rejects_unknown() -> None:
    with pytest.raises(KeyError):
        frame_for_domain("phantom")


def test_manifest_roundtrip() -> None:
    m = VisualizationManifest(
        run_id="r1",
        domain="cosmology",
        frame_count=10,
        formula_variant="F3",
        bake_uri=None,
        metadata={"phases": ["inflation"]},
    )
    again = VisualizationManifest.model_validate_json(m.model_dump_json())
    assert again == m


def test_frame_classes_match_discriminator() -> None:
    assert CosmologyFrame(tau=0.0, phase="inflation").domain == "cosmology"
    assert ChemistryFrame(tau=0.0, phase="warmup").domain == "chemistry"
    assert CondmatFrame(tau=0.0, phase="thermalize").domain == "condmat"
    assert HepFrame(tau=0.0, phase="vacuum").domain == "hep"
    assert NuclearFrame(tau=0.0, phase="ground").domain == "nuclear"
    assert AmoFrame(tau=0.0, phase="load").domain == "amo"
