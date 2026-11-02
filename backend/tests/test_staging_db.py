"""The staging database job (LEDGER Decision 20): migrations and the admin seed.

Runs against the backend's throwaway Postgres (``ucgle_f1.db.pytest_plugin``,
with ``supabase_shim.sql``) and a stand-in for Supabase Auth's Admin API that
keeps its users in that database's ``auth.users``, as Supabase Auth does, so
the migrations' triggers on ``auth.users`` and the ``user_roles`` foreign key
are the real ones. No network (``httpx.MockTransport``).
"""

from __future__ import annotations

import io
import json
import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
import psycopg
import pytest

from ucgle_f1.db import migrate as migrate_mod
from ucgle_f1.db import seed_admin as seed_mod
from ucgle_f1.db import staging
from ucgle_f1.db.migrate import migrations_dir

SUPABASE_URL = "https://stub-project.supabase.test"
SECRET_KEY = "sb_secret_TEST-ONLY-not-a-real-key-0123456789"
LEGACY_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.TEST-ONLY-signature"
DECISION_20_EMAIL = "jamesrhule@projecthumancity.com"


def _test_db() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("BLOCKED-ON-JAMES:DATABASE_URL (no test Postgres)")
    return url.replace("postgresql+psycopg://", "postgresql://")


def _sql(url: str, sql: str, *params: Any) -> list[tuple[Any, ...]]:
    with psycopg.connect(url, autocommit=True) as conn:
        cur = conn.execute(sql, params)
        return cur.fetchall() if cur.description else []


def _counts(url: str) -> tuple[int, int]:
    users = _sql(url, "select count(*) from auth.users")[0][0]
    admins = _sql(url, "select count(*) from public.user_roles where role = 'admin'")[0][0]
    return int(users), int(admins)


