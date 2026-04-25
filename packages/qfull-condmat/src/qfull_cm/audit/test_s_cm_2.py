"""S-cm-2: Heisenberg L=10 ED matches the canonical ground state.

Bethe-ansatz limit for the isotropic chain: −0.4438 per site;
finite-size open boundaries shift this slightly. We assert the
energy-per-site is in [-0.50, -0.40] (well-known band for L=10).
"""

from __future__ import annotations

from qfull_cm import CondMatProblem, compute_reference


def test_heisenberg_chain_10_in_band(heisenberg_problem: CondMatProblem) -> None:
    outcome = compute_reference(heisenberg_problem)
    assert outcome["method_used"] == "exact_diag"
    assert outcome["warning"] is None
    eps = outcome["metadata"]["energy_per_site"]
    assert -0.50 < eps < -0.40, (
        f"Heisenberg L=10 energy/site out of band: {eps}"
    )
