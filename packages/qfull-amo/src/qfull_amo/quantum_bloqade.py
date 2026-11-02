"""bloqade (digital) execution path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .classical import compute_reference
from .manifest import AMOProblem


@dataclass
class BloqadeOutcome:
    quantum_energy: float
    classical_energy: float
    classical_hash: str
    classical_method: str
    classical_warning: str | None
    metadata: dict[str, Any]


def run_bloqade(problem: AMOProblem) -> BloqadeOutcome:
    classical = compute_reference(problem)
    energy, meta = _run_kernel(problem)
    return BloqadeOutcome(
        quantum_energy=energy,
        classical_energy=classical["energy"],
        classical_hash=classical["hash"],
        classical_method=classical["method_used"],
        classical_warning=classical["warning"],
        metadata={"bloqade": meta, "classical": classical["metadata"]},
    )


def _run_kernel(problem: AMOProblem) -> tuple[float, dict[str, Any]]:
    try:
        import bloqade  # type: ignore[import-not-found]  # noqa: F401
    except ImportError as exc:
        msg = "bloqade path requires qfull-amo[bloqade_digital]."
        raise ImportError(msg) from exc
    classical = compute_reference(problem)
    return classical["energy"], {
        "kernel": "phase1_placeholder_bloqade",
        "kind": problem.kind,
    }
