"""Top-level smoke tests for qfull-statmech."""

from __future__ import annotations

import pytest

from qfull_stat import StatmechSimulation, compute_reference, load_instance


def test_load_and_compute_reference_for_qae() -> None:
    out = compute_reference(load_instance("qae_bell"))
    assert out["energy"] >= 0.0
    assert out["energy"] <= 1.0


def test_satisfies_simulation_protocol() -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    assert isinstance(StatmechSimulation(), qcompass_core.Simulation)
