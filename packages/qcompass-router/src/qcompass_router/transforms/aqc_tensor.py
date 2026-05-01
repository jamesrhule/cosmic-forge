"""qiskit-addon-aqc-tensor wrapper (lazy import)."""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord


def apply_aqc_tensor(
    circuit: Any,
    *,
    bond_dim: int = 64,
    target_fidelity: float = 0.99,
) -> tuple[Any, TransformRecord]:
    """Apply AQC-tensor compilation; return (circuit, record).

    Phase-1 wiring is contract-only: when the SDK is missing we
    return the circuit unchanged with a record marking the SDK
    state. Tests that need real AQC numerics use
    ``pytest.importorskip`` on ``qiskit_addon_aqc_tensor``.
    """
    parameters = {"bond_dim": bond_dim, "target_fidelity": target_fidelity}
    try:
        import qiskit_addon_aqc_tensor as aqc  # type: ignore[import-not-found]
    except ImportError:
        return circuit, TransformRecord(
            name="aqc_tensor",
            parameters=parameters,
            fidelity_loss=0.0,
            notes="SDK absent — pass-through.",
        )
    _ = aqc
    # Real wiring: aqc.tensor.compile(circuit, ...). Phase-1 keeps
    # the contract surface stable; PROMPT 6C lands the actual call.
    return circuit, TransformRecord(
        name="aqc_tensor",
        parameters=parameters,
        fidelity_loss=max(0.0, 1.0 - target_fidelity),
        notes="aqc-tensor SDK importable; numerics wired in PROMPT 6C.",
    )
