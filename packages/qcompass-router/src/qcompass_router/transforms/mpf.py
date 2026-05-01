"""qiskit-addon-mpf wrapper (lazy import)."""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord


def apply_mpf(
    circuit: Any,
    *,
    order: int = 4,
) -> tuple[Any, TransformRecord]:
    """Multi-product formula expansion. Phase-1: contract-only."""
    parameters = {"order": order}
    try:
        import qiskit_addon_mpf as mpf  # type: ignore[import-not-found]
    except ImportError:
        return circuit, TransformRecord(
            name="mpf",
            parameters=parameters,
            notes="SDK absent — pass-through.",
        )
    _ = mpf
    return circuit, TransformRecord(
        name="mpf",
        parameters=parameters,
        notes="mpf SDK importable; numerics wired in PROMPT 6C.",
    )
