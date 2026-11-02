"""S-stat-4: StatmechSimulation satisfies the qcompass.Simulation Protocol."""

from __future__ import annotations

from pathlib import Path

import pytest

from qfull_stat import StatmechProblem, StatmechSimulation


@pytest.mark.s_audit
def test_satisfies_simulation_protocol() -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    assert isinstance(StatmechSimulation(), qcompass_core.Simulation)


@pytest.mark.s_audit
def test_classical_dispatch_writes_sidecar(
    qae_bell: StatmechProblem, tmp_path: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = StatmechSimulation(artifacts_root=tmp_path)
    manifest = qcompass_core.Manifest(
        domain="statmech",
        version="1.0",
        problem=qae_bell.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    assert result.sidecar_path.exists()
    assert result.classical_method == "scipy_mc_qae"
