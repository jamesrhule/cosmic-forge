"""S-cm-4: OTOC chain-length feasibility flag.

The classical OTOC reference uses dense matrices and is bounded at
L=12. Asking for L>12 must raise a clear `ClassicalReferenceError`
that surfaces "exceeds dense-matrix limit". The dispatcher (sim.py)
relays this so the agent can choose between shrinking the chain or
moving to the netket NQS path (Phase 2).
"""

from __future__ import annotations

import pytest

from qcompass_core.errors import ClassicalReferenceError
from qfull_cm import CondMatProblem, OtocParams, compute_reference


def test_otoc_l_12_runs() -> None:
    p = CondMatProblem(
        kind="otoc",
        backend_preference="classical",
        otoc=OtocParams(L=12, n_steps=2, dt=0.1),
    )
    outcome = compute_reference(p)
    assert outcome["metadata"]["L"] == 12


def test_otoc_l_above_ceiling_raises() -> None:
    p = CondMatProblem(
        kind="otoc",
        backend_preference="classical",
        otoc=OtocParams(L=14, n_steps=2, dt=0.1),
    )
    with pytest.raises(ClassicalReferenceError, match="exceeds dense-matrix"):
        compute_reference(p)
