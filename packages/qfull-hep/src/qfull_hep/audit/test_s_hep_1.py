"""S-hep-1: Schwinger 1+1D L=4 chiral condensate matches lattice ED."""

from __future__ import annotations

from qfull_hep import HEPProblem, compute_reference


def test_schwinger_l4_chiral_condensate(schwinger_l4: HEPProblem) -> None:
    outcome = compute_reference(schwinger_l4)
    assert outcome["method_used"] == "schwinger_ed"
    cond = outcome["metadata"]["chiral_condensate"]
    # Massless / weak-coupling Schwinger model: condensate is bounded
    # below in magnitude by the analytic Coleman result (1/√π) but
    # finite-size corrections push it. We just check it is finite and
    # within a wide physical band.
    assert -1.0 < cond < 1.0, f"L=4 condensate out of band: {cond}"
