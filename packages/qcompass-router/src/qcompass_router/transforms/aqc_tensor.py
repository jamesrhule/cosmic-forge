"""Approximate quantum compilation via tensor-network state-fidelity
maximisation (qiskit-addon-aqc-tensor).

No-op when the addon is unavailable.
"""

from __future__ import annotations

from typing import Any

from qcompass_router.transforms._common import (
    circuit_depth,
    measure_ms,
    try_import,
)
from qcompass_router.transforms.record import TransformRecord


def apply(circuit: Any, **kwargs: Any) -> tuple[Any, TransformRecord]:
    addon = try_import("qiskit_addon_aqc_tensor")
    depth_before = circuit_depth(circuit)
    config = dict(kwargs)
    out = circuit

    with measure_ms() as ms:
        if addon is not None:
            try:
                MaximizeStateFidelity = getattr(  # noqa: N806
                    addon, "MaximizeStateFidelity", None
                )
                generate_ansatz = getattr(addon, "generate_ansatz_from_circuit", None)
                if generate_ansatz is not None and MaximizeStateFidelity is not None:
                    target = generate_ansatz(circuit)
                    objective = MaximizeStateFidelity(target=target, ansatz=circuit)
                    optimised = getattr(addon, "optimise", None)
                    if callable(optimised):
                        out = optimised(objective, **kwargs)
            except Exception:  # noqa: BLE001 — graceful no-op
                out = circuit

    return out, TransformRecord(
        name="aqc_tensor",
        config=config,
        depth_before=depth_before,
        depth_after=circuit_depth(out),
        runtime_ms=ms[0],
    )
