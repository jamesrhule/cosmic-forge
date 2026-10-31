"""ProviderAdapter ABC + shared types.

Every adapter under :mod:`qcompass_router.providers` subclasses
``ProviderAdapter`` and guards SDK imports inside
``is_available()``. Importing the adapter MUST always succeed; the
heavy SDK only loads when ``submit()`` or ``list_backends()`` is
called and the SDK happens to be present.

PROMPT 0 v2 §STEP B refactor: ``ProviderAdapter`` inherits from
:class:`qcompass_core.protocols.QProvider` (a runtime-checkable
Protocol) so any caller that takes a ``QProvider`` accepts our
adapters via ``isinstance`` checks. The router still consumes the
richer ``list_backends() -> list[BackendInfo]`` via
:meth:`list_backend_infos`; the Protocol's
``list_backends() -> list[str]`` resolves to the names of those
``BackendInfo`` records.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

from qcompass_core.protocols import QBackend, QProvider


ProviderKind = Literal[
    "local",
    "cloud-sc",         # superconducting
    "cloud-ion",        # trapped-ion
    "cloud-neutral-atom",
    "cloud-other",
]


@dataclass
class BackendInfo:
    """Lightweight descriptor an adapter returns from ``list_backend_infos``."""

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


class ProviderAdapter(ABC, QProvider):
    """Abstract adapter every provider implementation satisfies.

    Subclass invariants:
    - ``name``: stable string used as ``BackendInfo.provider``.
    - ``kind``: one of :data:`ProviderKind`.
    - ``is_available()`` MUST NOT raise even when the SDK or
      credentials are missing — it returns ``False``.
    - ``list_backend_infos()`` returns the rich descriptors the
      router consumes; Protocol-style ``list_backends()`` returns
      just the names.
    """

    name: ClassVar[str]
    kind: ClassVar[ProviderKind]

    @abstractmethod
    def is_available(self) -> bool:
        """Return True iff the SDK is importable AND credentials
        / endpoint configuration look usable."""

    @abstractmethod
    def list_backend_infos(self) -> list[BackendInfo]:
        """Return every backend this adapter can dispatch to."""

    def list_backends(self) -> list[str]:  # type: ignore[override]
        """qcompass_core.QProvider compatibility: return backend names."""
        return [info.name for info in self.list_backend_infos()]

    def get_backend(self, name: str) -> QBackend:  # type: ignore[override]
        """qcompass_core.QProvider compatibility.

        Phase-1 contract: provider adapters do not yet construct
        :class:`qcompass_core.QBackend` instances on demand (each
        adapter dispatches via ``submit()`` directly). The method
        is exposed so ``isinstance(adapter, QProvider)`` passes at
        runtime; calling it raises ``NotImplementedError``. PROMPT
        6C lands per-provider QBackend factories.
        """
        msg = (
            f"{type(self).__name__}.get_backend({name!r}) is not yet "
            "wired; call submit() directly during PROMPT 6A/6B."
        )
        raise NotImplementedError(msg)

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
