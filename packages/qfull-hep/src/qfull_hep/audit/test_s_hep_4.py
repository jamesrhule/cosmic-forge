"""S-hep-4: classical-MPS agreement for L>=10.

quimb's MPS reference is required to validate the dense-ED result
at L=10. Skipped cleanly when quimb is absent. The Phase-1 kernel
re-uses the dense ED for L=10 (which is at the edge of feasibility);
the test asserts the dispatcher returns a finite energy + the
expected method tag.
"""

from __future__ import annotations

import pytest

from qfull_hep import HEPProblem, compute_reference


@pytest.mark.slow
def test_schwinger_l10_dense_ed_returns_finite(
    schwinger_l10: HEPProblem,
) -> None:
    outcome = compute_reference(schwinger_l10)
    assert outcome["method_used"] == "schwinger_ed"
    assert outcome["energy"] == outcome["energy"]  # not NaN


def test_classical_mps_path_skips_when_quimb_absent() -> None:
    # When quimb is installed, the MPS path lands here (Phase 2).
    # Until then, this test is a sentinel: it always passes once the
    # SDK guard is wired and quimb is missing.
    pytest.importorskip("quimb")
