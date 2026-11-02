"""S-hep-2: ground-state energy decreases with L (string-tension monotonicity)."""

from __future__ import annotations

from qfull_hep import HEPProblem, compute_reference


def test_energy_monotone_with_size(
    schwinger_l4: HEPProblem,
    schwinger_l6: HEPProblem,
) -> None:
    e4 = compute_reference(schwinger_l4)["energy"]
    e6 = compute_reference(schwinger_l6)["energy"]
    # The Schwinger ground state extensively scales with L, so for
    # fixed coupling/mass the L=6 energy should be lower (more
    # negative) than L=4. This is the lightweight stand-in for the
    # full string-tension scaling check.
    assert e6 <= e4 + 1e-6, (
        f"Schwinger ground-state should not rise with L: "
        f"E(L=4)={e4}, E(L=6)={e6}"
    )