class FakeAuthAdmin:
    """Supabase Auth's ``/auth/v1/admin/users`` (list and create) over ``auth.users``.

    Mirrors supabase/auth ``internal/api/admin.go``: offset pages
    (``page``/``per_page``), an optional ``filter`` on the email, 422
    ``email_exists`` for a duplicate, and a create without a password.
    """

    def __init__(self, db_url: str, key: str = SECRET_KEY) -> None:
        self.db_url = db_url
        self.key = key
        self.requests: list[httpx.Request] = []
        self.created: list[dict[str, Any]] = []
        self.ignore_filter_once = False  # a listing that misses the user (race / old server)
        self.detached = False  # users that are not in this database (another project)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.host != urlsplit(SUPABASE_URL).hostname or request.url.scheme != "https":
            return httpx.Response(404)
        if request.headers.get("apikey") != self.key:
            return httpx.Response(401, json={"code": 401, "error_code": "no_authorization"})
        if request.url.path != "/auth/v1/admin/users":
            return httpx.Response(404, json={"code": 404, "error_code": "not_found"})
        if request.method == "GET":
            return self._list(request)
        if request.method == "POST":
            return self._create(json.loads(request.content))
        return httpx.Response(405)

    def _list(self, request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        per_page = int(request.url.params.get("per_page", "50"))
        flt = request.url.params.get("filter", "")
        if self.ignore_filter_once and flt:
            self.ignore_filter_once = False
            return httpx.Response(200, json={"aud": "authenticated", "users": []})
        rows = _sql(
            self.db_url,
            "select id, email, email_confirmed_at from auth.users"
            " where %s = '' or email ilike '%%' || %s || '%%'"
            " order by created_at desc, id limit %s offset %s",
            flt,
            flt,
            per_page,
            (page - 1) * per_page,
        )
        users = [
            {
                "id": str(r[0]),
                "email": r[1],
                "email_confirmed_at": r[2] and r[2].isoformat(),
                "aud": "authenticated",
            }
            for r in rows
        ]
        return httpx.Response(200, json={"aud": "authenticated", "users": users})

    def _create(self, body: dict[str, Any]) -> httpx.Response:
        self.created.append(body)
        email = str(body.get("email", "")).lower()
        if _sql(self.db_url, "select 1 from auth.users where lower(email) = %s", email):
            return httpx.Response(
                422,
                json={
                    "code": 422,
                    "error_code": "email_exists",
                    "msg": "A user with this email address has already been registered",
                },
            )
        if self.detached:
            return httpx.Response(
                200,
                json={
                    "id": str(uuid.uuid4()),
                    "email": email,
                    "email_confirmed_at": "2026-11-02T00:00:00Z",
                },
            )
        row = _sql(
            self.db_url,
            "insert into auth.users (email, email_confirmed_at)"
            " values (%s, case when %s then now() end) returning id, email_confirmed_at",
            email,
            bool(body.get("email_confirm")),
        )[0]
        return httpx.Response(
            200,
            json={
                "id": str(row[0]),
                "email": email,
                "email_confirmed_at": row[1] and row[1].isoformat(),
            },
        )


def _env(db_url: str, **extra: str) -> dict[str, str]:
    env = {
        "DATABASE_URL": db_url,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_SERVICE_ROLE_KEY": SECRET_KEY,
    }
    env.update(extra)
    return env


def _run(
    argv: list[str], env: dict[str, str], fake: FakeAuthAdmin | None = None
) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    transport = fake.transport() if fake else httpx.MockTransport(_no_network)
    rc = staging.main(argv, env=env, out=out, err=err, transport=transport)
    return rc, out.getvalue(), err.getvalue()


def _no_network(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"unexpected request {request.method} {request.url.path}")


def _no_secret_in(text: str, *secrets: str) -> None:
    for secret in secrets:
        assert secret not in text


# ── The seed ────────────────────────────────────────────────────────────────


def test_admin_email_is_decision_20s() -> None:
    assert seed_mod.ADMIN_EMAIL == DECISION_20_EMAIL
    assert staging.ADMIN_EMAIL is seed_mod.ADMIN_EMAIL  # the CLI's default


def test_seed_creates_the_admin_once_with_no_password_and_grants_the_role() -> None:
    db = _test_db()
    fake = FakeAuthAdmin(db)
    rc, out, err = _run(["seed-admin"], _env(db), fake)
    assert rc == 0, err

    assert len(fake.created) == 1
    assert fake.created[0] == {"email": DECISION_20_EMAIL, "email_confirm": True}  # no password
    rows = _sql(db, "select id, email, email_confirmed_at from auth.users")
    assert len(rows) == 1
    user_id, email, confirmed_at = rows[0]
    assert email == DECISION_20_EMAIL
    assert confirmed_at is not None
    roles = _sql(
        db,
        "select role::text, granted_by from public.user_roles where user_id = %s order by role",
        user_id,
    )
    # 'viewer' comes from main's on_auth_user_created trigger; 'admin' from the seed.
    assert roles == [("admin", None), ("viewer", None)]
    assert _sql(db, "select public.has_role(%s, 'admin')", user_id) == [(True,)]

    assert out == (
        f"admin user {user_id}: created (email confirmed: yes)\n"
        "admin role: granted (public.user_roles, as database role service_role)\n"
    )
    # sb_secret keys go on the apikey header only (Supabase API-key guide).
    assert all("authorization" not in r.headers for r in fake.requests)
    _no_secret_in(out + err, SECRET_KEY)


def test_seed_is_idempotent_on_rerun() -> None:
    db = _test_db()
    fake = FakeAuthAdmin(db)
    assert _run(["seed-admin"], _env(db), fake)[0] == 0
    first_user = _sql(db, "select id from auth.users")[0][0]
    fake.created.clear()

    rc, out, err = _run(["seed-admin"], _env(db), fake)
    assert rc == 0, err
    assert fake.created == []  # found, not created again
    assert _counts(db) == (1, 1)
    assert out == (
        f"admin user {first_user}: already present, unchanged (email confirmed: yes)\n"
        "admin role: already held, unchanged (public.user_roles, as database role service_role)\n"
    )


def test_seed_reuses_a_user_who_signed_up_and_leaves_it_unchanged() -> None:
    db = _test_db()
    user_id = _sql(
        db, "insert into auth.users (email) values (%s) returning id", DECISION_20_EMAIL.upper()
    )[0][0]
    fake = FakeAuthAdmin(db)
    rc, out, err = _run(["seed-admin"], _env(db), fake)
    assert rc == 0, err
    assert fake.created == []
    assert all(r.method == "GET" for r in fake.requests)
    assert _sql(db, "select email, email_confirmed_at from auth.users") == [
        (DECISION_20_EMAIL.upper(), None)
    ]
    assert _sql(db, "select public.has_role(%s, 'admin')", user_id) == [(True,)]
    assert out.startswith(
        f"admin user {user_id}: already present, unchanged (email confirmed: no)\n"
    )


def test_seed_handles_email_exists_from_the_create() -> None:
    """The user appears between the lookup and the create (or the filter missed it)."""
    db = _test_db()
    user_id = _sql(
        db, "insert into auth.users (email) values (%s) returning id", DECISION_20_EMAIL
    )[0][0]
    fake = FakeAuthAdmin(db)
    fake.ignore_filter_once = True
    rc, out, err = _run(["seed-admin"], _env(db), fake)
    assert rc == 0, err
    assert len(fake.created) == 1  # answered 422 email_exists, nothing created
    assert _counts(db) == (1, 1)
    assert out.startswith(f"admin user {user_id}: already present, unchanged")


def test_seed_pages_through_the_user_list(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _test_db()
    for i in range(5):
        _sql(
            db,
            "insert into auth.users (email, created_at)"
            " values (%s, now() + make_interval(secs => %s))",
            f"other{i}@example.test",
            i,
        )
    user_id = _sql(
        db,
        "insert into auth.users (email, created_at) values (%s, now() - interval '1 day')"
        " returning id",
        DECISION_20_EMAIL,
    )[0][0]
    monkeypatch.setattr(seed_mod, "_PER_PAGE", 2)
    fake = FakeAuthAdmin(db)
    with seed_mod.AuthAdmin(SUPABASE_URL, SECRET_KEY, transport=fake.transport()) as auth:
        found = auth.find_user(DECISION_20_EMAIL, use_filter=False)
    assert found is not None and found["id"] == str(user_id)
    assert len(fake.requests) == 3  # pages 1-2 hold the five newer users


def test_seed_sends_a_legacy_jwt_key_as_bearer_too() -> None:
    db = _test_db()
    fake = FakeAuthAdmin(db, key=LEGACY_KEY)
    rc, _, err = _run(["seed-admin"], _env(db, SUPABASE_SERVICE_ROLE_KEY=LEGACY_KEY), fake)
    assert rc == 0, err
    assert all(r.headers["authorization"] == f"Bearer {LEGACY_KEY}" for r in fake.requests)


def test_seed_refuses_when_supabase_url_and_database_url_are_different_projects() -> None:
    db = _test_db()
    fake = FakeAuthAdmin(db)
    fake.detached = True
    rc, out, err = _run(["seed-admin"], _env(db), fake)
    assert rc == 1
    assert out == ""
    assert "SUPABASE_URL and DATABASE_URL name different projects" in err
    assert _counts(db) == (0, 0)


def test_seed_reports_an_auth_error_without_the_key() -> None:
    db = _test_db()
    fake = FakeAuthAdmin(db, key="sb_secret_the-right-one")
    rc, out, err = _run(["seed-admin"], _env(db), fake)  # sends SECRET_KEY: refused
    assert rc == 1
    assert err == "admin seed failed: Supabase Auth user lookup failed: HTTP 401 no_authorization\n"
    _no_secret_in(out + err, SECRET_KEY)
    assert _counts(db) == (0, 0)


@pytest.mark.parametrize(
    "url",
    [
        "http://stub-project.supabase.test",
        "stub-project.supabase.test",
        "https://stub-project.supabase.test/rest/v1",
    ],
)
def test_seed_sends_the_key_only_to_an_https_project_url(url: str) -> None:
    db = _test_db()
    rc, out, err = _run(["seed-admin"], _env(db, SUPABASE_URL=url))  # any request fails the test
    assert rc == 1
    assert out == ""
    assert err.startswith("admin seed failed: SUPABASE_URL must be the project's https:// URL")
    assert url not in err
    assert _counts(db) == (0, 0)


def test_seed_email_override_is_validated() -> None:
    db = _test_db()
    rc, _, err = _run(["seed-admin", "--email", "not-an-email"], _env(db))
    assert rc == 1
    assert err == "admin seed failed: the admin email is not an email address\n"
    assert _counts(db) == (0, 0)


# ── R9: a missing secret blocks, connects to nothing, writes nothing ────────


@pytest.mark.parametrize("name", staging.SEED_NEEDS)
@pytest.mark.parametrize("absent_as", ["unset", "empty", "blank"])
def test_seed_missing_secret_is_blocked_on_james(
    name: str, absent_as: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = _test_db()
    env = _env(db)
    if absent_as == "unset":
        del env[name]
    else:
        env[name] = "" if absent_as == "empty" else "  \n"
    connects: list[str] = []
    monkeypatch.setattr(seed_mod.psycopg, "connect", lambda *a, **k: connects.append("db"))
    rc, out, err = _run(["seed-admin"], env)  # any HTTP request fails the test
    assert (rc, out, err) == (0, f"BLOCKED-ON-JAMES:{name}\n", "")
    assert connects == []
    monkeypatch.undo()
    assert _counts(db) == (0, 0)


def test_seed_lists_every_missing_secret_and_writes_the_step_summary(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    rc, out, err = _run(["seed-admin"], {"GITHUB_STEP_SUMMARY": str(summary)})
    assert (rc, err) == (0, "")
    assert out == "".join(f"BLOCKED-ON-JAMES:{n}\n" for n in staging.SEED_NEEDS)
    text = summary.read_text(encoding="utf-8")
    assert text.startswith("### Staging database: admin seed not run")
    for name in staging.SEED_NEEDS:
        assert f"`BLOCKED-ON-JAMES:{name}`" in text


@pytest.mark.parametrize("absent_as", ["unset", "empty"])
def test_migrate_missing_database_url_is_blocked_on_james(
    absent_as: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_a: Any, **_k: Any) -> list[str]:
        raise AssertionError("apply_migrations must not run")

    monkeypatch.setattr(staging, "apply_migrations", boom)
    env = {} if absent_as == "unset" else {"DATABASE_URL": ""}
    rc, out, err = _run(["migrate"], env)
    assert (rc, out, err) == (0, "BLOCKED-ON-JAMES:DATABASE_URL\n", "")


def test_migrate_uses_the_p301_runner() -> None:
    assert staging.apply_migrations is migrate_mod.apply_migrations


# ── Masking derived values under GitHub Actions ─────────────────────────────


def test_masks_the_database_password_as_written_and_decoded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applied: list[str] = []
    monkeypatch.setattr(staging, "apply_migrations", lambda url: applied.append(url) or [])
    url = "postgresql://postgres.ref:p%40ss%2Fw0rd@pooler.example.test:5432/postgres"
    rc, out, err = _run(["migrate"], {"DATABASE_URL": f" {url}\n", "GITHUB_ACTIONS": "true"})
    assert (rc, err) == (0, "")
    assert applied == [url]
    lines = out.splitlines()
    masks = [line for line in lines if line.startswith("::add-mask::")]
    assert lines[: len(masks)] == masks  # masks come before any other output
    assert {"::add-mask::p%40ss%2Fw0rd", "::add-mask::p@ss/w0rd", f"::add-mask::{url}"} <= set(
        masks
    )
    for line in lines[len(masks) :]:
        _no_secret_in(line, "p%40ss", "p@ss")


def test_no_masking_outside_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(staging, "apply_migrations", lambda url: [])
    rc, out, _ = _run(["migrate"], {"DATABASE_URL": "postgresql://u:pw@h/db"})
    assert (rc, out) == (0, "migrations: 0 applied\n")


def test_seed_masks_derived_values_under_actions() -> None:
    db = _test_db()
    fake = FakeAuthAdmin(db)
    rc, out, err = _run(
        ["seed-admin"], _env(db, SUPABASE_URL=SUPABASE_URL + "/", GITHUB_ACTIONS="true"), fake
    )
    assert rc == 0, err
    masks = {line for line in out.splitlines() if line.startswith("::add-mask::")}
    assert {
        f"::add-mask::{SECRET_KEY}",
        f"::add-mask::{SUPABASE_URL}",
        f"::add-mask::{db}",
    } <= masks
    rest = [line for line in out.splitlines() if not line.startswith("::add-mask::")]
    assert len(rest) == 2
    assert rest[0].startswith("admin user ") and rest[1].startswith("admin role: granted")
    _no_secret_in("\n".join(rest) + err, SECRET_KEY)


# ── End to end: an empty database, as qcompass-staging is today ─────────────


@pytest.fixture
def empty_database() -> Iterator[str]:
    """A new, empty database on the test server (Decision 20: 'The database is empty')."""
    base = _test_db()
    name = f"staging_sim_{uuid.uuid4().hex[:12]}"
    _sql(base, f'create database "{name}"')
    parts = urlsplit(base)
    try:
        yield urlunsplit(parts._replace(path=f"/{name}"))
    finally:
        _sql(base, f'drop database if exists "{name}" with (force)')


def test_empty_database_migrate_then_seed(empty_database: str) -> None:
    db = empty_database
    versions = sorted(p.name.split("_", 1)[0] for p in migrations_dir().glob("*.sql"))

    rc, out, err = _run(["migrate"], {"DATABASE_URL": db})
    assert rc == 0, err
    assert (
        out
        == "".join(f"applied {v}\n" for v in versions) + f"migrations: {len(versions)} applied\n"
    )
    recorded = [
        r[0]
        for r in _sql(db, "select version from supabase_migrations.schema_migrations order by 1")
    ]
    assert recorded == versions

    rc, out, err = _run(["migrate"], {"DATABASE_URL": db})  # nothing pending
    assert (rc, out, err) == (0, "migrations: 0 applied\n", "")

    fake = FakeAuthAdmin(db)
    rc, out, err = _run(["seed-admin"], _env(db), fake)
    assert rc == 0, err
    user_id = _sql(db, "select id from auth.users where email = %s", DECISION_20_EMAIL)[0][0]
    assert out.startswith(f"admin user {user_id}: created")
    assert _sql(db, "select public.has_role(%s, 'admin')", user_id) == [(True,)]
    rc, out, err = _run(["seed-admin"], _env(db), fake)
    assert rc == 0, err
    assert "already present, unchanged" in out and "already held, unchanged" in out
    assert _counts(db) == (1, 1)
