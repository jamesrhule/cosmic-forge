"""ipie AFQMC adapter (soft import)."""

from __future__ import annotations

from typing import Any

from ..errors import ClassicalReferenceError
from .base import ClassicalReferenceResult, hash_payload


class IpieAdapter:
    """AFQMC reference via ipie (soft import)."""

    name: str = "ipie"

    def compute(self, problem: dict[str, Any]) -> ClassicalReferenceResult:
        try:
            import ipie  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional
            msg = (
                "ipie is not installed. `pip install qcompass-core[afqmc]` "
                "to enable IpieAdapter."
            )
            raise ClassicalReferenceError(msg) from exc

        _ = ipie  # type: ignore[unused-ignore]
        msg = (
            "IpieAdapter.compute contract fixed; driver lands with "
            "qfull-chemistry. Use hash_only() for provenance now."
        )
        raise ClassicalReferenceError(msg)

    def hash_only(self, problem: dict[str, Any]) -> str:
        return hash_payload(problem)
