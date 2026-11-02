"""S-stat-2: Ising chain partition function is finite + ⟨E⟩ ≥ E_0."""

from __future__ import annotations

import pytest

from qfull_stat import StatmechProblem, compute_reference


@pytest.mark.s_audit
def test_ising_partition_returns_consistent_quantities(
    metropolis_l6: StatmechProblem,
) -> None:
    out = compute_reference(metropolis_l6)
    md = out["metadata"]
    assert md["Z"] > 0.0
    assert md["mean_energy"] >= md["ground_state"] - 1e-9
    assert md["model_domain"] == "stat_mech_ising"
