"""Package-suite Postgres fixtures (P3-01).

The router's calibration history, pricing cache and free-tier ledger and the
bench leaderboard live in Postgres. Tests get a real one: the same
throwaway database the backend suite uses (``TEST_DATABASE_URL`` or a local
cluster started by ``ucgle_f1.db``; never a pre-existing ``DATABASE_URL``,
R13), migrated from ``supabase/migrations``.

``pg_engine`` is per-test isolated: the package tables are truncated after
each test that uses it. Only tests that ask for it (directly or through a
store fixture) start the database.

This file lives outside every ``packages/*/src`` tree, so the import-boundary
guard (packages never import ``ucgle_f1``) still holds for shipped code.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from qcompass_core.db import engine_from_env
from ucgle_f1.db.pytest_plugin import PACKAGE_TABLES, scratch_database, truncate

if TYPE_CHECKING:
    from sqlalchemy import Engine


@pytest.fixture(scope="session")
def _qcompass_pg_session() -> Iterator[Engine]:
    with scratch_database() as url:
        if not url:
            pytest.fail(
                "no Postgres for the package stores: set TEST_DATABASE_URL or install "
                "the PostgreSQL server binaries (BLOCKED-ON-JAMES:DATABASE_URL otherwise)",
            )
        yield engine_from_env()


@pytest.fixture
def pg_engine(_qcompass_pg_session: Engine) -> Iterator[Engine]:
    """A SQLAlchemy engine on the migrated test database; tables cleaned after."""
    url = _qcompass_pg_session.url.render_as_string(hide_password=False)
    # Tenancy rows some RLS tests create are cleaned too.
    tables = (*PACKAGE_TABLES, "public.tenant_members", "public.tenants", "auth.users")
    truncate(url, tables)
    yield _qcompass_pg_session
    truncate(url, tables)
