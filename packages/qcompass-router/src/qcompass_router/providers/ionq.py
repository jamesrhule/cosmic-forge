"""IonQ native cloud adapter (with qiskit-ionq as fallback). Soft-imported."""

from __future__ import annotations

import os
from typing import Any, ClassVar
from uuid import uuid4

from qcompass_router import pricing_stub
from qcompass_router.providers.base import (
    BackendInfo,
    JobHandle,
    ProviderAdapter,
    _try_import,
)


class IonQNativeAdapter(ProviderAdapter):
    name: ClassVar[str] = "ionq"
    kind: ClassVar[str] = "cloud-ion"

    _CATALOG: ClassVar[dict[str, str]] = {
        # Native IonQ cloud uses the same backend names as Braket pricing keys.
        "ionq_aria": "braket_ionq_aria",
        "ionq_forte": "braket_ionq_forte",
    }

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("IONQ_API_KEY")

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        # Native ionq client is the preferred path; qiskit-ionq is the fallback.
        return _try_import("ionq") or _try_import("qiskit_ionq")

    def list_backends(self) -> list[BackendInfo]:
        return [BackendInfo(provider=self.name, name=n) for n in self._CATALOG]

    def estimate_cost_stub(self, circuit: Any, shots: int) -> float:
        cheapest = min(
            (
                pricing_stub.estimate(self.name, key, shots)
                for key in self._CATALOG.values()
            ),
            default=0.0,
        )
        return cheapest

    def submit(self, circuit: Any, shots: int, backend: str) -> JobHandle:
        if not self.is_available():
            raise RuntimeError("IonQ native client not available")
        # Native client preferred.
        if _try_import("ionq"):
            import ionq  # type: ignore

            client = ionq.Client(api_key=self._api_key)
            job = client.create_job(target=backend, shots=shots, circuit=circuit)
            return JobHandle(
                provider=self.name,
                backend=backend,
                job_id=getattr(job, "id", str(uuid4())),
            )
        from qiskit_ionq import IonQProvider  # type: ignore

        provider = IonQProvider(self._api_key)
        be = provider.get_backend(f"ionq_qpu.{backend}")
        job = be.run(circuit, shots=shots)
        return JobHandle(
            provider=self.name,
            backend=backend,
            job_id=getattr(job, "job_id", lambda: str(uuid4()))(),
        )
