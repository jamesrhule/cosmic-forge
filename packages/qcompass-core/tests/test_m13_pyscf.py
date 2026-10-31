"""M13 PySCF adapter test.

Skipped when PySCF is not installed. Validates that H2 / STO-3G FCI
matches the textbook value to within chemical accuracy (1 mHa).
"""

from __future__ import annotations

import pytest

from qcompass_core import ClassicalReferenceError, PySCFAdapter

pyscf = pytest.importorskip("pyscf")  # pragma: no cover - optional


# Reference: PySCF docs / Szabo-Ostlund: H2 / STO-3G FCI ≈ -1.137270 Hartree.
_H2_FCI_HARTREE = -1.1372744


def test_h2_sto3g_fci_matches_reference() -> None:
    adapter = PySCFAdapter()
    out = adapter.compute({
        "atom": "H 0 0 0; H 0 0 0.74",
        "basis": "sto-3g",
        "method": "fci",
    })
    assert out["metadata"]["method"] == "FCI"
    assert abs(out["energy"] - _H2_FCI_HARTREE) < 1e-3


def test_pyscf_adapter_requires_atom() -> None:
    with pytest.raises(ClassicalReferenceError):
        PySCFAdapter().compute({"basis": "sto-3g"})
