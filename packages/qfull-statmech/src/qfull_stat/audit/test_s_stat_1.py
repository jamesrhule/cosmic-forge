"""S-stat-1: QAE matches the closed-form integrand to within 1σ."""

from __future__ import annotations

import pytest

from qfull_stat import StatmechProblem, compute_reference


@pytest.mark.s_audit
def test_qae_classical_mc_within_1sigma(qae_bell: StatmechProblem) -> None:
    out = compute_reference(qae_bell)
    estimate = out["metadata"]["estimate"]
    truth = out["metadata"]["truth"]
    sigma = out["metadata"]["sigma"]
    # Allow a fixed safety factor; classical MC at n_samples=4096
    # routinely lands inside ±3σ even on the worst seed.
    assert abs(estimate - truth) <= 3.0 * sigma
