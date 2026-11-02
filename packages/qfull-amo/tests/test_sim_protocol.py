from __future__ import annotations

from pathlib import Path

import pytest

from qfull_amo import AMOSimulation, load_instance
from qfull_amo.sim import _resolve_path


def test_satisfies_simulation_protocol() -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    assert isinstance(AMOSimulation(), qcompass_core.Simulation)


def test_manifest_schema_has_required_keys() -> None:
    schema = AMOSimulation.manifest_schema()
    for k in ("kind", "backend_preference", "rydberg_ground_state", "mis_toy"):
        assert k in schema["properties"]


def test_resolve_path_classical() -> None:
    assert _resolve_path("classical") == "classical"


def test_resolve_path_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown backend_preference"):
        _resolve_path("warp")


def test_classical_dispatch_writes_sidecar(tmp_path: Path) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = AMOSimulation(artifacts_root=tmp_path)
    problem = load_instance("mis_path_5")
    manifest = qcompass_core.Manifest(
        domain="amo",
        version="1.0",
        problem=problem.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    assert result.sidecar_path.exists()
    assert result.classical_method == "mis_brute_force"
