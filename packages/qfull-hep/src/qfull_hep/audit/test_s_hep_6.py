"""S-hep-6: particle-obs units annotation (PROMPT 5 v2 §A audit).

Every HEP run carries a ``particle_obs`` dict keyed by observable
name with ``value`` / ``unit`` / ``uncertainty`` / ``status`` /
``notes``. The Schwinger fixture must surface chiral_condensate,
string_tension, anomaly_density with consistent unit tags so the
frontend visualizer + leaderboard renders them with a stable
schema.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qfull_hep import HEPProblem, HEPSimulation


_REQUIRED_KEYS = {"chiral_condensate", "string_tension", "anomaly_density"}
_EXPECTED_UNITS = {
    "chiral_condensate": "dimensionless",
    "string_tension": "g_squared_per_lattice_spacing",
    "anomaly_density": "dimensionless",
}


@pytest.mark.s_audit
def test_schwinger_particle_obs_units_present(
    schwinger_l4: HEPProblem, artifacts_dir: Path,
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

    # Result attribute carries the particle_obs dict.
    obs = result.particle_obs
    assert _REQUIRED_KEYS.issubset(obs.keys()), (
        f"missing observables; got {sorted(obs.keys())}"
    )

    # Each observable carries the v2 schema fields.
    for name, expected_unit in _EXPECTED_UNITS.items():
        entry = obs[name]
        assert entry["unit"] == expected_unit, (
            f"{name}: unit {entry['unit']!r} != {expected_unit!r}"
        )
        assert "status" in entry
        assert entry["status"] in {"ok", "unavailable"}
        assert "notes" in entry

    # Sidecar mirrors the dict.
    blob = json.loads(result.sidecar_path.read_text())
    sidecar_obs = blob["particle_obs"]
    assert _REQUIRED_KEYS.issubset(sidecar_obs.keys())
    assert sidecar_obs["chiral_condensate"]["status"] == "ok"
    assert isinstance(sidecar_obs["chiral_condensate"]["value"], float)
