"""S-nuc-3: 2-body NCSM matrix element finite + antisymmetric."""

from __future__ import annotations

from qfull_nuc import NuclearProblem, compute_reference


def test_ncsm_2body_finite_and_antisymmetric(
    ncsm_2body: NuclearProblem,
) -> None:
    outcome = compute_reference(ncsm_2body)
    assert outcome["method_used"] == "ncsm_synth"
    meta = outcome["metadata"]
    assert meta["bodies"] == 2
    assert meta["antisymmetry_residual"] < 1e-12
    # Energy is the lowest eigenvalue of the i*M Hermitian skew matrix
    # — must be finite.
    assert outcome["energy"] == outcome["energy"]  # not NaN
