"""Local Aer simulator adapter (qiskit-aer). Soft-imported."""

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


class LocalAerAdapter(ProviderAdapter):
    name: ClassVar[str] = "local_aer"
    kind: ClassVar[str] = "local"

    _DEFAULT_BACKEND: ClassVar[str] = "aer_simulator"

    def is_available(self) -> bool:
        return _try_import("qiskit_aer")

    def list_backends(self) -> list[BackendInfo]:
        return [
            BackendInfo(
                provider=self.name,
                name=self._DEFAULT_BACKEND,
                is_simulator=True,
            )
        ]

    def estimate_cost_stub(self, circuit: Any, shots: int) -> float:
        return pricing_stub.estimate(self.name, "", shots)

    def submit(self, circuit: Any, shots: int, backend: str) -> JobHandle:
        if not self.is_available():
            raise RuntimeError("qiskit-aer not installed")
        from qiskit_aer import AerSimulator  # type: ignore

        sim = AerSimulator()
        job = sim.run(circuit, shots=shots)
        return JobHandle(
            provider=self.name,
            backend=backend or self._DEFAULT_BACKEND,
            job_id=getattr(job, "job_id", lambda: str(uuid4()))(),
        )
