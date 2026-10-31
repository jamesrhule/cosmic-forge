"""block2 / pyblock2 DMRG adapter (soft import)."""

from __future__ import annotations

from typing import Any

from ..errors import ClassicalReferenceError
from .base import ClassicalReferenceResult, hash_payload


class Block2Adapter:
    """DMRG via pyblock2.

    Currently exposes the *contract* — full driver wiring lands when
    qfull-chemistry needs it. Calling :meth:`compute` without
    pyblock2 installed raises :class:`ClassicalReferenceError`.
    """

    name: str = "block2"

    def compute(self, problem: dict[str, Any]) -> ClassicalReferenceResult:
        try:
            import pyblock2  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional
            msg = (
                "pyblock2 is not installed. `pip install qcompass-core[chem]` "
                "or build block2 from source for DMRG references."
            )
            raise ClassicalReferenceError(msg) from exc

        _ = pyblock2  # type: ignore[unused-ignore]
        msg = (
            "Block2Adapter.compute is not yet wired. The contract is fixed; "
            "qfull-chemistry will land the driver in a later phase."
        )
        raise ClassicalReferenceError(msg)

    def hash_only(self, problem: dict[str, Any]) -> str:
        """Convenience: compute the canonical hash without running DMRG."""
        return hash_payload(problem)
