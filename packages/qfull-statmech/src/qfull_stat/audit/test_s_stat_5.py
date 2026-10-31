"""S-stat-5: provenance sidecar carries the right model_domain tag."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qfull_stat import StatmechProblem, StatmechSimulation


_EXPECTED_MODEL_DOMAIN = {
    "qae": "stat_mech_mc",
    "metropolis_ising": "stat_mech_ising",
    "tfd": "stat_mech_tfd",
}


@pytest.mark.s_audit
def test_sidecar_model_domain_matches_kind(
    qae_bell: StatmechProblem,
    metropolis_l6: StatmechProblem,
    tfd_l4: StatmechProblem,
    tmp_path: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = StatmechSimulation(artifacts_root=tmp_path)
    for problem in (qae_bell, metropolis_l6, tfd_l4):
        manifest = qcompass_core.Manifest(
            domain="statmech",
            version="1.0",
            problem=problem.model_dump(),
            backend_request=qcompass_core.BackendRequest(kind="classical"),
        )
        instance = sim.prepare(manifest)
        backend = qcompass_core.get_backend(manifest.backend_request)
        result = sim.run(instance, backend)
        blob = json.loads(result.sidecar_path.read_text())
        em = blob["provenance"]["error_mitigation_config"]
        assert em["model_domain"] == _EXPECTED_MODEL_DOMAIN[problem.kind]
