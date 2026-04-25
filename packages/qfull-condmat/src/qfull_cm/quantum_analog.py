"""QuEra Aquila (analog) execution path for condmat.

Lazy-imports ``bloqade-analog``. The analog path is best-suited for
spin-system Hamiltonians; we route Heisenberg / frustrated /
OTOC problems through the analog backend when requested. Hubbard
(electronic) goes through the digital path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .classical import compute_reference
from .manifest import CondMatProblem


@dataclass
class AnalogOutcome:
    analog_energy: float
    classical_energy: float
    classical_hash: str
    classical_method: str
    classical_warning: str | None
    metadata: dict[str, Any]


def run_analog(problem: CondMatProblem) -> AnalogOutcome:
    if problem.kind == "hubbard":
        msg = (
            "Hubbard problems are not natively analog-mapped; "
            "use backend_preference='ibm' or 'classical'."
        )
        raise ValueError(msg)
    classical = compute_reference(problem)
    energy, meta = _run_kernel(problem)
    return AnalogOutcome(
        analog_energy=energy,
        classical_energy=classical["energy"],
        classical_hash=classical["hash"],
        classical_method=classical["method_used"],
        classical_warning=classical["warning"],
        metadata={"analog": meta, "classical": classical["metadata"]},
    )


def _run_kernel(problem: CondMatProblem) -> tuple[float, dict[str, Any]]:
    try:
        import bloqade  # type: ignore[import-not-found]
    except ImportError as exc:
        msg = (
            "Analog path requires bloqade-analog; install via "
            "qfull-condmat[analog]."
        )
        raise ImportError(msg) from exc
    _ = bloqade
    classical = compute_reference(problem)
    return classical["energy"], {
        "kernel": "phase1_placeholder_analog",
        "kind": problem.kind,
        "shots": problem.shots,
    }
