"""IonQ Forte (preferred quantum path for nuclear)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .classical import compute_reference
from .manifest import NuclearProblem


@dataclass
class IonQOutcome:
    quantum_energy: float
    classical_energy: float
    classical_hash: str
    classical_method: str
    classical_warning: str | None
    metadata: dict[str, Any]


def run_ionq(problem: NuclearProblem) -> IonQOutcome:
    classical = compute_reference(problem)
    energy, meta = _run_kernel(problem)
    return IonQOutcome(
        quantum_energy=energy,
        classical_energy=classical["energy"],
        classical_hash=classical["hash"],
        classical_method=classical["method_used"],
        classical_warning=classical["warning"],
        metadata={"ionq": meta, "classical": classical["metadata"]},
    )


def _run_kernel(problem: NuclearProblem) -> tuple[float, dict[str, Any]]:
    try:
        import braket  # type: ignore[import-not-found]  # noqa: F401
    except ImportError as exc:
        msg = "IonQ path requires qfull-nuclear[ionq]."
        raise ImportError(msg) from exc
    classical = compute_reference(problem)
    return classical["energy"], {
        "kernel": "phase1_placeholder",
        "kind": problem.kind,
        "shots": problem.shots,
    }
