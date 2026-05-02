"""S-grav-1 — BLOCKING provenance-warning gate (PROMPT 9 v2 §A).

This audit is the Jafferis-style guard the v2 spec mandates:

  1. The schema layer rejects ``is_learned_hamiltonian=True``
     manifests that ship an empty / missing ``provenance_warning``.
  2. A learned-Hamiltonian run that DOES carry a warning surfaces
     it verbatim in:
       - ``GravityResult.provenance_warning``
       - the provenance sidecar JSON (top-level + error_mitigation_config)
  3. Non-learned (first-principles) runs are unaffected.

Failing this test BLOCKS merges. Locally verify by mutating
:func:`_learned_hamiltonian_requires_warning` in
``qfull_grav.manifest`` to ``return self`` unconditionally and
re-running ``pytest src/qfull_grav/audit/test_s_grav_1.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from qfull_grav import GravityProblem, GravitySimulation


@pytest.mark.s_audit
def test_learned_manifest_without_warning_is_rejected() -> None:
    """Schema BLOCKS: missing warning on learned-Hamiltonian flag."""
    with pytest.raises(ValidationError) as exc:
        GravityProblem.model_validate({
            "kind": "syk_dense",
            "backend_preference": "classical",
            "is_learned_hamiltonian": True,
            "provenance_warning": None,
            "syk_dense": {"N": 8, "q": 4, "J": 1.0, "seed": 0},
        })
    msg = str(exc.value).lower()
    assert "provenance_warning" in msg
    assert "must" in msg or "required" in msg


@pytest.mark.s_audit
def test_learned_manifest_with_empty_warning_is_rejected() -> None:
    """An empty / whitespace-only warning string is treated as missing."""
    with pytest.raises(ValidationError):
        GravityProblem.model_validate({
            "kind": "syk_dense",
            "backend_preference": "classical",
            "is_learned_hamiltonian": True,
            "provenance_warning": "   ",
            "syk_dense": {"N": 8, "q": 4, "J": 1.0, "seed": 0},
        })


@pytest.mark.s_audit
def test_learned_manifest_with_warning_surfaces_in_sidecar(
    syk_learned_n8: GravityProblem,
    artifacts_dir: Path,
) -> None:
    """The warning string flows verbatim into the provenance sidecar."""
    qcompass_core = pytest.importorskip("qcompass_core")
    sim = GravitySimulation(artifacts_root=artifacts_dir)
    manifest = qcompass_core.Manifest(
        domain="gravity",
        version="1.0",
        problem=syk_learned_n8.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)

    assert result.is_learned_hamiltonian is True
    assert result.provenance_warning, (
        "GravityResult must carry the manifest's provenance_warning verbatim."
    )

    blob = json.loads(result.sidecar_path.read_text())
    assert blob["is_learned_hamiltonian"] is True
    assert blob["provenance_warning"] == syk_learned_n8.provenance_warning
    em = blob["provenance"]["error_mitigation_config"]
    assert em.get("provenance_warning") == syk_learned_n8.provenance_warning
    assert em.get("is_learned_hamiltonian") is True


@pytest.mark.s_audit
def test_first_principles_manifest_does_not_set_warning(
    syk_n8: GravityProblem, artifacts_dir: Path,
) -> None:
    """Non-learned manifests don't carry a warning; sidecar reflects that."""
    qcompass_core = pytest.importorskip("qcompass_core")
    assert syk_n8.is_learned_hamiltonian is False
    assert syk_n8.provenance_warning in (None, "")

    sim = GravitySimulation(artifacts_root=artifacts_dir)
    manifest = qcompass_core.Manifest(
        domain="gravity",
        version="1.0",
        problem=syk_n8.model_dump(),
        backend_request=qcompass_core.BackendRequest(kind="classical"),
    )
    instance = sim.prepare(manifest)
    backend = qcompass_core.get_backend(manifest.backend_request)
    result = sim.run(instance, backend)
    assert result.is_learned_hamiltonian is False
    blob = json.loads(result.sidecar_path.read_text())
    assert blob["is_learned_hamiltonian"] is False
    em = blob["provenance"]["error_mitigation_config"]
    assert "provenance_warning" not in em
