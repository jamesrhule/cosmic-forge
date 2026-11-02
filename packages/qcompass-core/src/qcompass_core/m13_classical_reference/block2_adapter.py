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

    block2 is GPL-3.0-only, so QCompass never installs it into its own
    environment (PLAN R11): the DMRG reference runs as a separate process,
    delivered by P2-06. The soft import stays for environments that
    provide pyblock2 themselves.
    """

    name: str = "block2"

    def compute(self, problem: dict[str, Any]) -> ClassicalReferenceResult:
        try:
            import pyblock2  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional
            msg = (
                "pyblock2 is not installed. block2 is GPL-3.0-only, so QCompass "
                "does not install it in-process; DMRG references run as a "
                "separate process (PLAN P2-06)."
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
