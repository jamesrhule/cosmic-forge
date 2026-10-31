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

PROMPT 6A compatibility (P0-02 router unification): 6A-style adapters
override ``list_backends()`` to return ``BackendInfo`` records that
carry only ``provider`` + ``name``. :meth:`list_backend_infos` accepts
that shape, and the router fills the missing ``kind`` /
``fidelity_estimate`` / ``queue_time_s_estimate`` from the adapter's
kind priors (:data:`KIND_FIDELITY_PRIOR`, :data:`KIND_QUEUE_PRIOR_S`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, ClassVar, Literal

from qcompass_core.protocols import QBackend, QProvider


ProviderKind = Literal[
    "local",
    "cloud-sc",         # superconducting
    "cloud-ion",        # trapped-ion
    "cloud-neutral-atom",
    "cloud-other",
]


# Priors used when a backend descriptor does not carry its own
# fidelity / queue estimate (PROMPT 6A). Calibrated adapters fill the
# fields from the pricing seed and never hit these.
KIND_FIDELITY_PRIOR: dict[str, float] = {
    "local": 1.0,
    "cloud-sc": 0.97,
    "cloud-ion": 0.99,
    "cloud-neutral-atom": 0.96,
    "cloud-other": 0.97,
}
KIND_QUEUE_PRIOR_S: dict[str, float] = {
    "local": 0.0,
    "cloud-sc": 600.0,
    "cloud-ion": 900.0,
    "cloud-neutral-atom": 600.0,
    "cloud-other": 600.0,
}
_UNKNOWN_KIND_FIDELITY = 0.95
_UNKNOWN_KIND_QUEUE_S = 600.0


@dataclass
class BackendInfo:
    """Lightweight descriptor an adapter returns from ``list_backend_infos``.

    ``kind`` / ``fidelity_estimate`` / ``queue_time_s_estimate`` may be
    left as ``None`` (the PROMPT 6A shape); :meth:`with_priors` fills
    them from the owning adapter's kind.
    """

    name: str
    provider: str
    kind: ProviderKind | None = None
    fidelity_estimate: float | None = None
    queue_time_s_estimate: float | None = None
    free_tier: bool = False
    # True for SaaS simulators (sv1, dm1, tn1, quantinuum-emulator,
    # ionq-simulator, etc.). The router treats `simulator=True` like
    # the local adapters when ``require_real_hardware`` is set.
    simulator: bool = False
    notes: str = ""

    def with_priors(self, kind: str) -> "BackendInfo":
        """Return a copy whose unset fields come from ``kind``'s priors."""
        resolved_kind = self.kind or kind
        return replace(
            self,
            kind=resolved_kind,  # type: ignore[arg-type]
            fidelity_estimate=(
                self.fidelity_estimate
                if self.fidelity_estimate is not None
                else KIND_FIDELITY_PRIOR.get(resolved_kind, _UNKNOWN_KIND_FIDELITY)
            ),
            queue_time_s_estimate=(
                self.queue_time_s_estimate
                if self.queue_time_s_estimate is not None
                else KIND_QUEUE_PRIOR_S.get(resolved_kind, _UNKNOWN_KIND_QUEUE_S)
            ),
        )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobHandle:
    """Returned by ``submit``. PROMPT 6B fills out polling helpers."""

    provider: str
    backend: str
    job_id: str
    submitted_at: str = field(default_factory=_utc_now_iso)
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

    def list_backend_infos(self) -> list[BackendInfo]:
        """Return every backend this adapter can dispatch to.

        Shipped adapters override this. A PROMPT 6A-style adapter that
        overrides ``list_backends()`` to return ``BackendInfo`` records
        is accepted as-is (records missing fields are completed by
        :meth:`BackendInfo.with_priors` in the router).
        """
        if type(self).list_backends is ProviderAdapter.list_backends:
            msg = (
                f"{type(self).__name__} must override list_backend_infos() "
                "(or, PROMPT 6A style, list_backends() returning BackendInfo)."
            )
            raise NotImplementedError(msg)
        out: list[BackendInfo] = []
        for item in self.list_backends():
            if isinstance(item, BackendInfo):
                out.append(item)
            else:
                out.append(BackendInfo(name=str(item), provider=self.name))
        return out

    def list_backends(self) -> list[str]:  # type: ignore[override]
        """qcompass_core.QProvider compatibility: return backend names."""
        return [info.name for info in self.list_backend_infos()]

    def estimate_cost_for(self, backend: str, shots: int) -> float | None:
        """Per-backend price override (PROMPT 6A hook).

        ``None`` (the default) means "use the pricing engine / seed".
        Adapters that know a backend's price return a dollar figure,
        which the router prefers over the seed.
        """
        return None

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
