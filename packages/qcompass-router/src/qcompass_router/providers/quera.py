"""QuEra Aquila adapter (bloqade-analog via Braket). Soft-imported."""

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


class QueRaAdapter(ProviderAdapter):
    name: ClassVar[str] = "quera"
    kind: ClassVar[str] = "cloud-neutral-atom"

    _CATALOG: ClassVar[tuple[str, ...]] = ("aquila",)

    def is_available(self) -> bool:
        # bloqade-analog ships QueRa hardware tasks; it depends on
        # amazon-braket-sdk for hardware submission.
        return _try_import("bloqade.analog") and _try_import("braket.aws")

    def list_backends(self) -> list[BackendInfo]:
        return [BackendInfo(provider=self.name, name=n) for n in self._CATALOG]

    def estimate_cost_stub(self, circuit: Any, shots: int) -> float:
        return pricing_stub.estimate(self.name, "aquila", shots)

    def submit(self, circuit: Any, shots: int, backend: str) -> JobHandle:
        if not self.is_available():
            raise RuntimeError("QuEra not available (missing bloqade-analog/braket)")
        # bloqade-analog hardware submission API; circuit is expected to
        # be a QuEra-compatible analog program built by the caller.
        from bloqade.analog.task.batch import RemoteBatch  # type: ignore  # noqa: F401

        batch = circuit.braket.aquila.run_async(shots=shots)
        return JobHandle(
            provider=self.name,
            backend=backend,
            job_id=str(getattr(batch, "id", uuid4())),
        )
