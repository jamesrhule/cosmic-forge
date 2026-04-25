"""Pasqal Fresnel adapter (pulser + pasqal-cloud). Soft-imported."""

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


class PasqalAdapter(ProviderAdapter):
    name: ClassVar[str] = "pasqal"
    kind: ClassVar[str] = "cloud-neutral-atom"

    _CATALOG: ClassVar[tuple[str, ...]] = ("fresnel",)

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        project_id: str | None = None,
    ) -> None:
        self._username = username or os.environ.get("PASQAL_USERNAME")
        self._password = password or os.environ.get("PASQAL_PASSWORD")
        self._project_id = project_id or os.environ.get("PASQAL_PROJECT_ID")

    def is_available(self) -> bool:
        if not _try_import("pulser"):
            return False
        if not _try_import("pasqal_cloud"):
            return False
        if not all((self._username, self._password, self._project_id)):
            return False
        return True

    def list_backends(self) -> list[BackendInfo]:
        return [BackendInfo(provider=self.name, name=n) for n in self._CATALOG]

    def estimate_cost_stub(self, circuit: Any, shots: int) -> float:
        return pricing_stub.estimate(self.name, "fresnel", shots)

    def submit(self, circuit: Any, shots: int, backend: str) -> JobHandle:
        if not self.is_available():
            raise RuntimeError("Pasqal not available (missing pulser/pasqal-cloud/creds)")
        from pasqal_cloud import SDK  # type: ignore

        sdk = SDK(
            username=self._username,
            password=self._password,
            project_id=self._project_id,
        )
        # `circuit` is expected to be a serialized pulser sequence.
        batch = sdk.create_batch(serialized_sequence=circuit, jobs=[{"runs": shots}])
        return JobHandle(
            provider=self.name,
            backend=backend,
            job_id=str(getattr(batch, "id", uuid4())),
        )
