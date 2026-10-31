"""qiskit-addon-mpf wrapper (lazy import)."""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord
from ._common import call_first, run_addon_transform


def apply_mpf(
    circuit: Any,
    *,
    order: int = 4,
) -> tuple[Any, TransformRecord]:
    """Multi-product formula expansion via qiskit-addon-mpf."""
    return run_addon_transform(
        "mpf",
        circuit,
        {"order": order},
        module="qiskit_addon_mpf",
        call=call_first("trotter_circuit"),
    )
