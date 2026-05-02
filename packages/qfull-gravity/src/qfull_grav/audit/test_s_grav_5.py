"""S-grav-5: GravitySimulation satisfies the qcompass.Simulation Protocol."""

from __future__ import annotations

from pathlib import Path

import pytest

from qfull_grav import GravityProblem, GravitySimulation


@pytest.mark.s_audit
def test_satisfies_simulation_protocol() -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    assert isinstance(GravitySimulation(), qcompass_core.Simulation)


@pytest.mark.s_audit
def test_manifest_schema_has_required_keys() -> None:
    schema = GravitySimulation.manifest_schema()
    for k in ("kind", "is_learned_hamiltonian", "provenance_warning"):
        assert k in schema["properties"]


@pytest.mark.s_audit
def test_classical_dispatch_writes_sidecar(
    syk_n8: GravityProblem, tmp_path: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = GravitySimulation(artifacts_root=tmp_path)
    manifest = qcompass_core.Manifest(
        domain="gravity",
        version="1.0",
        problem=syk_n8.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    assert result.sidecar_path.exists()
    assert result.classical_method.startswith("syk_")
