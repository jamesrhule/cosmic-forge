"""bloqade-analog (QuEra Aquila / Braket) path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .classical import compute_reference
from .manifest import AMOProblem


@dataclass
class AnalogOutcome:
    quantum_energy: float
    classical_energy: float
    classical_hash: str
    classical_method: str
    classical_warning: str | None
    metadata: dict[str, Any]


def run_analog(problem: AMOProblem) -> AnalogOutcome:
    classical = compute_reference(problem)
    energy, meta = _run_kernel(problem)
    return AnalogOutcome(
        quantum_energy=energy,
        classical_energy=classical["energy"],
        classical_hash=classical["hash"],
        classical_method=classical["method_used"],
        classical_warning=classical["warning"],
        metadata={"analog": meta, "classical": classical["metadata"]},
    )


def _run_kernel(problem: AMOProblem) -> tuple[float, dict[str, Any]]:
    try:
        import bloqade_analog  # type: ignore[import-not-found]  # noqa: F401
    except ImportError as exc:
        msg = "Analog path requires qfull-amo[bloqade_analog]."
        raise ImportError(msg) from exc
    classical = compute_reference(problem)
    return classical["energy"], {
        "kernel": "phase1_placeholder_analog",
        "kind": problem.kind,
        "shots": problem.shots,
    }
