from __future__ import annotations

import pytest
from pydantic import ValidationError

from qfull_cm import CondMatProblem, HubbardParams, load_instance


@pytest.mark.parametrize(
    "name", ["hubbard_4x4", "heisenberg_chain_10", "otoc_chain_8"],
)
def test_load_instance(name: str) -> None:
    problem = load_instance(name)
    assert isinstance(problem, CondMatProblem)


def test_kind_must_match_payload() -> None:
    with pytest.raises(ValidationError):
        CondMatProblem.model_validate({
            "kind": "hubbard",
            "heisenberg": {"L": 4, "J": 1.0, "Jz": 1.0},
        })


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        CondMatProblem.model_validate({
            "kind": "hubbard",
            "hubbard": {"L": [2, 2]},
            "stowaway": True,
        })


def test_canonical_payload_is_stable() -> None:
    problem = CondMatProblem(
        kind="hubbard",
        hubbard=HubbardParams(L=(2, 2)),
    )
    a = problem.canonical_payload()
    b = CondMatProblem.model_validate(problem.model_dump()).canonical_payload()
    assert a == b
