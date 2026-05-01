"""AWS Braket adapter (amazon-braket-sdk)."""

from __future__ import annotations

import os
from typing import ClassVar

from .base import BackendInfo, JobHandle, ProviderAdapter, ProviderKind


class BraketAdapter(ProviderAdapter):
    name: ClassVar[str] = "braket"
    kind: ClassVar[ProviderKind] = "cloud-other"

    def is_available(self) -> bool:
        try:
            import braket  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            return False
        # Braket needs AWS credentials; PROMPT 6A treats SDK presence
        # as availability so the router can still quote pricing.
        return True

    def list_backend_infos(self) -> list[BackendInfo]:
        from .. import pricing_stub

        return [
            BackendInfo(
                name=entry.backend,
                provider=self.name,
                kind=self._classify(entry.backend),
                fidelity_estimate=entry.fidelity_estimate,
                queue_time_s_estimate=entry.queue_time_s_estimate,
                free_tier=entry.is_free_tier,
                simulator=entry.backend in {"sv1", "dm1", "tn1"},
                notes=f"AWS Braket {entry.backend}.",
            )
            for entry in pricing_stub.list_entries()
            if entry.provider == self.name
        ]

    @staticmethod
    def _classify(backend: str) -> ProviderKind:
        if "ionq" in backend:
            return "cloud-ion"
        if "rigetti" in backend or "iqm" in backend:
            return "cloud-sc"
        if backend == "sv1":
            return "cloud-other"
        return "cloud-other"

    def estimate_cost_stub(self, circuit: object, shots: int) -> float:
        from .. import pricing_stub

        return pricing_stub.estimate(self.name, "ionq_aria_1", shots)

    def submit(
        self,
        circuit: object,
        shots: int,
        backend: str,
    ) -> JobHandle:
        try:
            from braket.aws import AwsDevice  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            msg = "Braket submit requires amazon-braket-sdk."
            raise ImportError(msg) from exc
        _ = AwsDevice, os
        msg = "PROMPT 6A Braket submit() is contract-only; PROMPT 6B wires real submission."
        raise NotImplementedError(msg)
