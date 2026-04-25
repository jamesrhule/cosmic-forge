"""IQM adapter (iqm-client / qiskit-iqm). Soft-imported."""

from __future__ import annotations

import os
from typing import Any, ClassVar
from uuid import uuid4

from qcompass_router import pricing_stub
from qcompass_router.providers.base import (
    BackendInfo,
    JobHandle,
    ProviderAdapter,
    _try_import,
)


class IQMAdapter(ProviderAdapter):
    name: ClassVar[str] = "iqm"
    kind: ClassVar[str] = "cloud-sc"

    _CATALOG: ClassVar[tuple[str, ...]] = (
        "garnet",
        "deneb",
    )

    def __init__(self, server_url: str | None = None, token: str | None = None) -> None:
        self._server_url = server_url or os.environ.get("IQM_SERVER_URL")
        self._token = token or os.environ.get("IQM_TOKEN")

    def is_available(self) -> bool:
        if not self._server_url:
            return False
        return _try_import("iqm.iqm_client") or _try_import("qiskit_iqm")

    def list_backends(self) -> list[BackendInfo]:
        return [BackendInfo(provider=self.name, name=n) for n in self._CATALOG]

    def estimate_cost_stub(self, circuit: Any, shots: int) -> float:
        return pricing_stub.estimate(self.name, "", shots)

    def submit(self, circuit: Any, shots: int, backend: str) -> JobHandle:
        if not self.is_available():
            raise RuntimeError("IQM not available (missing SDK or credentials)")
        if _try_import("qiskit_iqm"):
            from qiskit_iqm import IQMProvider  # type: ignore

            provider = IQMProvider(self._server_url, token=self._token)
            be = provider.get_backend(backend)
            job = be.run(circuit, shots=shots)
            return JobHandle(
                provider=self.name,
                backend=backend,
                job_id=getattr(job, "job_id", lambda: str(uuid4()))(),
            )
        from iqm.iqm_client import IQMClient  # type: ignore

        client = IQMClient(self._server_url, token=self._token)
        run = client.submit_circuits([circuit], shots=shots)
        return JobHandle(
            provider=self.name,
            backend=backend,
            job_id=str(getattr(run, "id", uuid4())),
        )
