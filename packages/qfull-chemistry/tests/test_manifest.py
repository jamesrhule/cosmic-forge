"""Manifest tests: registry defaults + load_instance round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from qfull_chem import ChemistryProblem, MOLECULE_REGISTRY, load_instance


def test_registry_covers_canonical_four() -> None:
    expected = {"H2", "LiH", "N2", "FeMoco_toy"}
    assert set(MOLECULE_REGISTRY) == expected


@pytest.mark.parametrize("name", ["h2", "lih", "n2", "femoco_toy"])
def test_load_instance_returns_validated_problem(name: str) -> None:
    problem = load_instance(name)
    assert isinstance(problem, ChemistryProblem)
    assert problem.molecule in MOLECULE_REGISTRY


def test_h2_defaults_resolve() -> None:
    problem = load_instance("h2")
    assert problem.basis == "sto-3g"
    assert problem.reference == "FCI"
    assert problem.active_space == (2, 2)
    # Geometry mirrors the YAML body, including the trailing newline
    # that PySCF accepts.
    assert "H 0 0 0" in problem.geometry  # type: ignore[arg-type]
    assert "H 0 0 0.74" in problem.geometry  # type: ignore[arg-type]


def test_femoco_loads_without_fcidump() -> None:
    """Manifest validation must not require fcidump_path at planning time."""
    problem = load_instance("femoco_toy")
    assert problem.fcidump_path is None
    assert problem.active_space == (54, 54)
    assert problem.backend_preference == "dice"


def test_unknown_instance_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_instance("water")


def test_load_instance_from_path(tmp_path: Path) -> None:
    payload = {
        "molecule": "H2",
        "geometry": "H 0 0 0; H 0 0 0.74",
    }
    p = tmp_path / "custom.yaml"
    p.write_text(yaml.safe_dump(payload))
    problem = load_instance(str(p))
    assert problem.molecule == "H2"


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        ChemistryProblem.model_validate({
            "molecule": "H2",
            "stowaway": True,  # extra="forbid"
        })


def test_canonical_payload_is_stable() -> None:
    problem = load_instance("h2")
    payload_a = problem.canonical_problem_payload()
    payload_b = ChemistryProblem.model_validate(
        problem.model_dump()
    ).canonical_problem_payload()
    assert payload_a == payload_b
