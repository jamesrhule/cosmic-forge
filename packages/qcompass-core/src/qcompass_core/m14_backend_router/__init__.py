"""M14 — Backend router.

QDMI-shaped abstraction. Two built-in backends ship with
qcompass-core:

- ``classical_cpu``  — always-available no-op classical fallback.
- ``local_aer``      — qiskit-aer simulator (lazy import, optional).

Quantum providers (IBM, Azure, IonQ, …) plug in by satisfying the
:class:`QProvider` protocol and registering with :func:`register_provider`.
"""

from __future__ import annotations

from .backends import ClassicalCPUBackend, LocalAerBackend
from .router import (
    Router,
    available_backends,
    get_backend,
    register_provider,
    reset_router,
)

__all__ = [
    "ClassicalCPUBackend",
    "LocalAerBackend",
    "Router",
    "available_backends",
    "get_backend",
    "register_provider",
    "reset_router",
]
