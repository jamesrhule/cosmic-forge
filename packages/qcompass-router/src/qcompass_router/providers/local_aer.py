"""Local Aer adapter (qiskit-aer)."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import ClassVar

from .base import BackendInfo, JobHandle, ProviderAdapter, ProviderKind


class LocalAerAdapter(ProviderAdapter):
    name: ClassVar[str] = "local_aer"
    kind: ClassVar[ProviderKind] = "local"

    def is_available(self) -> bool:
        try:
            import qiskit_aer  # noqa: F401
        except ImportError:
            return False
        return True

    def list_backend_infos(self) -> list[BackendInfo]:
        # AerSimulator is the only backend we expose today; PROMPT
        # 6B can split into method-specific Aer simulators
        # (statevector / matrix_product_state / extended_stabilizer).
        return [
            BackendInfo(
                name="aer_simulator",
                provider=self.name,
                kind=self.kind,
                fidelity_estimate=1.0,
                queue_time_s_estimate=0.0,
                free_tier=True,
                simulator=True,
                notes="Noise-free Aer simulator on the local CPU.",
            ),
        ]

    def estimate_cost_stub(self, circuit: object, shots: int) -> float:
        from .. import pricing_stub

        return pricing_stub.estimate(self.name, "aer_simulator", shots)

    def submit(
        self,
        circuit: object,
        shots: int,
        backend: str,
    ) -> JobHandle:
        try:
            from qiskit_aer import AerSimulator  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional path
            msg = (
                "local_aer requires qiskit-aer; install via "
                "qcompass-router[ibm]."
            )
            raise ImportError(msg) from exc
        sim = AerSimulator()
        # We don't transpile here; PROMPT 6B's transform stack does
        # circuit-aware transpilation. For PROMPT 6A's smoke purposes
        # we just kick off the job.
        job = sim.run(circuit, shots=shots)
        return JobHandle(
            provider=self.name,
            backend=backend,
            job_id=str(getattr(job, "job_id", lambda: secrets.token_hex(6))()),
            submitted_at=datetime.now(UTC).isoformat(),
            metadata={"shots": shots},
        )
