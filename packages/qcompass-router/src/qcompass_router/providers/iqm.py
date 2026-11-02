"""IQM adapter (iqm-client / qiskit-iqm)."""

from __future__ import annotations

from typing import ClassVar

from .base import BackendInfo, JobHandle, ProviderAdapter, ProviderKind


class IQMAdapter(ProviderAdapter):
    name: ClassVar[str] = "iqm"
    kind: ClassVar[ProviderKind] = "cloud-sc"

    def is_available(self) -> bool:
        for module in ("iqm_client", "qiskit_iqm"):
            try:
                __import__(module)
                return True
            except ImportError:
                continue
        return False

    def list_backend_infos(self) -> list[BackendInfo]:
        from .. import pricing_stub

        return [
            BackendInfo(
                name=entry.backend,
                provider=self.name,
                kind=self.kind,
                fidelity_estimate=entry.fidelity_estimate,
                queue_time_s_estimate=entry.queue_time_s_estimate,
                free_tier=entry.is_free_tier,
                notes=f"IQM {entry.backend} (Starter: 30 credits/mo).",
            )
            for entry in pricing_stub.list_entries()
            if entry.provider == self.name
        ]

    def estimate_cost_stub(self, circuit: object, shots: int) -> float:
        from .. import pricing_stub

        return pricing_stub.estimate(self.name, "iqm_garnet", shots)

    def submit(
        self,
        circuit: object,
        shots: int,
        backend: str,
    ) -> JobHandle:
        msg = "PROMPT 6A IQM submit() is contract-only."
        raise NotImplementedError(msg)
