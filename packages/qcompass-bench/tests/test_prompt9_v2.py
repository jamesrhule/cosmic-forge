"""PROMPT 9 v2 reconciliation tests.

Pins the v2 §DEFINITION OF DONE invariants:

  - ``list_domains()`` returns the v2 stable set: cosmology.ucglef1,
    chemistry, condmat, amo, hep, nuclear, gravity, statmech (plus
    null) — the full ≥8 domain list.
  - The FT FeMoco + Schwinger templates emit cleanly against the
    pinned Azure RE test vectors.
  - The qfull-gravity provenance-warning Pydantic guard fires on
    learned-Hamiltonian manifests with empty warnings (the BLOCKING
    test that v2 §DoD names by hand).
"""

from __future__ import annotations

import pytest


def test_list_domains_has_eight_real_domains() -> None:
    qcompass_core = pytest.importorskip("qcompass_core")
    domains = set(qcompass_core.registry.list_domains())
    required = {
        "cosmology.ucglef1",
        "chemistry",
        "condmat",
        "amo",
        "hep",
        "nuclear",
        "gravity",
        "statmech",
    }
    missing = required - domains
    assert not missing, (
        f"v2 §DoD requires ≥8 domains; missing: {sorted(missing)}"
    )
    # The "null" sentinel is also exposed by the registry.
    assert "null" in domains


def test_fault_tolerant_plan_femoco_template_matches_pin(tmp_path) -> None:
    pytest.importorskip("qfull_chem.femoco_ft")
    pytest.importorskip("qcompass_router.ft")
    from qfull_chem.femoco_ft import emit_femoco_qpe_template
    from qcompass_router.ft import PINNED_TEST_VECTORS

    qir_path, plan = emit_femoco_qpe_template(qir_dir=tmp_path)
    pin = PINNED_TEST_VECTORS["femoco_thc_active_152"]
    assert plan.logical_qubits == pin["logical_qubits"]
    assert plan.toffoli_count == pin["toffoli_count"]
    assert plan.magic_state_factory == pin["magic_state_factory"]
    assert qir_path.exists()


def test_fault_tolerant_plan_schwinger_template_matches_pin(tmp_path) -> None:
    pytest.importorskip("qfull_hep.ft")
    pytest.importorskip("qcompass_router.ft")
    from qfull_hep.ft import emit_schwinger_ft_qpe_template
    from qcompass_router.ft import PINNED_TEST_VECTORS

    qir_path, plan = emit_schwinger_ft_qpe_template(qir_dir=tmp_path)
    pin = PINNED_TEST_VECTORS["schwinger_3plus1d_n128"]
    assert plan.logical_qubits == pin["logical_qubits"]
    assert plan.toffoli_count == pin["toffoli_count"]
    assert plan.code_distance == pin["code_distance"]
    assert qir_path.exists()


def test_gravity_provenance_warning_guard_blocks() -> None:
    """The Pydantic-level guard MUST fire on learned + empty warning.

    PROMPT 9 v2 §DoD names this as the BLOCKING test — verify
    locally by setting `_learned_hamiltonian_requires_warning` to
    `return self` and confirming this test fails.
    """
    pytest.importorskip("qfull_grav")
    from qfull_grav import GravityProblem
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="provenance_warning"):
        GravityProblem.model_validate({
            "kind": "syk_dense",
            "is_learned_hamiltonian": True,
            "provenance_warning": "",
            "syk_dense": {"N": 8, "q": 4, "J": 1.0, "seed": 0},
        })
