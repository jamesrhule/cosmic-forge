"""qiskit-addon-obp wrapper (lazy import)."""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord


def apply_obp(
    circuit: Any,
    *,
    threshold: float = 1e-3,
) -> tuple[Any, TransformRecord]:
    """Operator backpropagation. Phase-1: contract-only."""
    parameters = {"threshold": threshold}
    try:
        import qiskit_addon_obp as obp  # type: ignore[import-not-found]
    except ImportError:
        return circuit, TransformRecord(
            name="obp",
            parameters=parameters,
            notes="SDK absent — pass-through.",
        )
    _ = obp
    return circuit, TransformRecord(
        name="obp",
        parameters=parameters,
        notes="obp SDK importable; numerics wired in PROMPT 6C.",
    )
