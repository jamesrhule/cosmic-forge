"""S-grav-4: JT matrix ensemble reproduces semicircle support."""

from __future__ import annotations

import pytest

from qfull_grav import GravityProblem, compute_reference


@pytest.mark.s_audit
def test_jt_matrix_returns_semicircle_band(jt_n16: GravityProblem) -> None:
    out = compute_reference(jt_n16)
    assert out["metadata"]["model_domain"] == "JT_matrix_model"
    spec_min = out["metadata"]["spectrum_min"]
    spec_max = out["metadata"]["spectrum_max"]
    # Wigner semicircle: support ⊂ (-2, 2) for our scale convention.
    assert spec_min > -3.0
    assert spec_max < 3.0
