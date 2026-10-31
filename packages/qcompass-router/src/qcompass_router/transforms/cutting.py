"""qiskit-addon-cutting wrapper (lazy import)."""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord


def apply_cutting(
    circuit: Any,
    *,
    max_subcircuit_width: int = 8,
) -> tuple[Any, TransformRecord]:
    """Circuit cutting via qiskit-addon-cutting. Phase-1: contract-only."""
    parameters = {"max_subcircuit_width": max_subcircuit_width}
    try:
        import qiskit_addon_cutting as cutting  # type: ignore[import-not-found]
    except ImportError:
        return circuit, TransformRecord(
            name="cutting",
            parameters=parameters,
            notes="SDK absent — pass-through.",
        )
    _ = cutting
    return circuit, TransformRecord(
        name="cutting",
        parameters=parameters,
        notes="cutting SDK importable; numerics wired in PROMPT 6C.",
    )
