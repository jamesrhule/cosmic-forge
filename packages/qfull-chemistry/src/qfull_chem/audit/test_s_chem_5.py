"""S-chem-5: ProvenanceRecord present and classical_reference_hash recorded.

Always runs (no heavy SDK required). Verifies the dispatch envelope
on every backend_preference and asserts FeMoco-toy carries the
``"unavailable"`` sentinel + ``provenance_warning="no_classical_reference"``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qfull_chem import (
    ChemistryProblem,
    ChemistrySimulation,
    compute_reference,
)


@pytest.mark.s_audit
def test_femoco_classical_reference_marked_unavailable(
    femoco_problem: ChemistryProblem,
) -> None:
    outcome = compute_reference(femoco_problem)
    assert outcome["hash"] == "unavailable"
    assert outcome["warning"] == "no_classical_reference"
    assert outcome["method_used"] == "unavailable"


@pytest.mark.s_audit
def test_classical_path_yields_provenance_sidecar(
    h2_problem: ChemistryProblem,
    artifacts_dir: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    pytest.importorskip("pyscf")

    sim = ChemistrySimulation(artifacts_root=artifacts_dir)
    manifest = qcompass_core.Manifest(
        domain="chemistry",
        version="1.0",
        problem=h2_problem.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)

    sidecar = result.sidecar_path
    assert sidecar.exists()
    blob = json.loads(sidecar.read_text())
    assert blob["domain"] == "chemistry"
    assert blob["pathTaken"] == "classical"
    assert blob["provenance"]["classical_reference_hash"]
    assert blob["metrics"]["classical_energy"] is not None
    # H2 path is FCI live → no warning.
    assert blob["provenance_warning"] is None


@pytest.mark.s_audit
def test_femoco_run_marks_warning_in_sidecar(
    femoco_problem: ChemistryProblem,
    artifacts_dir: Path,
) -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = ChemistrySimulation(artifacts_root=artifacts_dir)
    # FeMoco-toy uses backend_preference="dice"; on non-Linux that
    # raises before we reach the sidecar. Force backend_preference
    # to "classical" so we exercise the warning-propagation code on
    # every platform.
    fem = femoco_problem.model_copy(update={"backend_preference": "classical"})
    manifest = qcompass_core.Manifest(
        domain="chemistry",
        version="1.0",
        problem=fem.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    blob = json.loads(result.sidecar_path.read_text())
    assert blob["provenance"]["classical_reference_hash"] == "unavailable"
    assert blob["provenance_warning"] == "no_classical_reference"
    assert blob["metrics"]["classical_energy"] != blob["metrics"]["classical_energy"]  # NaN
