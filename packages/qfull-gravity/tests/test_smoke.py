"""Top-level smoke tests for qfull-gravity."""

from __future__ import annotations

import pytest

from qfull_grav import (
    GravityProblem,
    GravitySimulation,
    compute_reference,
    load_instance,
)


def test_load_instance_and_compute_reference_round_trip() -> None:
    problem = load_instance("syk_n8")
    out = compute_reference(problem)
    assert out["energy"] < 0.0  # SYK ground state is negative
    assert out["hash"]


def test_satisfies_simulation_protocol() -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    assert isinstance(GravitySimulation(), qcompass_core.Simulation)


def test_unknown_instance_raises() -> None:
    with pytest.raises(FileNotFoundError, match="Unknown instance"):
        load_instance("does-not-exist")
