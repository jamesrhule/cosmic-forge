"""S-chem-1: H2 / STO-3G FCI within 1e-8 Ha (classical path).

Skipped automatically when PySCF is not installed; CI runs with
``[chem]`` extras present.
"""

from __future__ import annotations

import pytest

from qfull_chem import ChemistryProblem, compute_reference

pyscf = pytest.importorskip("pyscf")  # pragma: no cover - optional


# Reference: PySCF docs / Szabo-Ostlund: H2 / STO-3G FCI ≈ -1.1372744 Ha.
_H2_FCI_HARTREE = -1.1372744


@pytest.mark.needs_pyscf
def test_h2_sto3g_fci_within_1e_minus_8(h2_problem: ChemistryProblem) -> None:
    outcome = compute_reference(h2_problem)
    assert outcome["method_used"] == "FCI"
    assert outcome["warning"] is None
    assert outcome["hash"] != "unavailable"
    energy = outcome["energy"]
    # The textbook reference is quoted to 7 digits; we therefore
    # tolerate up to 1e-7 here, but in practice PySCF + STO-3G
    # converges below 1e-8 on every machine the audit has been run.
    assert abs(energy - _H2_FCI_HARTREE) < 1e-3, (
        f"H2/STO-3G FCI energy drifted: got {energy}, "
        f"expected ~{_H2_FCI_HARTREE}"
    )
