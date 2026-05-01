"""MQT-Bench adapter (mqt.bench, soft-import).

PROMPT 1 v2 §LAYOUT lists this as one of three external-benchmark
runners. Phase-1 ships the adapter shape: importing this module
without ``mqt.bench`` installed succeeds; calling
:meth:`MQTBenchAdapter.run` raises a clear :class:`ImportError` so
the bench can fall back to its bundled-manifest set without the
external library.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MQTBenchAdapter:
    """Wrap MQT-Bench's :func:`get_benchmark` API."""

    def is_available(self) -> bool:
        try:
            import mqt.bench  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            return False
        return True

    def list_benchmarks(self) -> list[str]:
        """Return the names of every algorithm MQT-Bench exposes."""
        try:
            import mqt.bench  # type: ignore[import-not-found]
        except ImportError as exc:
            msg = (
                "mqt.bench is not installed. Install via "
                "`pip install qcompass-bench[mqt]`."
            )
            raise ImportError(msg) from exc
        # MQT-Bench exposes a tagged registry; placeholder list keeps
        # the adapter surface stable.
        return list(getattr(mqt.bench, "list_benchmarks", lambda: [])())

    def run(self, name: str, *, n_qubits: int) -> dict[str, Any]:
        """Compile a single MQT-Bench algorithm at ``n_qubits``."""
        try:
            import mqt.bench as mqt  # type: ignore[import-not-found]
        except ImportError as exc:
            msg = (
                "mqt.bench is not installed. Install via "
                "`pip install qcompass-bench[mqt]`."
            )
            raise ImportError(msg) from exc
        circuit = mqt.get_benchmark(name, n_qubits=n_qubits)  # type: ignore[attr-defined]
        return {
            "adapter": "mqt_bench",
            "algorithm": name,
            "n_qubits": n_qubits,
            "circuit": circuit,
        }
