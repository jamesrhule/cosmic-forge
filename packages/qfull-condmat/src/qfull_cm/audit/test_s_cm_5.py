"""S-cm-5: ProvenanceRecord present + classical_reference_hash recorded."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qfull_cm import CondMatProblem, CondMatSimulation


@pytest.mark.s_audit
def test_provenance_sidecar_written(
    heisenberg_problem: CondMatProblem,
    artifacts_dir: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = CondMatSimulation(artifacts_root=artifacts_dir)
    manifest = qcompass_core.Manifest(
        domain="condmat",
        version="1.0",
        problem=heisenberg_problem.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    sidecar = result.sidecar_path
    assert sidecar.exists()
    blob = json.loads(sidecar.read_text())
    assert blob["domain"] == "condmat"
    assert blob["pathTaken"] == "classical"
    assert blob["provenance"]["classical_reference_hash"]
    assert blob["provenance_warning"] is None
