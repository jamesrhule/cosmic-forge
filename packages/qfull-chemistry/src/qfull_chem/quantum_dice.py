"""Dice-SHCI execution path.

``qiskit-addon-dice-solver`` is a thin wrapper around the
proprietary Dice binary that ships only for Linux. The package's
``[dice]`` extra is gated on ``sys_platform == 'linux'``; on
macOS / Windows the SDK is simply absent.

Public entries here check :func:`platform.system` first so the
caller fails fast with a clear message rather than mid-import.
Tests that exercise this path carry both ``pytest.importorskip``
and ``pytest.mark.skipif(platform.system() == "Darwin")``.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import Any

from .classical import compute_reference
from .manifest import ChemistryProblem


@dataclass
class DiceOutcome:
    """Output of :func:`run_dice`."""

    dice_energy: float
    classical_energy: float
    classical_hash: str
    classical_method: str
    classical_warning: str | None
    metadata: dict[str, Any]


def is_dice_available() -> bool:
    """Returns True iff the platform CAN run the Dice path.

    The actual SDK presence is verified by
    :func:`pytest.importorskip` in the audit tests; this helper only
    enforces the platform invariant.
    """
    return platform.system() == "Linux"


def run_dice(problem: ChemistryProblem) -> DiceOutcome:
    """Run a Dice-SHCI path and pair it with a classical reference.

    Raises :class:`RuntimeError` when called on a non-Linux platform
    (the addon's binary backend is Linux-only).
    """
    if not is_dice_available():
        msg = (
            "qiskit-addon-dice-solver is Linux-only "
            f"(detected platform={platform.system()!r}); "
            "use the SQD path instead, or move the workload to a "
            "Linux runner."
        )
        raise RuntimeError(msg)

    classical = compute_reference(problem)
    energy_dice, dice_meta = _run_dice_kernel(problem)
    return DiceOutcome(
        dice_energy=energy_dice,
        classical_energy=classical["energy"],
        classical_hash=classical["hash"],
        classical_method=classical["method_used"],
        classical_warning=classical["warning"],
        metadata={
            "dice": dice_meta,
            "classical": classical["metadata"],
        },
    )


def _run_dice_kernel(problem: ChemistryProblem) -> tuple[float, dict[str, Any]]:
    """Lazy import of the Dice SDK + return a placeholder energy.

    The actual SHCI invocation is intentionally not wired in this
    Phase-1 plugin; we only confirm the SDK loads (so the entry path
    is reachable) and round-trip the manifest. Phase-2 plugs in the
    real solver.
    """
    try:
        import qiskit_addon_dice_solver  # noqa: F401  (proves SDK is present)
    except ImportError as exc:
        msg = (
            "qiskit-addon-dice-solver is not installed; install "
            "qfull-chemistry[dice] (Linux only)."
        )
        raise ImportError(msg) from exc

    # Placeholder until the real Dice driver lands. The classical
    # pairing carries the audit weight.
    return float("nan"), {
        "solver": "qiskit_addon_dice_solver (placeholder)",
        "molecule": problem.molecule,
        "basis": problem.basis,
        "active_space": list(problem.active_space) if problem.active_space else None,
    }
