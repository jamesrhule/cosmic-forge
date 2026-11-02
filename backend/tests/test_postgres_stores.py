"""P3-01: backend stores on Postgres — RLS, reversible migrations, no SQLite."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import psycopg
import pytest

from ucgle_f1.db.migrate import apply_migrations, rollback
from ucgle_f1.m8_agent.auth import AuthStore
from ucgle_f1.m8_agent.scans import ScanRegistry

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
PACKAGES = Path(__file__).resolve().parents[2] / "packages"


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("no Postgres available")
    return url.replace("postgresql+psycopg://", "postgresql://")


def _user(conn: psycopg.Connection, email: str) -> str:
    return str(conn.execute("insert into auth.users (email) values (%s) returning id", (email,)).fetchone()[0])


def _as(conn: psycopg.Connection, user_id: str) -> None:
    """Act as a Supabase `authenticated` user (PostgREST's convention)."""
    conn.execute("set local role authenticated")
    conn.execute(
        "select set_config('request.jwt.claims', %s, true)",
        (json.dumps({"sub": user_id, "role": "authenticated"}),),
    )


def test_rls_scopes_scans_and_budgets_to_tenant_members() -> None:
    url = _url()
    store = AuthStore()
    scans = ScanRegistry()
    scans.submit(tenant_id="acme", domain="hep", kind="grid")
    scans.submit(tenant_id="globex", domain="hep", kind="grid")
    store.upsert_budget("acme", 10.0)
    store.upsert_budget("globex", 20.0)
    with psycopg.connect(url, autocommit=True) as conn:
        alice = _user(conn, "alice@example.test")
        mallory = _user(conn, "mallory@example.test")
    store.add_member("acme", alice, "member")

    with psycopg.connect(url) as conn:
        _as(conn, alice)
        slugs = {r[0] for r in conn.execute(
            "select t.slug from public.scans s join public.tenants t on t.id = s.tenant_id"
        )}
        budgets = conn.execute("select count(*) from public.tenant_budgets").fetchone()[0]
        keys = conn.execute("select count(*) from public.api_keys").fetchone()[0]
        conn.rollback()
    assert slugs == {"acme"}, "a member sees only their tenant's scans"
    assert budgets == 1
    assert keys == 0, "a plain member can't read API key rows"

    with psycopg.connect(url) as conn:
        _as(conn, mallory)
        assert conn.execute("select count(*) from public.scans").fetchone()[0] == 0
        conn.rollback()


def test_agent_tables_are_service_only() -> None:
    url = _url()
    with psycopg.connect(url, autocommit=True) as conn:
        uid = _user(conn, "bob@example.test")
        conn.execute(
            """insert into public.agent_hypotheses ("hypothesisId", "conversationId", text)
               values ('h1', 'c1', 'x')"""
        )
    with psycopg.connect(url) as conn:
        _as(conn, uid)
        assert conn.execute("select count(*) from public.agent_hypotheses").fetchone()[0] == 0
        conn.rollback()


def test_backend_migration_is_reversible_without_data_loss() -> None:
    url = _url()
    ScanRegistry().submit(tenant_id="acme", domain="hep", kind="keep-me")
    rollback("20261031160000", url)
    try:
        with psycopg.connect(url) as conn:
            assert conn.execute("select to_regclass('public.scans')").fetchone()[0] is None
            kept = conn.execute(
                "select kind from public._deprecated_scans_20261031160000"
            ).fetchall()
        assert ("keep-me",) in kept, "R13: rollback must not drop user data"
    finally:
        assert apply_migrations(url) == ["20261031160000"]
        with psycopg.connect(url, autocommit=True) as conn:
            # Remove the deprecated copies so later tests see a clean schema.
            for t in ("api_keys", "tenant_budgets", "scans", "agent_hypotheses", "agent_plans",
                      "agent_approval_tokens", "agent_run_links", "agent_tool_calls", "agent_patches"):
                conn.execute(f"drop table if exists public._deprecated_{t}_20261031160000 cascade")
        # SF4: 20261031200400 adds tenant_id to the agent tables this test
        # just recreated; re-apply it so later tests see the current schema.
        rollback("20261031200400", url)
        apply_migrations(url)
    assert ScanRegistry().list_all() == []


def test_no_sqlite_in_backend_deployed_code() -> None:
    offenders = []
    for py in BACKEND_SRC.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if re.search(r"^\s*import sqlite3|^\s*from sqlite3|sqlite:///", text, re.MULTILINE):
            offenders.append(str(py.relative_to(BACKEND_SRC)))
    assert offenders == [], offenders


def test_package_stores_migration_is_reversible_without_data_loss() -> None:
    url = _url()
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(
            "insert into public.bench_runs (domain, fixture, package_version, started_at,"
            " wall_seconds, provenance_hash, ok) values ('chemistry', 'keep-me', '0.2.0', now(), 1, 'h', true)"
        )
        conn.execute("insert into public.router_pricing_cache (provider) values ('ibm')")
    rollback("20261031170000", url)
    try:
        with psycopg.connect(url) as conn:
            assert conn.execute("select to_regclass('public.bench_runs')").fetchone()[0] is None
            kept = conn.execute(
                "select fixture from public._deprecated_bench_runs_20261031170000"
            ).fetchall()
            priced = conn.execute(
                "select provider from public._deprecated_router_pricing_cache_20261031170000"
            ).fetchall()
        assert kept == [("keep-me",)], "R13: rollback must not drop data"
        assert priced == [("ibm",)]
    finally:
        assert apply_migrations(url) == ["20261031170000"]
        with psycopg.connect(url, autocommit=True) as conn:
            for t in ("router_calibration_daily", "router_calibration_devices",
                      "router_pricing_cache", "router_free_tier_ledger", "bench_runs"):
                conn.execute(f"drop table if exists public._deprecated_{t}_20261031170000 cascade")
    with psycopg.connect(url, autocommit=True) as conn:
        # The re-created tables work (bench_runs' identity restarts cleanly).
        new_id = conn.execute(
            "insert into public.bench_runs (domain, fixture, package_version, started_at,"
            " wall_seconds, provenance_hash, ok) values ('chemistry', 'h2', '0.2.0', now(), 1, 'h', true)"
            " returning id"
        ).fetchone()[0]
        assert new_id >= 1
        conn.execute("truncate public.bench_runs restart identity")


def test_worker_queue_migration_is_reversible_without_data_loss() -> None:
    url = _url()
    tenant = AuthStore().ensure_tenant("acme")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(
            "insert into public.job_events (run_id, tenant_id, type) values ('run_keep', %s, 'status')",
            (tenant,),
        )
    # 20261031200300 and 20261102105000 replace functions this migration
    # created (and add overloads of them): roll them back first, newest first.
    rollback("20261102105000", url)
    rollback("20261031200300", url)
    rollback("20261031180000", url)
    try:
        with psycopg.connect(url) as conn:
            assert conn.execute("select to_regclass('public.job_events')").fetchone()[0] is None
            assert conn.execute(
                "select run_id from public._deprecated_job_events_20261031180000"
            ).fetchall() == [("run_keep",)], "R13: rollback must not drop data"
            assert conn.execute("select to_regproc('public.heartbeat_job')").fetchone()[0] is None
    finally:
        assert apply_migrations(url) == ["20261031180000", "20261031200300", "20261102105000"]
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("drop table if exists public._deprecated_job_events_20261031180000 cascade")
    with psycopg.connect(url) as conn:
        assert conn.execute("select to_regproc('public.reap_expired_jobs')").fetchone()[0] is not None
        assert conn.execute("select count(*) from public.job_events").fetchone()[0] == 0


def test_run_provenance_migration_is_reversible_without_data_loss() -> None:
    url = _url()
    tenant = AuthStore().ensure_tenant("acme")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(
            "insert into public.runs (id, tenant_id, config) values ('run_prov', %s, '{}')", (tenant,),
        )
        conn.execute(
            "insert into public.run_provenance (run_id, tenant_id, classical_reference_hash)"
            " values ('run_prov', %s, 'abc')", (tenant,),
        )
    rollback("20261031190000", url)
    try:
        with psycopg.connect(url) as conn:
            assert conn.execute("select to_regclass('public.run_provenance')").fetchone()[0] is None
            assert conn.execute(
                "select classical_reference_hash from public._deprecated_run_provenance_20261031190000"
            ).fetchall() == [("abc",)], "R13: rollback must not drop data"
    finally:
        assert apply_migrations(url) == ["20261031190000"]
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("drop table if exists public._deprecated_run_provenance_20261031190000 cascade")
            conn.execute("delete from public.runs where id = 'run_prov'")


def test_no_sqlite_in_package_deployed_code() -> None:
    """P3-01 done-when: no package store uses SQLite either."""
    offenders = []
    for py in PACKAGES.glob("*/src/**/*.py"):
        text = py.read_text(encoding="utf-8")
        if re.search(r"^\s*import sqlite3|^\s*from sqlite3|sqlite:///|sqlite3\.", text, re.MULTILINE):
            offenders.append(str(py.relative_to(PACKAGES)))
    assert offenders == [], offenders


def test_missing_database_url_is_503_blocked_on_james(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from ucgle_f1.db import reset_engine
    from ucgle_f1.m8_agent.auth import reset_auth_store
    from ucgle_f1.m8_agent.server import build_app

    monkeypatch.delenv("DATABASE_URL")
    reset_engine()
    reset_auth_store()
    client = TestClient(build_app(), raise_server_exceptions=False)
    resp = client.get(
        "/api/qcompass/domains",
        headers={"Authorization": "Bearer qcompass-tok_x", "X-QCompass-Tenant": "acme"},
    )
    assert resp.status_code == 503
    assert resp.json()["detail"]["message"] == "BLOCKED-ON-JAMES:DATABASE_URL"
    ready = client.get("/readyz")
    assert ready.status_code == 503
    assert "BLOCKED-ON-JAMES:DATABASE_URL" in ready.json()["checks"]["database"]["detail"]
