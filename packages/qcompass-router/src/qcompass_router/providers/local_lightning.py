"""Local PennyLane-Lightning adapter."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import ClassVar

from .base import BackendInfo, JobHandle, ProviderAdapter, ProviderKind


class LocalLightningAdapter(ProviderAdapter):
    name: ClassVar[str] = "local_lightning"
    kind: ClassVar[ProviderKind] = "local"

    def is_available(self) -> bool:
        try:
            import pennylane  # noqa: F401
            import pennylane_lightning  # noqa: F401
        except ImportError:
            return False
        return True

    def list_backends(self) -> list[BackendInfo]:
        return [
            BackendInfo(
                name="lightning.qubit",
                provider=self.name,
                kind=self.kind,
                fidelity_estimate=1.0,
                queue_time_s_estimate=0.0,
                free_tier=True,
                simulator=True,
                notes="PennyLane-Lightning CPU/GPU/Kokkos device.",
            ),
        ]

    def estimate_cost_stub(self, circuit: object, shots: int) -> float:
        from .. import pricing_stub

        return pricing_stub.estimate(self.name, "lightning.qubit", shots)

    def submit(
        self,
        circuit: object,
        shots: int,
        backend: str,
    ) -> JobHandle:
        try:
            import pennylane as qml  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            msg = (
                "local_lightning requires pennylane + pennylane-lightning; "
                "install via qcompass-router[lightning]."
            )
            raise ImportError(msg) from exc
        # circuit is expected to be a PennyLane QNode-compatible callable.
        _ = qml
        return JobHandle(
            provider=self.name,
            backend=backend,
            job_id=secrets.token_hex(6),
            submitted_at=datetime.now(UTC).isoformat(),
            metadata={"shots": shots},
        )
