"""qiskit-addon-obp wrapper (lazy import)."""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord
from ._common import call_first, run_addon_transform


def apply_obp(
    circuit: Any,
    *,
    threshold: float = 1e-3,
    **addon_kwargs: Any,
) -> tuple[Any, TransformRecord]:
    """Operator backpropagation via qiskit-addon-obp."""
    return run_addon_transform(
        "obp",
        circuit,
        {"threshold": threshold, **addon_kwargs},
        module="qiskit_addon_obp",
        call=call_first("backpropagate", kwargs=addon_kwargs),
    )


def apply(circuit: Any, **kwargs: Any) -> tuple[Any, TransformRecord]:
    """6B module-level entry point; extra kwargs go to the addon."""
    return apply_obp(circuit, **kwargs)
