"""AWS Braket adapter (amazon-braket-sdk). Soft-imported."""

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


class BraketAdapter(ProviderAdapter):
    name: ClassVar[str] = "braket"
    kind: ClassVar[str] = "cloud-other"

    # Pricing-seed key per backend keeps Phase-6A deterministic.
    _CATALOG: ClassVar[dict[str, str]] = {
        "ionq_aria": "braket_ionq_aria",
        "ionq_forte": "braket_ionq_forte",
        "rigetti_ankaa": "braket_rigetti_ankaa",
    }

    def is_available(self) -> bool:
        if not _try_import("braket.aws"):
            return False
        try:
            from braket.aws import AwsSession  # type: ignore

            AwsSession()
        except Exception:  # noqa: BLE001 — missing creds → unavailable
            return False
        return True

    def list_backends(self) -> list[BackendInfo]:
        return [
            BackendInfo(provider=self.name, name=name)
            for name in self._CATALOG
        ]

    def estimate_cost_stub(self, circuit: Any, shots: int) -> float:
        # Default to the cheapest cataloged backend if the caller hasn't
        # picked one yet — keeps `Router.decide` decisions consistent.
        cheapest = min(
            (
                pricing_stub.estimate(self.name, key, shots)
                for key in self._CATALOG.values()
            ),
            default=0.0,
        )
        return cheapest

    def estimate_cost_for(self, backend: str, shots: int) -> float:
        key = self._CATALOG.get(backend, backend)
        return pricing_stub.estimate(self.name, key, shots)

    def submit(self, circuit: Any, shots: int, backend: str) -> JobHandle:
        if not self.is_available():
            raise RuntimeError("Braket not available (missing SDK or credentials)")
        from braket.aws import AwsDevice, AwsQuantumTask  # type: ignore  # noqa: F401

        device_arn_map = {
            "ionq_aria": "arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1",
            "ionq_forte": "arn:aws:braket:us-east-1::device/qpu/ionq/Forte-1",
            "rigetti_ankaa": "arn:aws:braket:us-west-1::device/qpu/rigetti/Ankaa-3",
        }
        arn = device_arn_map.get(backend, backend)
        device = AwsDevice(arn)
        task = device.run(circuit, shots=shots)
        return JobHandle(
            provider=self.name,
            backend=backend,
            job_id=getattr(task, "id", str(uuid4())),
        )
