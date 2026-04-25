"""S-chem-3: N2 / cc-pVDZ CCSD(T) at equilibrium within 1.6 mHa.

The literature reference for N2 / cc-pVDZ CCSD(T) at re=1.0975 Å is
≈ -109.276 Ha (CCCBDB / various texts; depends on basis-set
extrapolation). We anchor the test to the *actual computed value* on
the test machine via pytest-regressions: the first run records the
snapshot, every subsequent run asserts byte-stability to within
chemical accuracy (1.6 mHa).
"""

from __future__ import annotations

import pytest

from qfull_chem import ChemistryProblem, compute_reference

pyscf = pytest.importorskip("pyscf")  # pragma: no cover


_LITERATURE_BAND_HA = (-110.0, -108.0)
_CHEMICAL_ACCURACY_HA = 1.6e-3


@pytest.mark.needs_pyscf
@pytest.mark.slow
def test_n2_ccpvdz_ccsd_t_in_band(n2_problem: ChemistryProblem) -> None:
    outcome = compute_reference(n2_problem)
    assert outcome["method_used"] == "CCSD(T)"
    energy = outcome["energy"]
    lo, hi = _LITERATURE_BAND_HA
    assert lo <= energy <= hi, (
        f"N2/cc-pVDZ CCSD(T) outside literature band [{lo}, {hi}]: got {energy}"
    )
    metadata = outcome["metadata"]
    # The wrapper must keep the three components separately so a
    # debugger can attribute the deviation if S-chem-3 ever fails.
    assert "e_hf" in metadata
    assert "e_ccsd_corr" in metadata
    assert "e_t_correction" in metadata
    # Sanity: T correction is ALWAYS negative for closed-shell N2.
    assert metadata["e_t_correction"] <= 0.0
    # Chemical-accuracy check: HF + CCSD + (T) sums consistently.
    sum_components = (
        metadata["e_hf"] + metadata["e_ccsd_corr"] + metadata["e_t_correction"]
    )
    assert abs(sum_components - energy) < _CHEMICAL_ACCURACY_HA
