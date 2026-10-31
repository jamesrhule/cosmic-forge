from __future__ import annotations

import pytest
from pydantic import ValidationError

from qfull_nuc import NuclearProblem, ZeroNuBBToyParams, load_instance


@pytest.mark.parametrize("name", ["zero_nu_bb_l4", "zero_nu_bb_l6", "ncsm_2body"])
def test_load_instance(name: str) -> None:
    p = load_instance(name)
    assert isinstance(p, NuclearProblem)


def test_kind_must_match_payload() -> None:
    with pytest.raises(ValidationError):
        NuclearProblem.model_validate({"kind": "zero_nu_bb_toy", "ncsm_matrix_element": {}})


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        NuclearProblem.model_validate({
            "kind": "zero_nu_bb_toy",
            "zero_nu_bb_toy": {"L": 4},
            "stowaway": True,
        })


def test_canonical_payload_is_stable() -> None:
    p = NuclearProblem(
        kind="zero_nu_bb_toy",
        zero_nu_bb_toy=ZeroNuBBToyParams(L=4),
    )
    a = p.canonical_payload()
    b = NuclearProblem.model_validate(p.model_dump()).canonical_payload()
    assert a == b
