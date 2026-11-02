"""S-chem-4: H2 SQD on noise-free Aer recovers FCI to within 1e-6 Ha.

Skipped on Darwin (the qiskit-addon-dice-solver chain occasionally
pulls a Linux-only transitive in some lockfiles; SQD itself is
cross-platform but we mark Darwin as the safe-skip signal until CI
gives us a clean macOS run).
"""

from __future__ import annotations

import platform

import pytest

from qfull_chem import ChemistryProblem, run_sqd

pyscf = pytest.importorskip("pyscf")  # pragma: no cover
qiskit_addon_sqd = pytest.importorskip("qiskit_addon_sqd")  # pragma: no cover


@pytest.mark.needs_sqd
@pytest.mark.skipif(
    platform.system() == "Darwin",
    reason="SQD path skipped on Darwin to dodge Dice transitive lockfile issues.",
)
def test_h2_sqd_within_chemical_accuracy(h2_problem: ChemistryProblem) -> None:
    outcome = run_sqd(h2_problem)
    # Phase-1 SQD kernel uses a noise-free FCI projection; the
    # tolerance MUST be tight enough to detect any future drift but
    # generous enough to absorb floating-point variation.
    assert abs(outcome.sqd_energy - outcome.classical_energy) < 1e-6, (
        f"SQD ({outcome.sqd_energy}) deviates from FCI "
        f"({outcome.classical_energy}) by more than 1e-6 Ha."
    )
    assert outcome.classical_method == "FCI"
    assert outcome.classical_warning is None
    assert outcome.classical_hash != "unavailable"
