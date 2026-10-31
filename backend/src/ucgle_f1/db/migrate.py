"""Apply ``supabase/migrations`` to a Postgres database (P3-01).

Applied versions are recorded in ``supabase_migrations.schema_migrations``,
the table the Supabase CLI uses, so this runner and ``supabase db push``
agree on what has been applied. Every migration is idempotent (R13), so
re-running is safe.

Against a database without Supabase's platform objects (a local cluster, CI's
``postgres:16`` service) the runner first applies ``supabase_shim.sql``. If
the ``pg_cron`` extension isn't installable there, ``create extension …
pg_cron`` is replaced by a no-op and the shim's ``cron`` schema stands in.
Neither substitution ever happens against a real Supabase project.

Down migrations live in ``supabase/migrations/down/<version>_*.down.sql``;
:func:`rollback` applies one and forgets its version.

Usage: ``python -m ucgle_f1.db.migrate [up|down <version>]``, using ``DATABASE_URL``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import psycopg

from .engine import database_url

_HERE = Path(__file__).resolve().parent
SHIM = _HERE / "supabase_shim.sql"
_PG_CRON = re.compile(r"create\s+extension\s+if\s+not\s+exists\s+pg_cron[^;]*;", re.IGNORECASE)


def migrations_dir() -> Path:
    for parent in _HERE.parents:
        cand = parent / "supabase" / "migrations"
        if cand.is_dir():
            return cand
    raise FileNotFoundError("supabase/migrations not found above " + str(_HERE))


def _libpq_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _versions(conn: psycopg.Connection) -> set[str]:
    conn.execute("create schema if not exists supabase_migrations")
    conn.execute(
        "create table if not exists supabase_migrations.schema_migrations "
        "(version text primary key, name text, statements text[])"
    )
    return {r[0] for r in conn.execute("select version from supabase_migrations.schema_migrations")}


def _is_supabase(conn: psycopg.Connection) -> bool:
    row = conn.execute("select 1 from pg_namespace where nspname = 'auth'").fetchone()
    return row is not None


def _pg_cron_available(conn: psycopg.Connection) -> bool:
    row = conn.execute("select 1 from pg_available_extensions where name = 'pg_cron'").fetchone()
    return row is not None


def apply_migrations(url: str | None = None, directory: Path | None = None) -> list[str]:
    """Apply every pending migration in version order; return the versions applied."""
    url = _libpq_url(url or database_url())
    directory = directory or migrations_dir()
    applied: list[str] = []
    with psycopg.connect(url, autocommit=True) as conn:
        if not _is_supabase(conn):
            conn.execute(SHIM.read_text(encoding="utf-8"))
        have_cron = _pg_cron_available(conn)
        done = _versions(conn)
        for path in sorted(directory.glob("*.sql")):
            version = path.name.split("_", 1)[0]
            if version in done:
                continue
            sql = path.read_text(encoding="utf-8")
            if not have_cron:
                sql = _PG_CRON.sub("select 1; -- pg_cron unavailable (local harness)", sql)
            with conn.transaction():
                conn.execute(sql)
                conn.execute(
                    "insert into supabase_migrations.schema_migrations (version, name) values (%s, %s)",
                    (version, path.stem.split("_", 1)[-1]),
                )
            applied.append(version)
    return applied


def rollback(version: str, url: str | None = None, directory: Path | None = None) -> None:
    """Apply ``down/<version>_*.down.sql`` and forget the version."""
    url = _libpq_url(url or database_url())
    directory = directory or migrations_dir()
    downs = sorted((directory / "down").glob(f"{version}_*.down.sql"))
    if not downs:
        raise FileNotFoundError(f"no down migration for {version}")
    with psycopg.connect(url, autocommit=True) as conn, conn.transaction():
        conn.execute(downs[0].read_text(encoding="utf-8"))
        conn.execute("delete from supabase_migrations.schema_migrations where version = %s", (version,))


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "up":
        for v in apply_migrations():
            print(f"applied {v}")
        return 0
    if argv[0] == "down" and len(argv) == 2:
        rollback(argv[1])
        print(f"rolled back {argv[1]}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
