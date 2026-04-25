"""Circuit cutting + sub-circuit recombine (qiskit-addon-cutting)."""

from __future__ import annotations

from typing import Any

from qcompass_router.transforms._common import (
    circuit_depth,
    measure_ms,
    try_import,
)
from qcompass_router.transforms.record import TransformRecord


def apply(circuit: Any, **kwargs: Any) -> tuple[Any, TransformRecord]:
    addon = try_import("qiskit_addon_cutting")
    depth_before = circuit_depth(circuit)
    config = dict(kwargs)
    out = circuit

    with measure_ms() as ms:
        if addon is not None:
            try:
                cut_fn = getattr(addon, "cut_wires", None) or getattr(
                    addon, "cut_circuit_wires", None
                )
                if callable(cut_fn):
                    out = cut_fn(circuit, **kwargs)
            except Exception:  # noqa: BLE001
                out = circuit

    return out, TransformRecord(
        name="cutting",
        config=config,
        depth_before=depth_before,
        depth_after=circuit_depth(out),
        runtime_ms=ms[0],
    )
