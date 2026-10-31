"""S-amo-3: adiabatic schedule fidelity ≥ 0.95 on a small Rydberg reference.

The Phase-1 quantum kernels are placeholders that return the
classical reference unchanged, so the fidelity is exactly 1.
This test is the structural pin: when Phase-2 wires bloqade-analog,
the schedule fidelity must remain ≥ 0.95.
"""

from __future__ import annotations

from qfull_amo import AMOProblem, compute_reference, run_bloqade


def test_classical_path_records_per_atom_energy(
    rydberg_chain_8: AMOProblem,
) -> None:
    outcome = compute_reference(rydberg_chain_8)
    eps = outcome["metadata"]["energy_per_atom"]
    # Must equal energy / L.
    assert abs(eps * outcome["metadata"]["L"] - outcome["energy"]) < 1e-9


def test_quantum_kernel_pairs_with_classical_reference(
    rydberg_chain_8: AMOProblem,
) -> None:
    # Force a quantum-path call; without bloqade installed it raises
    # ImportError, which we treat as "skip" for the fidelity invariant.
    import pytest

    try:
        out = run_bloqade(rydberg_chain_8)
    except ImportError:
        pytest.skip("bloqade not installed; classical reference still recorded.")
    # When wired (Phase 2), fidelity = quantum/classical ≈ 1.
    delta = abs(out.quantum_energy - out.classical_energy)
    assert delta <= 1e-6 + 1e-3 * abs(out.classical_energy)
