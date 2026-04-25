"""Sim-protocol tests: registry lookup, manifest_schema, dispatch."""

from __future__ import annotations

from pathlib import Path

import pytest

from qfull_chem import ChemistrySimulation, load_instance
from qfull_chem.sim import _resolve_path


def test_chemistry_simulation_satisfies_protocol() -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    Simulation = qcompass_core.Simulation

    sim = ChemistrySimulation()
    assert isinstance(sim, Simulation)


def test_manifest_schema_exposes_problem_fields() -> None:
    schema = ChemistrySimulation.manifest_schema()
    assert schema["type"] == "object"
    for required in ("molecule", "basis", "active_space", "backend_preference",
                     "reference", "shots", "seed"):
        assert required in schema["properties"], required


def test_resolve_path_classical_returns_classical() -> None:
    assert _resolve_path("classical") == "classical"


def test_resolve_path_sqd_explicit() -> None:
    assert _resolve_path("sqd") == "sqd"


def test_resolve_path_dice_explicit() -> None:
    assert _resolve_path("dice") == "dice"


def test_resolve_path_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown backend_preference"):
        _resolve_path("warp")


def test_classical_dispatch_writes_sidecar(tmp_path: Path) -> None:
    pytest.importorskip("pyscf")
    qcompass_core = pytest.importorskip("qcompass_core")

    artifacts = tmp_path / "art"
    sim = ChemistrySimulation(artifacts_root=artifacts)
    problem = load_instance("h2")
    manifest = qcompass_core.Manifest(
        domain="chemistry",
        version="1.0",
        problem=problem.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    assert result.path_taken == "classical"
    assert result.sidecar_path.exists()
    assert result.classical_method == "FCI"
    assert result.classical_warning is None
    assert result.quantum_energy is None


def test_validate_returns_summary(tmp_path: Path) -> None:
    pytest.importorskip("pyscf")
    qcompass_core = pytest.importorskip("qcompass_core")

    sim = ChemistrySimulation(artifacts_root=tmp_path)
    problem = load_instance("h2")
    manifest = qcompass_core.Manifest(
        domain="chemistry",
        version="1.0",
        problem=problem.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    summary = sim.validate(result, reference=-1.1372744)
    assert summary["domain"] == "chemistry"
    assert summary["molecule"] == "H2"
    assert summary["path_taken"] == "classical"
    assert summary["relative_error"] is not None


def test_prepare_rejects_wrong_domain() -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = ChemistrySimulation()
    manifest = qcompass_core.Manifest(
        domain="cosmology",
        version="1.0",
        problem={"x": 1},
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    with pytest.raises(ValueError, match="domain='chemistry'"):
        sim.prepare(manifest)
