"""S-nuc-5: ProvenanceRecord present + model_domain="1+1D_toy" flagged."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qfull_nuc import NuclearProblem, NuclearSimulation


@pytest.mark.s_audit
def test_provenance_sidecar_includes_model_domain(
    zero_nu_bb_l4: NuclearProblem,
    artifacts_dir: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = NuclearSimulation(artifacts_root=artifacts_dir)
    manifest = qcompass_core.Manifest(
        domain="nuclear",
        version="1.0",
        problem=zero_nu_bb_l4.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    blob = json.loads(result.sidecar_path.read_text())
    assert blob["domain"] == "nuclear"
    err = blob["provenance"]["error_mitigation_config"]
    assert err == {"model_domain": "1+1D_toy"}, (
        f"0νββ toy must always carry model_domain='1+1D_toy'; got {err}"
    )
