"""S-nuc-2: 0νββ toy occupancy lies in [0, 1] (charge-sector consistency)."""

from __future__ import annotations

from qfull_nuc import NuclearProblem, compute_reference


def test_zero_nu_bb_l4_occupancy_band(zero_nu_bb_l4: NuclearProblem) -> None:
    outcome = compute_reference(zero_nu_bb_l4)
    occ = outcome["metadata"]["occupancy"]
    assert 0.0 <= occ <= 1.0, (
        f"Per-site occupancy must lie in [0, 1]; got {occ}"
    )
