"""The staging database job (LEDGER Decision 20), run by ``.github/workflows/staging-db.yml``.

``qcompass-staging`` is the product's Supabase project. Its migrations and
its admin seed run from CI or the deploy job, never by hand::

    python -m ucgle_f1.db.staging migrate      # P3-01 runner (ucgle_f1.db.migrate.apply_migrations)
    python -m ucgle_f1.db.staging seed-admin   # ucgle_f1.db.seed_admin, ADMIN_EMAIL

Secrets come only from the environment, under the names in PLAN Part 6
(R9): ``migrate`` needs ``DATABASE_URL``; ``seed-admin`` needs
``DATABASE_URL``, ``SUPABASE_URL`` and ``SUPABASE_SERVICE_ROLE_KEY``. When
one is missing or blank, the command prints ``BLOCKED-ON-JAMES:<NAME>`` (one
line per missing name), connects to nothing, changes nothing and exits 0.

Under GitHub Actions (``GITHUB_ACTIONS=true``) each command first masks the
values it derives from those secrets, which Actions does not recognise as
secrets by itself: the ``DATABASE_URL`` password, as written and
percent-decoded, and each secret without surrounding whitespace. Nothing
here prints a secret.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO
from urllib.parse import unquote, urlsplit

import httpx
import psycopg
from psycopg.conninfo import conninfo_to_dict

from .migrate import apply_migrations
from .seed_admin import ADMIN_EMAIL, SeedError, seed_admin

MIGRATE_NEEDS = ("DATABASE_URL",)
SEED_NEEDS = ("DATABASE_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")


def missing(names: Sequence[str], env: Mapping[str, str]) -> list[str]:
    return [name for name in names if not env.get(name, "").strip()]


def _password_forms(url: str) -> set[str]:
    forms: set[str] = set()
    try:
        raw = urlsplit(url).password
    except ValueError:
        raw = None
    if raw:
        forms.update({raw, unquote(raw)})
    try:
        parsed = conninfo_to_dict(url).get("password")
    except Exception:  # an unparseable URL fails later, without its value
        parsed = None
    if parsed:
        forms.add(str(parsed))
    return forms


def derived_values(names: Sequence[str], env: Mapping[str, str]) -> list[str]:
    """Values derived from the secrets in ``names`` that a log could show."""
    values: set[str] = set()
    for name in names:
        value = env.get(name, "")
        if value.strip():
            values.add(value.strip())
            if name == "SUPABASE_URL":
                values.add(value.strip().rstrip("/"))
    if env.get("DATABASE_URL", "").strip() and "DATABASE_URL" in names:
        values.update(_password_forms(env["DATABASE_URL"].strip()))
    # One workflow command per line; a value with a line break is masked line by line.
    lines = {line for value in values for line in value.splitlines() if line.strip()}
    return sorted(lines)


def mask(names: Sequence[str], env: Mapping[str, str], out: TextIO) -> None:
    if env.get("GITHUB_ACTIONS") != "true":
        return
    for value in derived_values(names, env):
        out.write(f"::add-mask::{value}\n")
    out.flush()


def _blocked(names: list[str], env: Mapping[str, str], out: TextIO, what: str) -> int:
    for name in names:
        out.write(f"BLOCKED-ON-JAMES:{name}\n")
    summary = env.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:
            with Path(summary).open("a", encoding="utf-8") as fh:
                fh.write(f"### Staging database: {what} not run\n\n")
                for name in names:
                    fh.write(f"`BLOCKED-ON-JAMES:{name}` (a `staging` environment secret)\n\n")
        except OSError:
            pass
    return 0


def _failed(what: str, exc: Exception, err: TextIO) -> int:
    # Driver and HTTP errors name hosts and SQLSTATEs, never the password or
    # the key; under Actions the derived values are masked as well.
    err.write(f"{what} failed: {type(exc).__name__}: {exc}\n")
    return 1


def run_migrate(env: Mapping[str, str], out: TextIO, err: TextIO) -> int:
    absent = missing(MIGRATE_NEEDS, env)
    if absent:
        return _blocked(absent, env, out, "migrations")
    mask(MIGRATE_NEEDS, env, out)
    try:
        applied = apply_migrations(env["DATABASE_URL"].strip())
    except psycopg.Error as exc:
        return _failed("migrations", exc, err)
    for version in applied:
        out.write(f"applied {version}\n")
    out.write(f"migrations: {len(applied)} applied\n")
    return 0


def run_seed(env: Mapping[str, str], out: TextIO, err: TextIO, *, email: str = ADMIN_EMAIL,
             transport: httpx.BaseTransport | None = None) -> int:
    absent = missing(SEED_NEEDS, env)
    if absent:
        return _blocked(absent, env, out, "admin seed")
    mask(SEED_NEEDS, env, out)
    try:
        result = seed_admin(
            database_url=env["DATABASE_URL"].strip(),
            supabase_url=env["SUPABASE_URL"],
            service_role_key=env["SUPABASE_SERVICE_ROLE_KEY"].strip(),
            email=email,
            transport=transport,
        )
    except SeedError as exc:
        err.write(f"admin seed failed: {exc}\n")
        return 1
    except (psycopg.Error, httpx.HTTPError) as exc:
        return _failed("admin seed", exc, err)
    user = "created" if result.user_created else "already present, unchanged"
    role = "granted" if result.role_granted else "already held, unchanged"
    confirmed = "yes" if result.email_confirmed else "no"
    out.write(f"admin user {result.user_id}: {user} (email confirmed: {confirmed})\n")
    out.write(f"admin role: {role} (public.user_roles, as database role {result.db_role})\n")
    return 0


def main(argv: Sequence[str] | None = None, *, env: Mapping[str, str] | None = None,
         out: TextIO | None = None, err: TextIO | None = None,
         transport: httpx.BaseTransport | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ucgle_f1.db.staging", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="apply supabase/migrations with the P3-01 runner")
    seed = sub.add_parser("seed-admin", help="ensure the admin user and its admin role")
    seed.add_argument("--email", default=ADMIN_EMAIL,
                      help="default: ADMIN_EMAIL (LEDGER Decision 20)")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    env = os.environ if env is None else env
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    if args.command == "migrate":
        return run_migrate(env, out, err)
    return run_seed(env, out, err, email=args.email, transport=transport)


if __name__ == "__main__":
    sys.exit(main())
