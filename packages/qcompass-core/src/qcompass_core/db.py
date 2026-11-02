"""Engine resolution for the library-package stores (P3-01).

The router's calibration history, pricing cache and free-tier ledger and the
bench leaderboard live in Supabase Postgres (``supabase/migrations``). Each
store takes a SQLAlchemy ``Engine`` (injected by the API or worker process,
which owns the connection pool). A store built without one falls back to
:func:`engine_from_env`, which reads ``DATABASE_URL`` (R9: environment only),
the same variable and URL rules as the compute API's ``ucgle_f1.db``.

A missing URL raises :class:`DatabaseNotConfigured` whose message is
``BLOCKED-ON-JAMES:DATABASE_URL``; there is no fallback database (R9).

SQLAlchemy and psycopg are imported lazily so ``qcompass-core`` itself does
not depend on them; ``qcompass-router`` and ``qcompass-bench`` do.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy import Engine

# Every ``create_engine`` keyword this module passes (pool and connect args).
# The compute API's ``ucgle_f1.db.engine.ENGINE_KWARGS`` must stay equal
# (REV-SF6; a backend test compares the two constants and the engines).
ENGINE_KWARGS: Mapping[str, Any] = MappingProxyType(
    {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10},
)

_ENGINES: dict[str, Engine] = {}
_LOCK = threading.Lock()


class DatabaseNotConfigured(RuntimeError):
    """``DATABASE_URL`` is unset; the code path is blocked on James (R9/R14)."""

    code = "BLOCKED-ON-JAMES:DATABASE_URL"

    def __init__(self) -> None:
        super().__init__("BLOCKED-ON-JAMES:DATABASE_URL")


def sqlalchemy_url(url: str) -> str:
    """Rewrite ``postgres://`` / ``postgresql://`` to the psycopg 3 driver."""
    url = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def engine_from_env() -> Engine:
    """A pooled engine for the current ``DATABASE_URL`` (one per URL)."""
    raw = os.environ.get("DATABASE_URL", "").strip()
    if not raw:
        raise DatabaseNotConfigured
    url = sqlalchemy_url(raw)
    with _LOCK:
        engine = _ENGINES.get(url)
        if engine is None:
            from sqlalchemy import create_engine

            engine = create_engine(url, **ENGINE_KWARGS)
            _ENGINES[url] = engine
        return engine


def dispose_engines() -> None:
    """Dispose every engine built by :func:`engine_from_env` (tests, shutdown)."""
    with _LOCK:
        for engine in _ENGINES.values():
            engine.dispose()
        _ENGINES.clear()


__all__ = ["ENGINE_KWARGS", "DatabaseNotConfigured", "dispose_engines", "engine_from_env", "sqlalchemy_url"]
