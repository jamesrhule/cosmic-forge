"""Circuit transforms (qiskit-addon-* wrappers).

Every transform soft-imports its qiskit addon. When the addon (or qiskit
itself) is missing, `apply()` returns the input circuit unchanged with a
TransformRecord whose `depth_before == depth_after`. The router treats
this as a graceful no-op.
"""

from __future__ import annotations

from typing import Any

from qcompass_router.transforms.aqc_tensor import apply as apply_aqc_tensor
from qcompass_router.transforms.cutting import apply as apply_cutting
from qcompass_router.transforms.mpf import apply as apply_mpf
from qcompass_router.transforms.obp import apply as apply_obp
from qcompass_router.transforms.record import TransformName, TransformRecord

_REGISTRY = {
    "aqc_tensor": apply_aqc_tensor,
    "mpf": apply_mpf,
    "obp": apply_obp,
    "cutting": apply_cutting,
}


def apply_transforms(
    circuit: Any,
    names: list[str],
    **kwargs: Any,
) -> tuple[Any, list[TransformRecord]]:
    """Run the named transforms in order, threading the circuit through.

    Unknown names raise `ValueError`. Per-transform kwargs are passed
    through `kwargs[<name>]` (a sub-dict).
    """
    records: list[TransformRecord] = []
    current = circuit
    for name in names:
        fn = _REGISTRY.get(name)
        if fn is None:
            raise ValueError(
                f"unknown transform {name!r}; valid: {sorted(_REGISTRY)}"
            )
        per_kwargs = kwargs.get(name) or {}
        current, record = fn(current, **per_kwargs)
        records.append(record)
    return current, records


__all__ = [
    "TransformName",
    "TransformRecord",
    "apply_transforms",
]
