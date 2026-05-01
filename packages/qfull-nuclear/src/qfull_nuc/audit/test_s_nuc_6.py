"""S-nuc-6: particle-obs schema + model_domain across kinds (PROMPT 5 v2).

Every nuclear run emits a ``particle_obs`` dict keyed by the
appropriate observable for its kind. ``model_domain`` is recorded
on the result + provenance sidecar and matches the canonical
mapping ``zero_nu_bb_toy → 1+1D_toy``,
``ncsm_matrix_element → few_body_3d``,
``effective_hamiltonian → effective_hamiltonian``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qfull_nuc import NuclearProblem, NuclearSimulation


def _run(
    sim: NuclearSimulation,
    problem: NuclearProblem,
    qcompass_core,
):
    manifest = qcompass_core.Manifest(
        domain="nuclear",
        version="1.0",
        problem=problem.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    return sim.run(instance, backend)


@pytest.mark.s_audit
def test_zero_nu_bb_observables_units(
    zero_nu_bb_l4: NuclearProblem, artifacts_dir: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = NuclearSimulation(artifacts_root=artifacts_dir)
    result = _run(sim, zero_nu_bb_l4, qcompass_core)

    obs = result.particle_obs
    assert "lnv_signature" in obs
    assert "occupancy_imbalance" in obs
    assert obs["lnv_signature"]["unit"] == "dimensionless"
    assert obs["occupancy_imbalance"]["unit"] == "dimensionless"
    assert result.model_domain == "1+1D_toy"

    blob = json.loads(result.sidecar_path.read_text())
    assert blob["model_domain"] == "1+1D_toy"
    assert blob["particle_obs"]["occupancy_imbalance"]["status"] == "ok"


@pytest.mark.s_audit
def test_ncsm_observables_units(
    ncsm_2body: NuclearProblem, artifacts_dir: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = NuclearSimulation(artifacts_root=artifacts_dir)
    result = _run(sim, ncsm_2body, qcompass_core)

    obs = result.particle_obs
    assert "antisymmetry_residual" in obs
    assert obs["antisymmetry_residual"]["unit"] == "matrix_element"
    assert result.model_domain == "few_body_3d"

    blob = json.loads(result.sidecar_path.read_text())
    assert blob["model_domain"] == "few_body_3d"


@pytest.mark.s_audit
def test_effective_hamiltonian_observables_units(
    heavy_neutrino_mixing: NuclearProblem, artifacts_dir: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = NuclearSimulation(artifacts_root=artifacts_dir)
    result = _run(sim, heavy_neutrino_mixing, qcompass_core)

    obs = result.particle_obs
    assert "mixing_amplitude" in obs
    assert "energy_gap" in obs
    assert obs["mixing_amplitude"]["unit"] == "probability"
    assert obs["energy_gap"]["unit"] == "natural_units"
    assert result.model_domain == "effective_hamiltonian"

    blob = json.loads(result.sidecar_path.read_text())
    assert blob["model_domain"] == "effective_hamiltonian"
    assert isinstance(blob["particle_obs"]["mixing_amplitude"]["value"], float)
