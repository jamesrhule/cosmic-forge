"""S-nuc-1: 0νββ toy L=4 dense ED returns finite, deterministic energy."""

from __future__ import annotations

from qfull_nuc import NuclearProblem, compute_reference


def test_zero_nu_bb_l4_ground_state(zero_nu_bb_l4: NuclearProblem) -> None:
    a = compute_reference(zero_nu_bb_l4)
    b = compute_reference(zero_nu_bb_l4)
    # Determinism (numpy.linalg.eigvalsh is exact-ish, identical inputs
    # yield identical outputs to FP precision).
    assert abs(a["energy"] - b["energy"]) < 1e-10
    assert a["method_used"] == "zero_nu_bb_ed"
    # 1+1D toy must always carry the model_domain tag.
    assert a["metadata"]["model_domain"] == "1+1D_toy"
