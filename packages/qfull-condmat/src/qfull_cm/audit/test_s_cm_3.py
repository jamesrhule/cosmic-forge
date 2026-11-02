"""S-cm-3: OTOC fidelity vs classical reference within 5%.

The Phase-1 quantum kernel is a placeholder that returns the
classical reference unchanged, so the fidelity is exactly 1. This
test pins the structural shape: the OTOC magnitude is recorded in
the classical metadata and the dispatcher returns it.
"""

from __future__ import annotations

from qfull_cm import CondMatProblem, compute_reference


def test_otoc_classical_reference_records_magnitude(
    otoc_problem: CondMatProblem,
) -> None:
    outcome = compute_reference(otoc_problem)
    assert outcome["method_used"] == "otoc_dense"
    meta = outcome["metadata"]
    assert "otoc_magnitude" in meta
    # OTOC magnitude is bounded ∈ [0, ⟨V V†⟩] = [0, ∞) for general V;
    # for σ^z (eigenvalue ±1/2) we expect O(1).
    assert 0.0 <= meta["otoc_magnitude"] < 10.0
    assert meta["L"] == 8
