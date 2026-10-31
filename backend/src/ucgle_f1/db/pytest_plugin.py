"""Pytest plugin: every backend test session runs against a real Postgres (P3-01).

Safety (R13): tests NEVER use a pre-existing ``DATABASE_URL``, which might
be a real database. They use ``TEST_DATABASE_URL`` (CI's throwaway
``postgres:16`` service) or start a local cluster, apply the migrations, and
only then point ``DATABASE_URL`` at it for this process. Tables are
truncated after each test for isolation.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from .engine import reset_engine
from .local import find_bindir, start_local_postgres
from .migrate import apply_migrations

# Tables the test suite writes; truncated after each test.
_TEST_TABLES = (
    "public.api_keys", "public.tenant_budgets", "public.scans",
    "public.agent_hypotheses", "public.agent_plans", "public.agent_approval_tokens",
    "public.agent_run_links", "public.agent_tool_calls", "public.agent_patches",
    "public.tenant_members", "public.tenants", "auth.users",
)


def _reset_singletons() -> None:
    reset_engine()
    try:
        from ucgle_f1.m8_agent.auth import reset_auth_store
        from ucgle_f1.m8_agent.memory.store import reset_store
        from ucgle_f1.m8_agent.scans import reset_scan_registry
    except ImportError:  # pragma: no cover - backend without the agent extras
        return
    reset_auth_store()
    reset_scan_registry()
    reset_store()


@pytest.fixture(scope="session", autouse=True)
def _qcompass_postgres() -> Iterator[str | None]:
    previous = os.environ.get("DATABASE_URL")
    started = None
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if find_bindir() is None:
            # No server available: DB-backed tests will report
            # BLOCKED-ON-JAMES:DATABASE_URL instead of touching a real DB.
            os.environ.pop("DATABASE_URL", None)
            yield None
            return
        started = start_local_postgres()
        url = started.url
    os.environ["DATABASE_URL"] = url
    apply_migrations(url)
    _reset_singletons()
    try:
        yield url
    finally:
        _reset_singletons()
        if started is not None:
            started.stop()
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


@pytest.fixture(autouse=True)
def _qcompass_clean_tables(_qcompass_postgres: str | None) -> Iterator[None]:
    yield
    if not _qcompass_postgres:
        return
    import psycopg

    with psycopg.connect(_qcompass_postgres.replace("postgresql+psycopg://", "postgresql://"), autocommit=True) as conn:
        conn.execute("truncate " + ", ".join(_TEST_TABLES) + " restart identity cascade")
    _reset_singletons()
