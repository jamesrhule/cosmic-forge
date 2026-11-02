"""IBM Heron fallback path for nuclear."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .classical import compute_reference
from .manifest import NuclearProblem


@dataclass
class IBMOutcome:
    quantum_energy: float
    classical_energy: float
    classical_hash: str
    classical_method: str
    classical_warning: str | None
    metadata: dict[str, Any]


def run_ibm(problem: NuclearProblem) -> IBMOutcome:
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


def _run_kernel(problem: NuclearProblem) -> tuple[float, dict[str, Any]]:
    try:
        import qiskit  # noqa: F401
        import qiskit_aer  # noqa: F401
    except ImportError as exc:
        msg = "IBM path requires qfull-nuclear[ibm]."
        raise ImportError(msg) from exc
    classical = compute_reference(problem)
    return classical["energy"], {
        "kernel": "phase1_placeholder_ibm",
        "kind": problem.kind,
        "shots": problem.shots,
    }
