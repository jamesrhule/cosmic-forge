from __future__ import annotations

import pytest
from pydantic import ValidationError

from qfull_hep import HEPProblem, SchwingerParams, load_instance


@pytest.mark.parametrize("name", ["schwinger_l4", "schwinger_l6", "schwinger_l10"])
def test_load_instance(name: str) -> None:
    p = load_instance(name)
    assert isinstance(p, HEPProblem)
    assert p.kind == "schwinger"


def test_kind_must_match_payload() -> None:
    with pytest.raises(ValidationError):
        HEPProblem.model_validate({"kind": "schwinger", "zN": {"N": 2, "Lx": 2, "Ly": 2}})


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        HEPProblem.model_validate({
            "kind": "schwinger",
            "schwinger": {"L": 4},
            "stowaway": True,
        })


def test_canonical_payload_is_stable() -> None:
    p = HEPProblem(kind="schwinger", schwinger=SchwingerParams(L=4))
    a = p.canonical_payload()
    b = HEPProblem.model_validate(p.model_dump()).canonical_payload()
    assert a == b
