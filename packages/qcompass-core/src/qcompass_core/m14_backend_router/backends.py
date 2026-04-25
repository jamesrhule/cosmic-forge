"""Built-in backends for the M14 router."""

from __future__ import annotations

from typing import Any

from ..errors import BackendUnavailableError
from ..manifest import ResourceEstimate


class ClassicalCPUBackend:
    """Always-available no-op classical backend."""

    name: str = "classical_cpu"
    provider: str = "qcompass"
    calibration_hash: str | None = None

    def submit(self, payload: Any, *, shots: int, seed: int | None) -> Any:
        # Pure CPU pass-through: callers wrap their classical
        # computation in a payload that knows how to ``run()`` itself.
        run = getattr(payload, "run", None)
        if callable(run):
            return run()
        # Fallback: echo the payload so deterministic round-trip tests
        # have something to assert against.
        return {"shots": shots, "seed": seed, "echo": payload}

    def cost_estimate(self, _payload: Any) -> ResourceEstimate:
        return ResourceEstimate(
            physical_qubits=0,
            logical_qubits=0,
            t_count=0,
            rotation_count=0,
            depth=0,
            runtime_seconds=0.0,
            estimator="stub",
            notes="Classical CPU fallback — no quantum resources.",
        )


class LocalAerBackend:
    """qiskit-aer simulator. Imports the SDK lazily.

    Submitting a payload requires :mod:`qiskit_aer`. Without it the
    backend is registered (so callers see it in the catalogue) but
    every ``submit()`` call raises :class:`BackendUnavailableError`.
    """

    name: str = "local_aer"
    provider: str = "qiskit"
    calibration_hash: str | None = None  # Aer is deterministic; hash N/A.

    def __init__(self) -> None:
        self._aer = self._maybe_import_aer()

    @staticmethod
    def _maybe_import_aer() -> object | None:
        try:
            from qiskit_aer import AerSimulator  # type: ignore[import-not-found]
        except ImportError:
            return None
        return AerSimulator()

    def submit(self, payload: Any, *, shots: int, seed: int | None) -> Any:
        if self._aer is None:
            msg = (
                "qiskit-aer is not installed. Install with "
                "`pip install qcompass-core[ibm]` to enable local_aer."
            )
            raise BackendUnavailableError(msg)
        # Payload must be a transpiled QuantumCircuit; we leave the
        # actual ``transpile`` step to the plugin so we don't impose a
        # qiskit version on every importer.
        return self._aer.run(payload, shots=shots, seed_simulator=seed).result()

    def cost_estimate(self, payload: Any) -> ResourceEstimate:
        try:
            n_qubits = int(getattr(payload, "num_qubits", 0))
            depth = int(payload.depth()) if hasattr(payload, "depth") else 0
        except Exception:  # pragma: no cover - introspection best-effort
            n_qubits, depth = 0, 0
        return ResourceEstimate(
            physical_qubits=n_qubits,
            logical_qubits=n_qubits,
            t_count=0,
            rotation_count=0,
            depth=depth,
            runtime_seconds=0.0,
            estimator="stub",
            notes="LocalAer cost estimate — ideal simulator, no error model.",
        )
