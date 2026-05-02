"""S-stat-3: TFD partition function reproduces the Ising backbone Z(β)."""

from __future__ import annotations

import math

import pytest

from qfull_stat import StatmechProblem, compute_reference


@pytest.mark.s_audit
def test_tfd_partition_function_finite(tfd_l4: StatmechProblem) -> None:
    out = compute_reference(tfd_l4)
    Z = out["metadata"]["Z"]
    assert Z > 0.0
    assert math.isfinite(Z)
    assert out["metadata"]["model_domain"] == "stat_mech_tfd"
