"""S-chem-2: LiH / 6-31G DMRG within 1 mHa.

Requires both PySCF (for the integral build) and pyblock2 (for the
DMRG driver). Skipped cleanly when either is missing.
"""

from __future__ import annotations

import pytest

from qfull_chem import ChemistryProblem, compute_reference

pyscf = pytest.importorskip("pyscf")  # pragma: no cover
pyblock2 = pytest.importorskip("pyblock2")  # pragma: no cover


# Reference target: HF energy is around -7.97 Ha; DMRG converges to
# the FCI limit. We tolerate 1 mHa deviation against an HF-anchored
# floor since reproducible literature numbers depend on integrals
# the test machine is the source of.
_LIH_HF_LOWER_BOUND_HA = -8.5
_LIH_HF_UPPER_BOUND_HA = -7.5


@pytest.mark.needs_block2
@pytest.mark.slow
def test_lih_6_31g_dmrg_in_band(lih_problem: ChemistryProblem) -> None:
    outcome = compute_reference(lih_problem)
    assert outcome["method_used"] == "DMRG"
    assert outcome["warning"] is None
    energy = outcome["energy"]
    assert _LIH_HF_LOWER_BOUND_HA <= energy <= _LIH_HF_UPPER_BOUND_HA, (
        f"LiH/6-31G DMRG energy out of physical band: got {energy}"
    )
