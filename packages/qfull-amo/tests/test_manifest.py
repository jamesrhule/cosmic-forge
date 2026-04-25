from __future__ import annotations

import pytest
from pydantic import ValidationError

from qfull_amo import AMOProblem, RydbergParams, load_instance


@pytest.mark.parametrize("name", ["rydberg_chain_8", "rydberg_ring_6", "mis_path_5"])
def test_load_instance(name: str) -> None:
    p = load_instance(name)
    assert isinstance(p, AMOProblem)


def test_kind_must_match_payload() -> None:
    with pytest.raises(ValidationError):
        AMOProblem.model_validate({"kind": "rydberg_ground_state", "mis_toy": {"n_nodes": 2, "edges": []}})


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        AMOProblem.model_validate({
            "kind": "rydberg_ground_state",
            "rydberg_ground_state": {"L": 4},
            "stowaway": True,
        })


def test_canonical_payload_is_stable() -> None:
    p = AMOProblem(
        kind="rydberg_ground_state",
        rydberg_ground_state=RydbergParams(L=4),
    )
    a = p.canonical_payload()
    b = AMOProblem.model_validate(p.model_dump()).canonical_payload()
    assert a == b
