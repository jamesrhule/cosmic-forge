"""Schema + builder tests for cosmic_forge_viz (PROMPT 7 v2 §PART B)."""

from __future__ import annotations

import pytest

from cosmic_forge_viz import (
    AmoFrame,
    ChemistryFrame,
    CondmatFrame,
    CosmologyFrame,
    HepFrame,
    NuclearFrame,
    VisualizationTimeline,
    frame_class_for_domain,
)
from cosmic_forge_viz.fixtures import build_synthetic_timeline
from cosmic_forge_viz.formulas import (
    active_formulas_for_couplings,
    formulas_at_phase,
)
from cosmic_forge_viz.phases import phase_for_tau, phases_for_domain


def test_frame_class_for_domain_resolves_all_six() -> None:
    assert frame_class_for_domain("cosmology") is CosmologyFrame
    assert frame_class_for_domain("chemistry") is ChemistryFrame
    assert frame_class_for_domain("condmat") is CondmatFrame
    assert frame_class_for_domain("hep") is HepFrame
    assert frame_class_for_domain("nuclear") is NuclearFrame
    assert frame_class_for_domain("amo") is AmoFrame


def test_frame_class_for_domain_unknown_raises() -> None:
    with pytest.raises(KeyError, match="Unknown domain"):
        frame_class_for_domain("gravity")


def test_cosmology_synthetic_timeline_round_trips() -> None:
    timeline = build_synthetic_timeline(
        "cosmology", "kawai-kim-natural",
        n_frames=8, tau_max=8.0,
        couplings={"alpha_GB": 1.0, "beta_CS": 1.5, "nieh_yan": 0.0},
    )
    assert timeline.run_id == "kawai-kim-natural"
    assert timeline.domain == "cosmology"
    assert len(timeline.frames) == 8

    # Round-trip via the discriminated union.
    parsed = timeline.parsed_frames()
    assert all(isinstance(f, CosmologyFrame) for f in parsed)
    # active_terms populated from the F-rules.
    assert any(f.active_terms for f in parsed)


def test_chemistry_synthetic_timeline_carries_orbital_block() -> None:
    timeline = build_synthetic_timeline("chemistry", "h2-sto3g", n_frames=4)
    parsed = timeline.parsed_frames()
    assert all(isinstance(f, ChemistryFrame) for f in parsed)
    assert all(len(f.orbitals) == 8 for f in parsed)


def test_hep_synthetic_timeline_carries_particle_obs() -> None:
    timeline = build_synthetic_timeline(
        "hep", "schwinger-1plus1d", n_frames=4,
    )
    parsed = timeline.parsed_frames()
    assert all(isinstance(f, HepFrame) for f in parsed)
    for frame in parsed:
        po = frame.particle_obs
        assert "chiral_condensate" in po
        assert "string_tension" in po
        assert "anomaly_density" in po
        assert po["chiral_condensate"].unit == "dimensionless"


def test_nuclear_synthetic_timeline_tags_model_domain() -> None:
    timeline = build_synthetic_timeline(
        "nuclear", "0nbb-1+1d-toy", n_frames=4, model_domain="1+1D_toy",
    )
    parsed = timeline.parsed_frames()
    assert all(f.model_domain == "1+1D_toy" for f in parsed)

    timeline_eff = build_synthetic_timeline(
        "nuclear", "heavy-neutrino-mixing", n_frames=4,
        model_domain="effective_hamiltonian",
    )
    parsed_eff = timeline_eff.parsed_frames()
    assert all(f.model_domain == "effective_hamiltonian" for f in parsed_eff)


def test_active_formulas_classifier_no_couplings_returns_empty() -> None:
    assert active_formulas_for_couplings(None) == []
    assert active_formulas_for_couplings({}) == []


def test_active_formulas_classifier_full_stack() -> None:
    out = active_formulas_for_couplings({
        "alpha_GB": 1.0, "beta_CS": 2.0, "nieh_yan": 0.5,
    })
    # F1 (a_gb) + F2 (b_cs) + F3 (both) + F4 (NY) + F5 (a_gb & |b_cs|>1) +
    # F6 (all three) + F7 (a_gb*b_cs > 1e-3).
    for f in ("F1", "F2", "F3", "F4", "F5", "F6", "F7"):
        assert f in out


def test_formulas_at_phase_inflation_drops_anomaly_terms() -> None:
    couplings = {"alpha_GB": 1.0, "beta_CS": 0.5, "nieh_yan": 0.0}
    out = formulas_at_phase("inflation", couplings)
    # Inflation suppresses F2 (Chern-Simons drive) — no F2 even though
    # b_cs != 0.
    assert "F2" not in out
    # F1 still active.
    assert "F1" in out


def test_phase_for_tau_progresses_with_fraction() -> None:
    phases = phases_for_domain("cosmology")
    assert phase_for_tau("cosmology", 0.0, 100.0) == phases[0]
    assert phase_for_tau("cosmology", 100.0, 100.0) == phases[-1]
    # Halfway through hits one of the middle phases.
    mid = phase_for_tau("cosmology", 50.0, 100.0)
    assert mid in phases


def test_visualization_timeline_serialises_round_trip() -> None:
    timeline = build_synthetic_timeline("amo", "rydberg-mis", n_frames=3)
    blob = timeline.model_dump_json()
    restored = VisualizationTimeline.model_validate_json(blob)
    assert restored.run_id == timeline.run_id
    assert restored.frames == timeline.frames
