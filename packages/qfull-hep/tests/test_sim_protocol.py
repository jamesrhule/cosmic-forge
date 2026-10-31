from __future__ import annotations

from pathlib import Path

import pytest

from qfull_hep import HEPSimulation, load_instance
from qfull_hep.scadapt_vqe import is_available, run_scadapt_vqe
from qfull_hep.sim import _resolve_path


def test_satisfies_simulation_protocol() -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    assert isinstance(HEPSimulation(), qcompass_core.Simulation)


def test_manifest_schema_has_required_keys() -> None:
    schema = HEPSimulation.manifest_schema()
    for k in ("kind", "backend_preference", "schwinger"):
        assert k in schema["properties"]


def test_resolve_path_classical() -> None:
    assert _resolve_path("classical") == "classical"


def test_resolve_path_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown backend_preference"):
        _resolve_path("warp")


def test_classical_dispatch_writes_sidecar(tmp_path: Path) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = HEPSimulation(artifacts_root=tmp_path)
    problem = load_instance("schwinger_l4")
    manifest = qcompass_core.Manifest(
        domain="hep",
        version="1.0",
        problem=problem.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    assert result.sidecar_path.exists()
    assert result.classical_method == "schwinger_ed"


def test_scadapt_vqe_unavailable_raises() -> None:
    if is_available():
        pytest.skip("scadapt_vqe is available; skip the absent-path branch")
    with pytest.raises(NotImplementedError, match="not vendored yet"):
        run_scadapt_vqe(load_instance("schwinger_l4"))
