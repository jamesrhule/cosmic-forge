"""S-hep-3: anomaly-inflow consistency.

For a half-filled Schwinger lattice, the total expected occupation
is L/2 + small finite-size corrections. The audit ensures the
classical reference reports both the actual ⟨n_total⟩ and the
vacuum baseline (L/2) so downstream analyses can compute the chiral
charge change Δ Q_chiral = ⟨n⟩ − L/2 unambiguously.
"""

from __future__ import annotations

from qfull_hep import HEPProblem, compute_reference


def test_anomaly_inflow_records_baseline_and_total(
    schwinger_l4: HEPProblem,
) -> None:
    outcome = compute_reference(schwinger_l4)
    meta = outcome["metadata"]
    assert "vacuum_q_total" in meta
    assert "total_n_expected" in meta
    # Vacuum baseline is exactly L/2.
    assert meta["vacuum_q_total"] == 4 / 2
    # Total expectation is bounded by [0, L].
    assert 0.0 <= meta["total_n_expected"] <= 4.0 + 1e-6
