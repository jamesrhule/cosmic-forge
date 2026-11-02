"""S-grav-2: Dense SYK ED reproduces deterministic ground-state energy."""

from __future__ import annotations

import pytest

from qfull_grav import GravityProblem, compute_reference


@pytest.mark.s_audit
def test_syk_dense_n8_ground_state_deterministic(syk_n8: GravityProblem) -> None:
    out_a = compute_reference(syk_n8)
    out_b = compute_reference(syk_n8)
    assert out_a["energy"] == out_b["energy"]
    assert out_a["hash"] == out_b["hash"]
    assert out_a["metadata"]["model_domain"] == "toy_SYK_1+1D"
    # Spectral form factor sanity: g(t=1) > 0 by construction.
    assert out_a["metadata"]["spectral_form_factor"] > 0.0
