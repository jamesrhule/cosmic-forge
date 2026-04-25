"""S-amo-1: Rydberg ground-state energy is finite and bounded."""

from __future__ import annotations

from qfull_amo import AMOProblem, compute_reference


def test_rydberg_chain_8_energy_finite_and_bounded(
    rydberg_chain_8: AMOProblem,
) -> None:
    outcome = compute_reference(rydberg_chain_8)
    assert outcome["method_used"] == "rydberg_ed"
    e = outcome["energy"]
    L = outcome["metadata"]["L"]
    # Energy lower bound: -Ω/2 * L (everyone driven, no detuning).
    # Upper bound: Δ * L + V * L for fully blockaded ferromagnet.
    assert -2.0 * L < e < 100.0 * L
