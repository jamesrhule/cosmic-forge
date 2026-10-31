"""qiskit-addon-obp wrapper (lazy import)."""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord
from ._common import call_first, run_addon_transform


def apply_obp(
    circuit: Any,
    *,
    threshold: float = 1e-3,
) -> tuple[Any, TransformRecord]:
    """Operator backpropagation via qiskit-addon-obp."""
    return run_addon_transform(
        "obp",
        circuit,
        {"threshold": threshold},
        module="qiskit_addon_obp",
        call=call_first("backpropagate"),
    )
