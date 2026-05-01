"""Azure Quantum adapter (azure-quantum)."""

from __future__ import annotations

from typing import ClassVar

from .base import BackendInfo, JobHandle, ProviderAdapter, ProviderKind


class AzureAdapter(ProviderAdapter):
    name: ClassVar[str] = "azure"
    kind: ClassVar[ProviderKind] = "cloud-other"

    def is_available(self) -> bool:
        try:
            import azure.quantum  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            return False
        return True

    def list_backends(self) -> list[BackendInfo]:
        from .. import pricing_stub

        return [
            BackendInfo(
                name=entry.backend,
                provider=self.name,
                kind="cloud-ion" if "ionq" in entry.backend else "cloud-other",
                fidelity_estimate=entry.fidelity_estimate,
                queue_time_s_estimate=entry.queue_time_s_estimate,
                free_tier=entry.is_free_tier,
                notes=f"Azure Quantum {entry.backend}.",
            )
            for entry in pricing_stub.list_entries()
            if entry.provider == self.name
        ]

    def estimate_cost_stub(self, circuit: object, shots: int) -> float:
        from .. import pricing_stub

        # Default Azure target: IonQ Aria via Azure (per-shot model).
        return pricing_stub.estimate(self.name, "ionq_aria", shots)

    def submit(
        self,
        circuit: object,
        shots: int,
        backend: str,
    ) -> JobHandle:
        try:
            from azure.quantum import Workspace  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            msg = "Azure submit requires azure-quantum."
            raise ImportError(msg) from exc
        _ = Workspace
        msg = "PROMPT 6A Azure submit() is contract-only."
        raise NotImplementedError(msg)
