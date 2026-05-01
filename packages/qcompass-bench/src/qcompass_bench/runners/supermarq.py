"""SupermarQ adapter (soft-import)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SupermarQAdapter:
    """Wrap the SupermarQ benchmarking suite."""

    def is_available(self) -> bool:
        try:
            import supermarq  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            return False
        return True

    def list_benchmarks(self) -> list[str]:
        try:
            import supermarq as sm  # type: ignore[import-not-found]
        except ImportError as exc:
            msg = (
                "supermarq is not installed. Install via "
                "`pip install qcompass-bench[supermarq]`."
            )
            raise ImportError(msg) from exc
        return list(getattr(sm, "list_benchmarks", lambda: [])())

    def run(self, name: str, **kwargs: Any) -> dict[str, Any]:
        try:
            import supermarq as sm  # type: ignore[import-not-found]
        except ImportError as exc:
            msg = (
                "supermarq is not installed. Install via "
                "`pip install qcompass-bench[supermarq]`."
            )
            raise ImportError(msg) from exc
        bench = getattr(sm, "Benchmark", None)
        if bench is None:
            msg = "supermarq.Benchmark is not exposed by this version."
            raise ImportError(msg)
        return {
            "adapter": "supermarq",
            "benchmark": name,
            "kwargs": kwargs,
        }
