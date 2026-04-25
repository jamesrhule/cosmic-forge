"""S-hep-5: ProvenanceRecord present + classical_reference_hash recorded."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qfull_hep import HEPProblem, HEPSimulation


@pytest.mark.s_audit
def test_provenance_sidecar_written(
    schwinger_l4: HEPProblem,
    artifacts_dir: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = HEPSimulation(artifacts_root=artifacts_dir)
    manifest = qcompass_core.Manifest(
        domain="hep",
        version="1.0",
        problem=schwinger_l4.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    blob = json.loads(result.sidecar_path.read_text())
    assert blob["domain"] == "hep"
    assert blob["pathTaken"] == "classical"
    assert blob["provenance"]["classical_reference_hash"]
    assert blob["provenance_warning"] is None
