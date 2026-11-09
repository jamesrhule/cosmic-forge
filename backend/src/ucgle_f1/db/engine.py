"""The process-wide SQLAlchemy engine (P3-01).

``DATABASE_URL`` (R9: environment only) points at the Supabase Postgres
database, e.g. ``postgresql://postgres:…@db.<ref>.supabase.co:5432/postgres``.
``postgres://`` and ``postgresql://`` URLs are rewritten to the psycopg 3
driver. A missing URL raises :class:`DatabaseNotConfigured`, whose message is
``BLOCKED-ON-JAMES:DATABASE_URL``; HTTP layers map it to 503, and ``/readyz``
reports it. There is no fallback database (R9: no insecure default).
"""

from __future__ import annotations

import os
import threading
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from sqlalchemy import Engine, create_engine

# Every ``create_engine`` keyword this module passes (pool and connect args).
# ``qcompass_core.db.ENGINE_KWARGS`` must stay equal (REV-SF6; a test compares
# the two constants and the engines they build).
ENGINE_KWARGS: Mapping[str, Any] = MappingProxyType(
    {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10},
)

_ENGINE: Engine | None = None
_ENGINE_URL: str | None = None
_LOCK = threading.Lock()


class DatabaseNotConfigured(RuntimeError):
    def __init__(self) -> None:
        super().__init__("BLOCKED-ON-JAMES:DATABASE_URL")


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise DatabaseNotConfigured
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def get_engine() -> Engine:
    """The engine for the current ``DATABASE_URL`` (rebuilt if it changes)."""
    global _ENGINE, _ENGINE_URL
    url = database_url()
    with _LOCK:
        if _ENGINE is None or _ENGINE_URL != url:
            if _ENGINE is not None:
                _ENGINE.dispose()
            _ENGINE = create_engine(url, **ENGINE_KWARGS)
            _ENGINE_URL = url
        return _ENGINE


def reset_engine() -> None:
    global _ENGINE, _ENGINE_URL
    with _LOCK:
        if _ENGINE is not None:
            _ENGINE.dispose()
        _ENGINE = None
        _ENGINE_URL = None


__all__ = ["ENGINE_KWARGS", "DatabaseNotConfigured", "database_url", "get_engine", "reset_engine"]
