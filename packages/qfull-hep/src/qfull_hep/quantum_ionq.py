"""IonQ Forte path for HEP via Amazon Braket SDK (lazy import)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .classical import compute_reference
from .manifest import HEPProblem


@dataclass
class IonQOutcome:
    quantum_energy: float
    classical_energy: float
    classical_hash: str
    classical_method: str
    classical_warning: str | None
    metadata: dict[str, Any]


def run_ionq(problem: HEPProblem) -> IonQOutcome:
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


def _run_kernel(problem: HEPProblem) -> tuple[float, dict[str, Any]]:
    try:
        import braket  # type: ignore[import-not-found]  # noqa: F401
    except ImportError as exc:
        msg = "IonQ path requires amazon-braket-sdk; install qfull-hep[ionq]."
        raise ImportError(msg) from exc
    classical = compute_reference(problem)
    return classical["energy"], {
        "kernel": "phase1_placeholder_ionq",
        "kind": problem.kind,
        "shots": problem.shots,
    }
