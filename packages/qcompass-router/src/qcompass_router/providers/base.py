"""ProviderAdapter ABC + shared types.

Every adapter under :mod:`qcompass_router.providers` subclasses
``ProviderAdapter`` and guards SDK imports inside
``is_available()``. Importing the adapter MUST always succeed; the
heavy SDK only loads when ``submit()`` or ``list_backends()`` is
called and the SDK happens to be present.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal


ProviderKind = Literal[
    "local",
    "cloud-sc",         # superconducting
    "cloud-ion",        # trapped-ion
    "cloud-neutral-atom",
    "cloud-other",
]


@dataclass
class BackendInfo:
    """Lightweight descriptor an adapter returns from ``list_backends``."""

    name: str
    provider: str
    kind: ProviderKind
    fidelity_estimate: float
    queue_time_s_estimate: float
    free_tier: bool = False
    # True for SaaS simulators (sv1, dm1, tn1, quantinuum-emulator,
    # ionq-simulator, etc.). The router treats `simulator=True` like
    # the local adapters when ``require_real_hardware`` is set.
    simulator: bool = False
    notes: str = ""


@dataclass
class JobHandle:
    """Returned by ``submit``. PROMPT 6B fills out polling helpers."""

    provider: str
    backend: str
    job_id: str
    submitted_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderAdapter(ABC):
    """Abstract adapter every provider implementation satisfies.

    Subclass invariants:
    - ``name``: stable string used as ``BackendInfo.provider``.
    - ``kind``: one of :data:`ProviderKind`.
    - ``is_available()`` MUST NOT raise even when the SDK or
      credentials are missing — it returns ``False``.
    - ``list_backends()`` raises ``ImportError`` if invoked
      without the SDK installed.
    """

    name: ClassVar[str]
    kind: ClassVar[ProviderKind]

    @abstractmethod
    def is_available(self) -> bool:
        """Return True iff the SDK is importable AND credentials
        / endpoint configuration look usable."""

    @abstractmethod
    def list_backends(self) -> list[BackendInfo]:
        """Return every backend this adapter can dispatch to."""

    @abstractmethod
    def estimate_cost_stub(self, circuit: object, shots: int) -> float:
        """Return a dollar estimate for ``shots`` of ``circuit``.

        PROMPT 6A uses the static seed in
        :mod:`qcompass_router.pricing_stub`; PROMPT 6B replaces
        with circuit-aware live pricing.
        """

    @abstractmethod
    def submit(
        self,
        circuit: object,
        shots: int,
        backend: str,
    ) -> JobHandle:
        """Submit ``circuit`` to ``backend``; return a job handle.

        Raises ``ImportError`` when the SDK is absent and
        ``RuntimeError`` when credentials cannot be resolved.
        """
