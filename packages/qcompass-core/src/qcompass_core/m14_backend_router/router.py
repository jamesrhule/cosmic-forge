"""M14 — Router.

Resolves a :class:`BackendRequest` against the catalogue of built-in
backends + provider-registered backends. Cost & calibration are
captured from each :class:`QBackend` instance directly so the router
remains agnostic of vendor APIs.
"""

from __future__ import annotations

from threading import RLock
from typing import TYPE_CHECKING

from ..errors import BackendUnavailableError
from ..manifest import BackendRequest

if TYPE_CHECKING:  # pragma: no cover
    from ..protocols import QBackend, QProvider


_lock = RLock()
_providers: dict[str, "QProvider"] = {}
_builtin: dict[str, "QBackend"] = {}


def reset_router() -> None:
    """Clear every provider registration. Used by tests."""
    with _lock:
        _providers.clear()
        _builtin.clear()


def register_provider(provider: "QProvider") -> None:
    """Register a :class:`QProvider`. The provider's name becomes the lookup key."""
    with _lock:
        if provider.name in _providers:
            msg = f"Provider '{provider.name}' is already registered."
            raise ValueError(msg)
        _providers[provider.name] = provider


def _ensure_builtins_loaded() -> None:
    if _builtin:
        return
    from .backends import ClassicalCPUBackend, LocalAerBackend

    cpu = ClassicalCPUBackend()
    aer = LocalAerBackend()
    _builtin[cpu.name] = cpu  # type: ignore[assignment]
    _builtin[aer.name] = aer  # type: ignore[assignment]


def available_backends() -> list[str]:
    """Sorted catalogue of built-ins + every registered provider's backends."""
    with _lock:
        _ensure_builtins_loaded()
        names = set(_builtin)
        for prov in _providers.values():
            try:
                names.update(prov.list_backends())
            except Exception:  # pragma: no cover - skip flaky provider
                continue
    return sorted(names)


def get_backend(request: BackendRequest) -> "QBackend":
    """Resolve a :class:`BackendRequest` to a concrete :class:`QBackend`.

    Ordering:
    1. ``request.target`` if explicit and reachable.
    2. ``request.priority`` list, in order.
    3. The single matching built-in if ``kind`` is unambiguous.

    Raises :class:`BackendUnavailableError` if nothing matches.
    """
    with _lock:
        _ensure_builtins_loaded()
        candidates = list(_builtin.values())
        for prov in _providers.values():
            try:
                for name in prov.list_backends():
                    candidates.append(prov.get_backend(name))
            except Exception:  # pragma: no cover - skip flaky provider
                continue

    by_name = {b.name: b for b in candidates}

    if request.target:
        backend = by_name.get(request.target)
        if backend is None:
            msg = f"Backend '{request.target}' not registered."
            raise BackendUnavailableError(msg)
        return backend

    for name in request.priority:
        if name in by_name:
            return by_name[name]

    if request.kind == "classical":
        return _builtin["classical_cpu"]
    if request.kind == "quantum_simulator":
        if "local_aer" in by_name:
            return by_name["local_aer"]
    if request.kind == "auto":
        # Prefer simulator; degrade to classical fallback.
        if "local_aer" in by_name:
            return by_name["local_aer"]
        return _builtin["classical_cpu"]

    msg = (
        f"No backend satisfies request kind={request.kind!r}; "
        f"available: {sorted(by_name)}"
    )
    raise BackendUnavailableError(msg)


class Router:
    """Object-oriented facade for code that prefers an instance API."""

    def __init__(self) -> None:
        _ensure_builtins_loaded()

    def available(self) -> list[str]:
        return available_backends()

    def resolve(self, request: BackendRequest) -> "QBackend":
        return get_backend(request)

    def register(self, provider: "QProvider") -> None:
        register_provider(provider)
