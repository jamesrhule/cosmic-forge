"""IBM Quantum adapter (qiskit-ibm-runtime)."""

from __future__ import annotations

import os
from typing import ClassVar

from .base import BackendInfo, JobHandle, ProviderAdapter, ProviderKind


class IBMAdapter(ProviderAdapter):
    name: ClassVar[str] = "ibm"
    kind: ClassVar[ProviderKind] = "cloud-sc"

    def is_available(self) -> bool:
        try:
            import qiskit_ibm_runtime  # noqa: F401
        except ImportError:
            return False
        # The Open Plan does NOT require credentials at import time;
        # we still honour QISKIT_IBM_TOKEN if set, but treat the
        # adapter as available whenever the SDK is importable so the
        # router can quote pricing for IBM Heron without forcing the
        # user to log in first. PROMPT 6B replaces this with a real
        # credential probe.
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
                notes=f"IBM {entry.backend} (Open Plan: 10 min/month).",
            )
            for entry in pricing_stub.list_entries()
            if entry.provider == self.name
        ]

    def estimate_cost_stub(self, circuit: object, shots: int) -> float:
        from .. import pricing_stub

        # Default to ibm_heron when the caller doesn't pin a backend.
        return pricing_stub.estimate(self.name, "ibm_heron", shots)

    def submit(
        self,
        circuit: object,
        shots: int,
        backend: str,
    ) -> JobHandle:
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional
            msg = "IBM submit requires qiskit-ibm-runtime."
            raise ImportError(msg) from exc
        _ = QiskitRuntimeService, os
        msg = (
            "PROMPT 6A IBM submit() is contract-only; PROMPT 6B wires "
            "real Sampler / Estimator V2 dispatch."
        )
        raise NotImplementedError(msg)
