"""Shared types + utilities for classical-reference adapters."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol, TypedDict

from ..errors import ClassicalReferenceError


class ClassicalReferenceResult(TypedDict):
    """Common return shape across PySCF / block2 / quimb / ipie."""

    hash: str
    energy: float
    metadata: dict[str, Any]


class ClassicalReference(Protocol):
    """Protocol every M13 adapter satisfies."""

    name: str

    def compute(self, problem: dict[str, Any]) -> ClassicalReferenceResult:
        """Run the reference computation; raise :class:`ClassicalReferenceError` on failure."""


def hash_payload(payload: dict[str, Any]) -> str:
    """SHA-256 of the canonical JSON encoding of ``payload``.

    Adapters call this *after* normalising their problem dict so two
    callers describing the same physical system produce the same hash
    regardless of dict ordering.
    """
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def require(condition: bool, message: str) -> None:
    """Helper that raises :class:`ClassicalReferenceError` on failure."""
    if not condition:
        raise ClassicalReferenceError(message)
