"""S-cm-1: Hubbard 4×4 reference round-trip.

The dense-ED ceiling for Hubbard is 8 sites; 4×4 (=16 sites) is
beyond it. This audit accepts that the path raises a clear
``ClassicalReferenceError`` (DMRG via tenpy is the planned backend).
The structural check is that the dispatcher returns *something* for
small Hubbard instances — we exercise a 1×4 chain to validate.
"""

from __future__ import annotations

import pytest

from qcompass_core.errors import ClassicalReferenceError
from qfull_cm import CondMatProblem, HubbardParams, compute_reference


def test_hubbard_4x4_raises_above_ed_ceiling() -> None:
    problem = CondMatProblem(
        kind="hubbard",
        backend_preference="classical",
        hubbard=HubbardParams(L=(4, 4), U=4.0, t=1.0),
    )
    with pytest.raises(ClassicalReferenceError, match="exceeds ED ceiling"):
        compute_reference(problem)


def test_hubbard_small_returns_finite_energy() -> None:
    problem = CondMatProblem(
        kind="hubbard",
        backend_preference="classical",
        hubbard=HubbardParams(L=(1, 4), U=4.0, t=1.0),
    )
    outcome = compute_reference(problem)
    assert outcome["method_used"] == "exact_diag"
    assert outcome["metadata"]["filling"] == "half"
    # The simplified ED kernel is bounded: E_min >= -2 t L for any U.
    assert outcome["energy"] >= -2.0 * 1.0 * 4 - 1e-9
