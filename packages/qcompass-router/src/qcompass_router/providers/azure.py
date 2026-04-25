"""Azure Quantum adapter (azure-quantum). Soft-imported."""

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


class AzureQuantumAdapter(ProviderAdapter):
    name: ClassVar[str] = "azure"
    kind: ClassVar[str] = "cloud-other"

    _CATALOG: ClassVar[dict[str, str]] = {
        "quantinuum_h2": "azure_quantinuum_h2",
        "ionq_aria": "azure_ionq_aria",
    }

    def __init__(
        self,
        subscription_id: str | None = None,
        resource_group: str | None = None,
        name: str | None = None,
        location: str | None = None,
    ) -> None:
        self._subscription_id = subscription_id
        self._resource_group = resource_group
        self._workspace_name = name
        self._location = location

    def is_available(self) -> bool:
        if not _try_import("azure.quantum"):
            return False
        if not all(
            (
                self._subscription_id,
                self._resource_group,
                self._workspace_name,
                self._location,
            )
        ):
            return False
        try:
            from azure.quantum import Workspace  # type: ignore

            Workspace(
                subscription_id=self._subscription_id,
                resource_group=self._resource_group,
                name=self._workspace_name,
                location=self._location,
            )
        except Exception:  # noqa: BLE001
            return False
        return True

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
            raise RuntimeError("Azure Quantum not available (missing SDK/creds)")
        from azure.quantum import Workspace  # type: ignore

        ws = Workspace(
            subscription_id=self._subscription_id,
            resource_group=self._resource_group,
            name=self._workspace_name,
            location=self._location,
        )
        target = ws.get_targets(backend)
        job = target.submit(circuit, shots=shots)
        return JobHandle(
            provider=self.name,
            backend=backend,
            job_id=getattr(job, "id", str(uuid4())),
        )
