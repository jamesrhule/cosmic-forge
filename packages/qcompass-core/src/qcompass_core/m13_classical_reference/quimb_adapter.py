"""quimb tensor-network adapter (soft import)."""

from __future__ import annotations

from typing import Any

from ..errors import ClassicalReferenceError
from .base import ClassicalReferenceResult, hash_payload


class QuimbAdapter:
    """quimb-based MPS / tensor-network reference (soft import)."""

    name: str = "quimb"

    def compute(self, problem: dict[str, Any]) -> ClassicalReferenceResult:
        try:
            import quimb  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional
            msg = (
                "quimb is not installed. `pip install qcompass-core[tn]` "
                "to enable QuimbAdapter."
            )
            raise ClassicalReferenceError(msg) from exc

        _ = quimb  # type: ignore[unused-ignore]
        msg = (
            "QuimbAdapter.compute contract fixed; driver lands with "
            "qfull-condmat. Use hash_only() to record provenance now."
        )
        raise ClassicalReferenceError(msg)

    def hash_only(self, problem: dict[str, Any]) -> str:
        return hash_payload(problem)
