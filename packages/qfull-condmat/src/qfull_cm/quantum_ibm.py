"""IBM Heron (digital) execution path for condmat.

Lazy-imports ``qiskit`` + ``qiskit_ibm_runtime``. The actual circuit
construction for Hubbard / Heisenberg / OTOC ansätze lands in
Phase 2; this module ships the dispatch shape so the audit
exercises every code path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .classical import compute_reference
from .manifest import CondMatProblem


@dataclass
class IBMOutcome:
    quantum_energy: float
    classical_energy: float
    classical_hash: str
    classical_method: str
    classical_warning: str | None
    metadata: dict[str, Any]


def run_ibm(problem: CondMatProblem) -> IBMOutcome:
    """Execute the condmat problem on IBM Heron (or Aer noise-free).

    Always pairs with a classical reference so the audit can attach
    `classical_reference_hash` to the provenance record.
    """
    classical = compute_reference(problem)
    energy, meta = _run_kernel(problem)
    return IBMOutcome(
        quantum_energy=energy,
        classical_energy=classical["energy"],
        classical_hash=classical["hash"],
        classical_method=classical["method_used"],
        classical_warning=classical["warning"],
        metadata={"ibm": meta, "classical": classical["metadata"]},
    )


def _run_kernel(problem: CondMatProblem) -> tuple[float, dict[str, Any]]:
    try:
        import qiskit  # noqa: F401
        import qiskit_aer  # noqa: F401
    except ImportError as exc:
        msg = (
            "IBM path requires qiskit + qiskit-aer; install via "
            "qfull-condmat[ibm]."
        )
        raise ImportError(msg) from exc

    # Phase-1 kernel: returns the classical energy as a placeholder
    # so the dispatch shape is exercisable end-to-end. Phase-2 wires
    # a real VQE / hardware-efficient ansatz.
    classical = compute_reference(problem)
    return classical["energy"], {
        "kernel": "phase1_placeholder",
        "kind": problem.kind,
        "shots": problem.shots,
    }
