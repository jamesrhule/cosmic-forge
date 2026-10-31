"""qiskit-addon-cutting wrapper (lazy import)."""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord
from ._common import call_first, run_addon_transform


def apply_cutting(
    circuit: Any,
    *,
    max_subcircuit_width: int = 8,
) -> tuple[Any, TransformRecord]:
    """Circuit cutting via qiskit-addon-cutting."""
    return run_addon_transform(
        "cutting",
        circuit,
        {"max_subcircuit_width": max_subcircuit_width},
        module="qiskit_addon_cutting",
        call=call_first("cut_wires", "cut_circuit_wires"),
    )
