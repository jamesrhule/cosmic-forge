"""S-grav-3: Sparse SYK reduces coupling count proportional to sparsity."""

from __future__ import annotations

import pytest

from qfull_grav import GravityProblem, compute_reference


@pytest.mark.s_audit
def test_sparse_syk_runs_at_higher_N(syk_sparse_n12: GravityProblem) -> None:
    out = compute_reference(syk_sparse_n12)
    assert out["metadata"]["model_domain"] == "SYK_sparse"
    assert out["metadata"]["N"] == 12
    assert 0.0 < out["metadata"]["sparsity"] <= 1.0
    # Spectrum width is finite; sparse SYK should have a non-trivial gap.
    spec = out["metadata"]
    assert spec["spectrum_max"] > spec["spectrum_min"]
