"""qiskit-addon-cutting wrapper (lazy import)."""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord
from ._common import call_first, run_addon_transform


def apply_cutting(
    circuit: Any,
    *,
    max_subcircuit_width: int = 8,
    **addon_kwargs: Any,
) -> tuple[Any, TransformRecord]:
    """Circuit cutting via qiskit-addon-cutting."""
    return run_addon_transform(
        "cutting",
        circuit,
        {"max_subcircuit_width": max_subcircuit_width, **addon_kwargs},
        module="qiskit_addon_cutting",
        call=call_first("cut_wires", "cut_circuit_wires", kwargs=addon_kwargs),
    )


def apply(circuit: Any, **kwargs: Any) -> tuple[Any, TransformRecord]:
    """6B module-level entry point; extra kwargs go to the addon."""
    return apply_cutting(circuit, **kwargs)
