"""Classical-path smoke tests independent of S-chem-* numerics."""

from __future__ import annotations

import math

import pytest

from qfull_chem import compute_reference, load_instance
from qfull_chem.classical import ClassicalOutcome


def test_femoco_returns_unavailable_sentinel() -> None:
    """The FeMoco-toy path must NOT crash even without integrals."""
    problem = load_instance("femoco_toy")
    outcome: ClassicalOutcome = compute_reference(problem)
    assert outcome["hash"] == "unavailable"
    assert outcome["warning"] == "no_classical_reference"
    assert math.isnan(outcome["energy"])
    assert outcome["method_used"] == "unavailable"


@pytest.mark.needs_pyscf
def test_h2_classical_path_round_trips() -> None:
    pytest.importorskip("pyscf")
    outcome = compute_reference(load_instance("h2"))
    assert outcome["method_used"] == "FCI"
    assert math.isfinite(outcome["energy"])
    assert outcome["hash"] != "unavailable"
    assert outcome["warning"] is None
