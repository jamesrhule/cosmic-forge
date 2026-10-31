"""S-grav-6: every kind maps to a model_domain tag."""

from __future__ import annotations

import pytest

from qfull_grav import model_domain_for_kind


_EXPECTED = {
    "syk_dense": "toy_SYK_1+1D",
    "syk_sparse": "SYK_sparse",
    "jt_matrix": "JT_matrix_model",
}


@pytest.mark.s_audit
def test_kind_to_model_domain_complete() -> None:
    for kind, expected in _EXPECTED.items():
        assert model_domain_for_kind(kind) == expected


@pytest.mark.s_audit
def test_unknown_kind_raises() -> None:
    with pytest.raises(ValueError, match="unknown gravity"):
        model_domain_for_kind("ads_cft_correspondence")
