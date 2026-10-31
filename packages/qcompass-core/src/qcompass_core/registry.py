"""Plugin registry for QCompass simulation domains.

Plugins publish themselves via the ``qcompass.domains`` entry-point
group. The registry resolves names lazily and caches the lookup so
re-imports are cheap. In-process tests can register plugins
programmatically with :func:`register`; that override is purged by
:func:`reset_registry` between test cases.

Discovery order:
1. In-process registry (set by :func:`register`).
2. ``importlib.metadata.entry_points(group="qcompass.domains")``.
"""

from __future__ import annotations

from importlib import metadata
from threading import RLock
from typing import TYPE_CHECKING

from .errors import UnknownDomainError

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from .protocols import Simulation


_GROUP = "qcompass.domains"
_lock = RLock()
_inprocess: dict[str, type["Simulation"]] = {}


def register(name: str, cls: type["Simulation"]) -> None:
    """Programmatically register a :class:`Simulation` class.

    Used by tests and by callers that build plugins on the fly. The
    name is normalised to lower-case; conflicts raise :class:`ValueError`.
    """
    key = name.lower().strip()
    if not key:
        msg = "Plugin name must be a non-empty string."
        raise ValueError(msg)
    with _lock:
        if key in _inprocess:
            msg = f"In-process plugin '{key}' is already registered."
            raise ValueError(msg)
        _inprocess[key] = cls


def reset_registry() -> None:
    """Drop every in-process registration. Entry-point discoveries are unaffected."""
    with _lock:
        _inprocess.clear()


def list_domains() -> list[str]:
    """Return the sorted union of in-process + entry-point registered domains."""
    with _lock:
        names = set(_inprocess)
    for ep in _entry_points():
        names.add(ep.name.lower())
    return sorted(names)


def get_simulation(name: str) -> type["Simulation"]:
    """Look up a :class:`Simulation` class by registered ``name``.

    Raises :class:`UnknownDomainError` if no plugin matches. Lazy
    resolution: entry-point classes are only loaded when requested.
    """
    key = name.lower().strip()
    with _lock:
        cls = _inprocess.get(key)
    if cls is not None:
        return cls
    for ep in _entry_points():
        if ep.name.lower() == key:
            loaded = ep.load()
            if not isinstance(loaded, type):
                msg = (
                    f"Entry point '{ep.name}' resolved to {loaded!r}, expected a class."
                )
                raise UnknownDomainError(msg)
            return loaded
    raise UnknownDomainError(
        f"No qcompass.domains plugin named '{name}'. "
        f"Known: {list_domains()}",
    )


def _entry_points() -> list[metadata.EntryPoint]:
    """Resolve the ``qcompass.domains`` group across importlib variants."""
    try:
        eps = metadata.entry_points(group=_GROUP)
    except TypeError:
        # Older importlib_metadata returns a SelectableGroups dict on
        # Python < 3.10. We target 3.12+ but keep the fallback for the
        # backport on test machines.
        eps = metadata.entry_points().get(_GROUP, [])  # type: ignore[attr-defined]
    return list(eps)
