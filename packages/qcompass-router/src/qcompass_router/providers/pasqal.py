"""Pasqal adapter (pulser SDK)."""

from __future__ import annotations

from typing import ClassVar

from .base import BackendInfo, JobHandle, ProviderAdapter, ProviderKind


class PasqalAdapter(ProviderAdapter):
    name: ClassVar[str] = "pasqal"
    kind: ClassVar[ProviderKind] = "cloud-neutral-atom"

    def is_available(self) -> bool:
        try:
            import pulser  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            return False
        return True

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
                notes=f"Pasqal {entry.backend} via pulser.",
            )
            for entry in pricing_stub.list_entries()
            if entry.provider == self.name
        ]

    def estimate_cost_stub(self, circuit: object, shots: int) -> float:
        from .. import pricing_stub

        return pricing_stub.estimate(self.name, "fresnel", shots)

    def submit(
        self,
        circuit: object,
        shots: int,
        backend: str,
    ) -> JobHandle:
        msg = "PROMPT 6A Pasqal submit() is contract-only."
        raise NotImplementedError(msg)
