"""QED-C App-Oriented Benchmarks adapter (soft-import).

The QED-C suite isn't a pip-installable wheel today; users vendor
it locally. The adapter checks for an importable
``qedc_benchmarks`` namespace and raises a documented hint when
absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class QedCAdapter:
    """Wrap the QED-C App-Oriented Benchmarks runner."""

    def is_available(self) -> bool:
        try:
            import qedc_benchmarks  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            return False
        return True

    def list_benchmarks(self) -> list[str]:
        try:
            import qedc_benchmarks as qedc  # type: ignore[import-not-found]
        except ImportError as exc:
            msg = (
                "QED-C App-Oriented Benchmarks are not installed. "
                "Vendor the suite under qedc_benchmarks/ and add the "
                "directory to PYTHONPATH; see the QED-C GitHub repo."
            )
            raise ImportError(msg) from exc
        return list(getattr(qedc, "list_benchmarks", lambda: [])())

    def run(self, name: str, **kwargs: Any) -> dict[str, Any]:
        try:
            import qedc_benchmarks  # type: ignore[import-not-found]  # noqa: F401
        except ImportError as exc:
            msg = (
                "QED-C App-Oriented Benchmarks are not installed; "
                "vendor the suite to use this adapter."
            )
            raise ImportError(msg) from exc
        return {
            "adapter": "qed_c",
            "benchmark": name,
            "kwargs": kwargs,
        }
