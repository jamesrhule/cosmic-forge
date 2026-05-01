"""Native IonQ adapter (qiskit-ionq fallback when present)."""

from __future__ import annotations

from typing import ClassVar

from .base import BackendInfo, JobHandle, ProviderAdapter, ProviderKind


class IonQAdapter(ProviderAdapter):
    name: ClassVar[str] = "ionq"
    kind: ClassVar[ProviderKind] = "cloud-ion"

    def is_available(self) -> bool:
        # Native IonQ Python SDK is `ionq`. Fall back to qiskit-ionq.
        for module in ("ionq", "qiskit_ionq"):
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
                notes=f"IonQ native {entry.backend}.",
            )
            for entry in pricing_stub.list_entries()
            if entry.provider == self.name
        ]

    def estimate_cost_stub(self, circuit: object, shots: int) -> float:
        from .. import pricing_stub

        return pricing_stub.estimate(self.name, "aria", shots)

    def submit(
        self,
        circuit: object,
        shots: int,
        backend: str,
    ) -> JobHandle:
        msg = "PROMPT 6A IonQ submit() is contract-only."
        raise NotImplementedError(msg)
