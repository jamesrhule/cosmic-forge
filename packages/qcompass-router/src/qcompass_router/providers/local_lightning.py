"""Local PennyLane Lightning adapter (CPU/GPU/Kokkos). Soft-imported."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import uuid4

from qcompass_router import pricing_stub
from qcompass_router.providers.base import (
    BackendInfo,
    JobHandle,
    ProviderAdapter,
    _try_import,
)


class LocalLightningAdapter(ProviderAdapter):
    name: ClassVar[str] = "local_lightning"
    kind: ClassVar[str] = "local"

    # Lightning device variants, in order of preference: gpu first if
    # available (largest circuits), then kokkos, then cpu.
    _VARIANTS: ClassVar[tuple[str, ...]] = (
        "lightning.gpu",
        "lightning.kokkos",
        "lightning.qubit",
    )

    def is_available(self) -> bool:
        return _try_import("pennylane") and _try_import("pennylane_lightning")

    def list_backends(self) -> list[BackendInfo]:
        return [
            BackendInfo(provider=self.name, name=v, is_simulator=True)
            for v in self._VARIANTS
        ]

    def _resolve_device(self) -> str:
        """Pick the best lightning variant available; fall back to CPU."""
        if not self.is_available():
            return "lightning.qubit"
        try:
            import pennylane as qml  # type: ignore

            for variant in self._VARIANTS:
                try:
                    qml.device(variant, wires=1)
                    return variant
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            pass
        return "lightning.qubit"

    def estimate_cost_stub(self, circuit: Any, shots: int) -> float:
        return pricing_stub.estimate(self.name, "", shots)

    def submit(self, circuit: Any, shots: int, backend: str) -> JobHandle:
        if not self.is_available():
            raise RuntimeError("pennylane-lightning not installed")
        device_name = backend or self._resolve_device()
        # Phase-6A: we just acknowledge submission. Phase-6B wires QASM
        # → PennyLane qfunc + executes against the device.
        return JobHandle(
            provider=self.name,
            backend=device_name,
            job_id=str(uuid4()),
        )
