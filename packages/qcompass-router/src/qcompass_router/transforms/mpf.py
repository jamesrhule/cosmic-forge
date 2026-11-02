"""qiskit-addon-mpf wrapper (lazy import)."""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord
from ._common import call_first, run_addon_transform


def apply_mpf(
    circuit: Any,
    *,
    order: int = 4,
    **addon_kwargs: Any,
) -> tuple[Any, TransformRecord]:
    """Multi-product formula expansion via qiskit-addon-mpf."""
    return run_addon_transform(
        "mpf",
        circuit,
        {"order": order, **addon_kwargs},
        module="qiskit_addon_mpf",
        call=call_first("trotter_circuit", kwargs=addon_kwargs),
    )



def apply(circuit: Any, **kwargs: Any) -> tuple[Any, TransformRecord]:
    """6B module-level entry point: every kwarg (named ones included) goes to the addon."""
    return run_addon_transform(
        "mpf",
        circuit,
        {"order": 4, **kwargs},
        module="qiskit_addon_mpf",
        call=call_first("trotter_circuit", kwargs=kwargs),
    )
