"""qiskit-addon-aqc-tensor wrapper (lazy import)."""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord
from ._common import run_addon_transform


def _aqc_call_with(kwargs: dict[str, Any]) -> Any:
    """``call`` that forwards ``kwargs`` to ``optimise`` (6B passthrough)."""

    def _aqc_call(addon: Any, circuit: Any) -> Any | None:
        maximize = getattr(addon, "MaximizeStateFidelity", None)
        generate_ansatz = getattr(addon, "generate_ansatz_from_circuit", None)
        optimise = getattr(addon, "optimise", None)
        if generate_ansatz is None or maximize is None or not callable(optimise):
            return None
        target = generate_ansatz(circuit)
        objective = maximize(target=target, ansatz=circuit)
        return optimise(objective, **kwargs)

    return _aqc_call


def apply_aqc_tensor(
    circuit: Any,
    *,
    bond_dim: int = 64,
    target_fidelity: float = 0.99,
    **addon_kwargs: Any,
) -> tuple[Any, TransformRecord]:
    """Approximate quantum compilation via tensor networks.

    Pass-through (with a record saying so) when the SDK is missing or
    exposes no usable entry point; ``fidelity_loss`` is
    ``1 - target_fidelity`` only when the compilation actually ran.
    """
    return run_addon_transform(
        "aqc_tensor",
        circuit,
        {"bond_dim": bond_dim, "target_fidelity": target_fidelity, **addon_kwargs},
        module="qiskit_addon_aqc_tensor",
        call=_aqc_call_with(addon_kwargs),
        fidelity_loss_if_applied=max(0.0, 1.0 - target_fidelity),
    )


def apply(circuit: Any, **kwargs: Any) -> tuple[Any, TransformRecord]:
    """6B module-level entry point: every kwarg goes to ``optimise``."""
    fidelity = float(kwargs.get("target_fidelity", 0.99))
    return run_addon_transform(
        "aqc_tensor",
        circuit,
        {"bond_dim": 64, "target_fidelity": 0.99, **kwargs},
        module="qiskit_addon_aqc_tensor",
        call=_aqc_call_with(kwargs),
        fidelity_loss_if_applied=max(0.0, 1.0 - fidelity),
    )
