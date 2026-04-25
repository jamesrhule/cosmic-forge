"""S-amo-5: ProvenanceRecord present + classical_reference_hash recorded."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qfull_amo import AMOProblem, AMOSimulation


@pytest.mark.s_audit
def test_provenance_sidecar_written(
    rydberg_chain_8: AMOProblem,
    artifacts_dir: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = AMOSimulation(artifacts_root=artifacts_dir)
    manifest = qcompass_core.Manifest(
        domain="amo",
        version="1.0",
        problem=rydberg_chain_8.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    blob = json.loads(result.sidecar_path.read_text())
    assert blob["domain"] == "amo"
    assert blob["pathTaken"] == "classical"
    assert blob["provenance"]["classical_reference_hash"]
    assert blob["provenance_warning"] is None
