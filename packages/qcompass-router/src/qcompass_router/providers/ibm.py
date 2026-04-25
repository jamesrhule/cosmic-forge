"""IBM Quantum runtime adapter (qiskit-ibm-runtime). Soft-imported."""

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


class IBMRuntimeAdapter(ProviderAdapter):
    name: ClassVar[str] = "ibm"
    kind: ClassVar[str] = "cloud-sc"

    # Common IBM superconducting backends. Used for routing/pricing
    # before live `list_backends()` is wired.
    _CATALOG: ClassVar[tuple[str, ...]] = (
        "ibm_brisbane",
        "ibm_kyoto",
        "ibm_osaka",
        "ibm_torino",
        "ibm_heron",
    )

    def __init__(self, channel: str = "ibm_quantum", token: str | None = None) -> None:
        self._channel = channel
        self._token = token

    def is_available(self) -> bool:
        if not _try_import("qiskit_ibm_runtime"):
            return False
        try:  # noqa: SIM105 — credentials probe
            from qiskit_ibm_runtime import QiskitRuntimeService  # type: ignore

            QiskitRuntimeService(channel=self._channel, token=self._token)
        except Exception:  # noqa: BLE001 — missing creds is just "unavailable"
            return False
        return True

    def list_backends(self) -> list[BackendInfo]:
        if not self.is_available():
            return [
                BackendInfo(provider=self.name, name=b, n_qubits=127)
                for b in self._CATALOG
            ]
        from qiskit_ibm_runtime import QiskitRuntimeService  # type: ignore

        svc = QiskitRuntimeService(channel=self._channel, token=self._token)
        out: list[BackendInfo] = []
        for backend in svc.backends():
            out.append(
                BackendInfo(
                    provider=self.name,
                    name=backend.name,
                    n_qubits=getattr(backend, "num_qubits", 0),
                    is_simulator=getattr(backend, "simulator", False),
                )
            )
        return out

    def estimate_cost_stub(self, circuit: Any, shots: int) -> float:
        return pricing_stub.estimate(self.name, "", shots)

    def submit(self, circuit: Any, shots: int, backend: str) -> JobHandle:
        if not self.is_available():
            raise RuntimeError("IBM runtime not available (missing SDK or credentials)")
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2  # type: ignore

        svc = QiskitRuntimeService(channel=self._channel, token=self._token)
        be = svc.backend(backend)
        sampler = SamplerV2(mode=be)
        job = sampler.run([circuit], shots=shots)
        return JobHandle(
            provider=self.name,
            backend=backend,
            job_id=getattr(job, "job_id", lambda: str(uuid4()))(),
        )
