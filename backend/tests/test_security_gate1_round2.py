"""Gate 1 security review, round 2 (database, authorisation, tokens, run ids).

One regression test per finding (LEDGER decision 14). Each test drives HTTP
or SQL with APIs that existed before the fix, so on 9c6bf4c it fails on the
bug itself; with the fix it passes. IDs match
``docs/build/lanes/W1-sec-db.md`` and
``docs/build/evidence/W1-security-round2-db.md``.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from ucgle_f1.db.migrate import apply_migrations, rollback
from ucgle_f1.jobs import JobQueue
from ucgle_f1.m8_agent.auth import AuthError, get_auth_store
from ucgle_f1.m8_agent.server import build_app

RUN_FIXTURE = Path(__file__).resolve().parent / "data" / "gate1_run_result.json"
_COSMOLOGY_PROBLEM = {
    "potential": {"kind": "starobinsky", "params": {"M": 1.0e-5}},
    "couplings": {"xi": 1.0e-3, "theta_grav": 1.0e-3, "f_a": 1.0e17,
                  "M_star": 1.0e18, "M1": 1.0e12, "S_E2": 1.0},
    "reheating": {"Gamma_phi": 1.0e-6, "T_reh_GeV": 1.0e13},
    "precision": "fast",
}
_AGENT_TABLES = ("agent_hypotheses", "agent_plans", "agent_approval_tokens",
                 "agent_run_links", "agent_tool_calls", "agent_patches")


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("BLOCKED-ON-JAMES:DATABASE_URL (no test Postgres)")
    return url.replace("postgresql+psycopg://", "postgresql://")


def _sql(sql: str, *params: Any) -> list[tuple[Any, ...]]:
    """Run ``sql`` as the database owner (the API's role)."""
    with psycopg.connect(_url(), autocommit=True) as conn:
        cur = conn.execute(sql, params)
        return cur.fetchall() if cur.description else []


def _user(email: str) -> str:
    return str(_sql("insert into auth.users (email) values (%s) returning id", email)[0][0])


def _personal_tenant(user_id: str) -> str:
    return str(_sql(
        "select tenant_id from public.tenant_members where user_id = %s and role = 'owner'", user_id,
    )[0][0])


@contextmanager
def _as(user_id: str, *, verified: bool = True) -> Iterator[psycopg.Connection]:
    """A connection acting as a Supabase ``authenticated`` user (PostgREST's convention).

    Commits when the block ends normally; rolls back on an exception.
    """
    with psycopg.connect(_url()) as conn:
        conn.execute("set local role authenticated")
        claims: dict[str, Any] = {"sub": user_id, "role": "authenticated"}
        if verified:
            claims["email_verified"] = True
        conn.execute("select set_config('request.jwt.claims', %s, true)", (json.dumps(claims),))
        yield conn


def _rowcount_as(user_id: str, sql: str, *params: Any) -> int:
    with _as(user_id) as conn:
        return conn.execute(sql, params).rowcount


@contextmanager
def _tenant_checks_suspended() -> Iterator[None]:
    """Drop every CHECK constraint on public.tenants, then restore each with its
    own definition (pg_get_constraintdef keeps NOT VALID). Builds rows that
    predate the slug guards without naming any migration."""
    saved = _sql(
        "select conname, pg_get_constraintdef(oid) from pg_constraint "
        "where conrelid = 'public.tenants'::regclass and contype = 'c'"
    )
    for name, _ in saved:
        _sql(f'alter table public.tenants drop constraint "{name}"')
    try:
        yield
    finally:
        for name, definition in saved:  # a migration run inside may have re-added it
            _sql(f'alter table public.tenants drop constraint if exists "{name}"')
            _sql(f'alter table public.tenants add constraint "{name}" {definition}')


def _migrations_from(version: str) -> list[str]:
    return [r[0] for r in _sql(
        "select version from supabase_migrations.schema_migrations where version >= %s order by version",
        version,
    )]


@contextmanager
def _rolled_back_from(version: str) -> Iterator[None]:
    """Roll back every applied migration from ``version`` on (newest first); the
    block then sets up the old state; on exit all of them are re-applied."""
    versions = _migrations_from(version)
    for v in reversed(versions):
        rollback(v, _url())
    try:
        yield
    finally:
        assert apply_migrations(_url()) == versions


@pytest.fixture
def tenants(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Two enterprise tenants (acme, globex) with run-scope API keys, production mode."""
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    monkeypatch.delenv("QCOMPASS_ENV", raising=False)
    monkeypatch.delenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", raising=False)
    store = get_auth_store()
    out: dict[str, Any] = {"client": TestClient(build_app()), "artifacts": tmp_path / "artifacts"}
    for slug in ("acme", "globex"):
        tok = store.issue(slug, scopes=["read", "run"])
        out[slug] = {
            "uuid": store.ensure_tenant(slug),
            "headers": {"Authorization": f"Bearer {tok.token_id}", "X-QCompass-Tenant": slug},
        }
    _sql("update public.tenants set subscription_tier = 'enterprise' where slug in ('acme', 'globex')")
    return out


def _submit(client: TestClient, headers: dict[str, str], **extra: Any) -> Any:
    return client.post("/api/qcompass/domains/cosmology/runs",
                       json={"manifest": _COSMOLOGY_PROBLEM, **extra}, headers=headers)


# ── c1/c2 MEDIUM: the 'dev' slug and created_by ────────────────────────


def test_r2_owner_cannot_take_the_dev_slug_or_clear_created_by() -> None:
    """R2-DEV-SLUG: an owner renamed their tenant to 'dev' by nulling created_by in the same UPDATE."""
    mallory = _user("mallory-dev@example.test")
    mine = _personal_tenant(mallory)
    with pytest.raises(psycopg.errors.CheckViolation):
        _rowcount_as(mallory, "update public.tenants set slug = 'dev', created_by = null where id = %s", mine)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _rowcount_as(mallory, "update public.tenants set created_by = null where id = %s", mine)
    for variant in ("DEV", " dev "):
        with pytest.raises(psycopg.errors.CheckViolation):
            _rowcount_as(mallory, "update public.tenants set slug = %s where id = %s", variant, mine)
    assert _sql("select slug <> 'dev', created_by::text from public.tenants where id = %s", mine) == [
        (True, mallory),
    ]
    # Renaming to anything else still works (main's "owners update tenants").
    assert _rowcount_as(mallory, "update public.tenants set slug = 'mallory-co' where id = %s", mine) == 1


@pytest.mark.parametrize("owned_by", ["creator", "member"])
def test_r2_dev_api_never_uses_a_user_owned_dev_tenant(owned_by: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """R2-DEV-SLUG: AuthStore.ensure_tenant('dev') returned a squatter's tenant (QCOMPASS_ENV=dev)."""
    monkeypatch.setenv("QCOMPASS_ENV", "dev")
    mallory = _user("mallory-dev-api@example.test")
    with _tenant_checks_suspended():  # a row from before the guard (main allowed it)
        squatted = str(_sql(
            "insert into public.tenants (name, slug, created_by) values ('m', 'dev', %s) returning id",
            mallory if owned_by == "creator" else None,
        )[0][0])
        _sql("insert into public.tenant_members (tenant_id, user_id, role) values (%s, %s, 'owner')",
             squatted, mallory)
        try:
            store = get_auth_store()
            assert store.resolve_tenant("dev") is None
            with pytest.raises(AuthError) as refused:
                store.ensure_tenant("dev")
            assert "BLOCKED-ON-JAMES" in str(refused.value)
            assert store.resolve_tenant(squatted) == (squatted, "dev"), "the owner keeps their tenant by id"
        finally:
            _sql("delete from public.tenants where id = %s", squatted)


# ── c1 NIT: slugs that Postgres casts to uuid ─────────────────────────


@pytest.mark.parametrize("slug", [
    "a0ee-bc99-9c0b-4ef8-bb6d-6bb9-bd38-0a11", "{a0eebc99-9c0b4ef8-bb6d6bb9-bd380a11}",
    "A0EEBC999C0B4EF8BB6D6BB9BD380A11",
])
def test_r2_slugs_that_cast_to_uuid_are_refused(slug: str) -> None:
    """R2-UUID-SLUG: the slug guard's regex missed forms Postgres casts to uuid."""
    assert _sql("select %s::uuid::text", slug) == [("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",)]
    with pytest.raises(psycopg.errors.CheckViolation):
        _sql("insert into public.tenants (name, slug) values ('odd', %s)", slug)
    mallory = _user("mallory-uuid@example.test")
    with pytest.raises(psycopg.errors.CheckViolation):
        _rowcount_as(mallory, "update public.tenants set slug = %s where id = %s", slug, _personal_tenant(mallory))


# ── c2 HIGH: subscription_tier ────────────────────────────────────────


def test_r2_owner_cannot_raise_their_own_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R2-TIER: an owner set subscription_tier='enterprise' and escaped every plan limit."""
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    monkeypatch.delenv("QCOMPASS_ENV", raising=False)
    alice = _user("alice-tier@example.test")
    personal = _personal_tenant(alice)
    slug = _sql("select slug from public.tenants where id = %s", personal)[0][0]
    # Named by UUID: a key is never bound to a user's tenant by its slug (round 3B).
    tok = get_auth_store().issue(personal, scopes=["read", "run"])
    headers = {"Authorization": f"Bearer {tok.token_id}", "X-QCompass-Tenant": slug}
    client = TestClient(build_app())
    assert _submit(client, headers).status_code == 202
    assert _submit(client, headers).status_code == 429  # free: one concurrent job
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _rowcount_as(alice, "update public.tenants set subscription_tier = 'enterprise' where id = %s", personal)
    assert _sql("select subscription_tier::text from public.tenants where id = %s", personal) == [("free",)]
    blocked = _submit(client, headers)
    assert blocked.status_code == 429 and blocked.json()["detail"]["code"] == "PLAN_CONCURRENT_JOBS_EXCEEDED"
    # A tenant a user creates starts on the free plan whatever the insert says.
    with _as(alice) as conn:
        conn.execute("insert into public.tenants (name, slug, created_by, subscription_tier) "
                     "values ('a', 'alice-co', %s, 'enterprise')", (alice,))
    assert _sql("select subscription_tier::text from public.tenants where slug = 'alice-co'") == [("free",)]
    # The service (billing) still sets plans.
    _sql("update public.tenants set subscription_tier = 'pro' where id = %s", personal)
    assert _submit(client, headers).status_code == 202


# ── c1/c2/c4: the SF4 backfill and user-owned 'dev' tenants ───────────


@pytest.mark.parametrize("owned_by", ["creator", "member"])
def test_r2_sf4_backfill_never_hands_agent_rows_to_a_user_owned_dev_tenant(owned_by: str) -> None:
    """R2-SF4-BACKFILL: 20261031200400 gave every legacy agent row to a user-owned 'dev' tenant.

    The database is taken back to just before 20261031200400 (every later
    migration rolled back too), legacy tenant-less rows are written, a user
    owns 'dev', and the migrations are applied again.
    """
    mallory = _user("mallory-sf4@example.test")
    with _tenant_checks_suspended():  # a 'dev' row from before the guard (main allowed it)
        with _rolled_back_from("20261031200400"):
            _sql('insert into public.agent_patches ("patchId", "conversationId", "targetPath", rationale, '
                 "\"unifiedDiff\") values ('patch_legacy', 'c_victim', 'victim/secret.py', 'r', '+VICTIM_SECRET')")
            _sql('insert into public.agent_tool_calls ("conversationId", tool, "requestJson", "responseJson", ok) '
                 "values ('c_victim', 'get_run', '{\"secret\": 1}', '{}', true)")
            _sql('insert into public.agent_hypotheses ("hypothesisId", "conversationId", text) '
                 "values ('hyp_legacy', 'c_victim', 'victim hypothesis')")
            dev = str(_sql(
                "insert into public.tenants (name, slug, created_by) values ('m', 'dev', %s) returning id",
                mallory if owned_by == "creator" else None,
            )[0][0])
            _sql("insert into public.tenant_members (tenant_id, user_id, role) values (%s, %s, 'owner')",
                 dev, mallory)
        try:
            with _as(mallory) as conn:
                seen = {t: conn.execute(f"select count(*) from public.{t}").fetchone()[0]
                        for t in ("agent_patches", "agent_tool_calls", "agent_hypotheses")}
            assert seen == {"agent_patches": 0, "agent_tool_calls": 0, "agent_hypotheses": 0}, seen
            for t in _AGENT_TABLES:
                assert _sql(f"select count(*) from public.{t} where tenant_id is not null") == [(0,)], t
            assert _sql("select count(*) from public.agent_patches") == [(1,)], "nothing is deleted"
        finally:
            _sql("delete from public.tenants where id = %s", dev)


# ── c1 LOW: /v1/chat tool calls and the event loop ────────────────────


def _waiting_on_a_lock(count: int, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        n = _sql("select count(*) from pg_stat_activity where wait_event_type = 'Lock'")[0][0]
        if n >= count:
            return True
        time.sleep(0.05)
    return False


def test_r2_chat_tool_calls_do_not_block_the_event_loop(
    tenants: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R2-CHAT-LOOP: /v1/chat ran cancel_run on the event loop's thread, stalling every request."""
    from ucgle_f1.m8_agent import server
    from ucgle_f1.m8_agent.models.base import ChatEvent

    JobQueue().enqueue_run(
        run_id="run_chat_slow", tenant_uuid=tenants["acme"]["uuid"], kind="ucgle_f1.run", payload={},
        label="slow", config={"kind": "ucgle_f1.run", "domain": "cosmology"}, enforce_limits=False,
    )
    acme = tenants["acme"]["headers"]

    class _Stub:
        def __init__(self, cfg: Any) -> None:
            self.config = cfg

        async def stream(self, messages: Any, tools: Any) -> Any:
            yield ChatEvent(type="tool_call", tool_call={
                "id": "call_1", "name": "cancel_run",
                "arguments": {"run_id": "run_chat_slow", "approval_token": token},
            })
            yield ChatEvent(type="finish")

    monkeypatch.setattr(server, "get_provider", _Stub)
    out: dict[str, Any] = {}
    with TestClient(build_app()) as client:  # one event loop serves every request
        token = client.post("/api/approvals", json={"scopes": ["cancel_run"]}, headers=acme).json()["tokenId"]
        with psycopg.connect(_url()) as holder:
            # A slow database: the run row is locked, so cancel_run waits.
            holder.execute("select 1 from public.runs where id = 'run_chat_slow' for update")

            def chat() -> None:
                body = {"conversationId": "c_loop", "messages": [], "modelId": "stub"}
                with client.stream("POST", "/v1/chat", json=body, headers=acme) as resp:
                    out["chat"] = "".join(resp.iter_text())

            def health() -> None:
                out["health"] = client.get("/healthz").status_code

            t_chat = threading.Thread(target=chat, daemon=True)
            t_chat.start()
            try:
                assert _waiting_on_a_lock(1), "cancel_run never reached the locked run"
                t_health = threading.Thread(target=health, daemon=True)
                t_health.start()
                t_health.join(5)
                answered = not t_health.is_alive()
            finally:
                holder.rollback()  # release the lock either way
        t_chat.join(30)
        if not answered:
            t_health.join(30)
    assert answered and out.get("health") == 200, "the event loop was blocked by the tool call"
    assert '"ok":true' in out["chat"].replace(" ", "")


# ── c2 MEDIUM: M1 residual (USING clauses, audits, timelines) ─────────


def test_r2_writes_hung_off_a_run_need_a_writer_of_its_tenant(tenants: dict[str, Any]) -> None:
    """R2-M1-USING: authors kept updating/deleting runs, results, audits and timelines in tenants
    they did not write for (USING clauses and main's audit/timeline policies had no tenant test)."""
    acme, globex = tenants["acme"]["uuid"], tenants["globex"]["uuid"]
    alice = _user("alice-m1@example.test")  # no membership in globex
    carol = _user("carol-m1@example.test")
    get_auth_store().add_member("globex", carol, "viewer")
    get_auth_store().add_member("acme", alice, "member")
    # Rows written before the fix (or kept after a membership ended).
    for run_id, author in (("run_alice_globex", alice), ("run_carol_globex", carol)):
        _sql("insert into public.runs (id, author_user_id, tenant_id, config) values (%s, %s, %s, '{}')",
             run_id, author, globex)
        _sql("insert into public.run_results (run_id, payload) values (%s, '{\"v\": 1}')", run_id)
    for run_id, author in (("run_alice_globex", alice), ("run_carol_globex", carol)):
        # Moving the run out of the tenant, rewriting it, or deleting what hangs off it.
        assert _rowcount_as(author, "update public.runs set tenant_id = null where id = %s", run_id) == 0
        assert _rowcount_as(author, "delete from public.run_results where run_id = %s", run_id) == 0
        if author == carol:  # a viewer passes main's WITH CHECK (membership only)
            assert _rowcount_as(author, "update public.runs set status = 'completed' where id = %s", run_id) == 0
            assert _rowcount_as(author, "update public.run_results set payload = '{\"v\": 2}' "
                                "where run_id = %s", run_id) == 0
        for table, cols, vals in (
            ("audit_reports", "run_id, verdicts", "%s, '{}'"),
            ("viz_timelines", "run_id, storage_path", "%s, 'x'"),
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                _rowcount_as(author, f"insert into public.{table} ({cols}) values ({vals})", run_id)
        assert _rowcount_as(author, "delete from public.runs where id = %s", run_id) == 0
    assert _sql("select count(*) from public.runs where status = 'queued' and tenant_id = %s", globex) == [(2,)]
    assert _sql("select payload from public.run_results where run_id = 'run_alice_globex'") == [({"v": 1},)]
    # Writers keep their writes: alice in acme, and anyone on a personal run.
    for run_id, tenant in (("run_alice_acme", acme), ("run_alice_personal", None)):
        with _as(alice) as conn:
            conn.execute("insert into public.runs (id, author_user_id, tenant_id, config) values (%s, %s, %s, '{}')",
                         (run_id, alice, tenant))
            conn.execute("insert into public.run_results (run_id, payload) values (%s, '{}')", (run_id,))
            conn.execute("insert into public.audit_reports (run_id, verdicts) values (%s, '{}')", (run_id,))
            conn.execute("insert into public.viz_timelines (run_id, storage_path) values (%s, 'x')", (run_id,))
            # The client's own flow (simulator.ts setRunStatus): queued → running → completed.
            assert conn.execute("update public.runs set status = 'running' where id = %s", (run_id,)).rowcount == 1
            assert conn.execute("update public.runs set status = 'completed' where id = %s", (run_id,)).rowcount == 1
    assert _rowcount_as(alice, "delete from public.runs where id = 'run_alice_personal'") == 1


# ── c2 MEDIUM: a viewer plants runs the API serves ────────────────────


def test_r2_api_never_serves_client_written_tenant_runs(tenants: dict[str, Any]) -> None:
    """R2-VIEWER-PLANT: a viewer inserted a 'completed' tenant run and result; the API served it."""
    client, globex = tenants["client"], tenants["globex"]
    carol, dave = _user("carol-plant@example.test"), _user("dave-plant@example.test")
    get_auth_store().add_member("globex", carol, "viewer")
    get_auth_store().add_member("globex", dave, "member")
    cfg = json.dumps({"domain": "chemistry", "kind": "qcompass.run"})
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with _as(carol) as conn:
            conn.execute("insert into public.runs (id, author_user_id, tenant_id, status, config) "
                         "values ('qc_forged', %s, %s, 'completed', %s)", (carol, globex["uuid"], cfg))
    # A writer's client row is the member's own data, never a platform run.
    with _as(dave) as conn:
        conn.execute("insert into public.runs (id, author_user_id, tenant_id, status, config) "
                     "values ('qc_client', %s, %s, 'completed', %s)", (dave, globex["uuid"], cfg))
        conn.execute("insert into public.run_results (run_id, payload) values ('qc_client', '{\"forged\": true}')")
    headers = globex["headers"]
    assert client.get("/api/qcompass/domains/chemistry/runs/qc_client", headers=headers).status_code == 404
    assert client.get("/api/qcompass/domains/chemistry/runs", headers=headers).json() == []
    assert JobQueue().result("qc_client", tenant_uuid=globex["uuid"]) is None


# ── c2 MEDIUM: the monthly quota counted client rows ──────────────────


def test_r2_client_rows_do_not_count_against_the_monthly_quota(tenants: dict[str, Any]) -> None:
    """R2-QUOTA: 25 client-inserted runs dated 2099 locked a free tenant out until 2099."""
    client, globex = tenants["client"], tenants["globex"]
    _sql("update public.tenants set subscription_tier = 'free' where id = %s", globex["uuid"])
    dave = _user("dave-quota@example.test")
    get_auth_store().add_member("globex", dave, "member")
    with _as(dave) as conn:
        conn.execute(
            "insert into public.runs (id, author_user_id, tenant_id, config, created_at) "
            "select 'junk_' || g, %s, %s, '{}', '2099-12-31' from generate_series(1, 25) g",
            (dave, globex["uuid"]),
        )
    resp = _submit(client, globex["headers"])
    assert resp.status_code == 202, resp.text


# ── c2 LOW: storage grants in the test shim, and storage RLS ──────────


def test_r2_storage_grants_match_supabase() -> None:
    """R2-STORAGE-SHIM: the shim granted nothing on storage.objects, so every storage RLS test was vacuous."""
    for priv in ("select", "insert", "update", "delete"):
        for role in ("anon", "authenticated"):
            assert _sql("select has_table_privilege(%s, 'storage.objects', %s)", role, priv) == [(True,)]
    # The wave's read policy, observed: a member reads its tenant's artefact.
    acme = get_auth_store().ensure_tenant("acme")
    bob = _user("bob-storage@example.test")
    get_auth_store().add_member("acme", bob, "viewer")
    JobQueue().enqueue_run(run_id="run_art", tenant_uuid=acme, kind="qcompass.run", payload={}, label="a",
                           config={"domain": "chemistry", "kind": "qcompass.run"}, enforce_limits=False)
    _sql("insert into storage.objects (bucket_id, name) values ('run-artifacts', 'run_art/provenance.json')")
    with _as(bob) as conn:
        assert conn.execute("select name from storage.objects").fetchall() == [("run_art/provenance.json",)]


def test_r2_storage_writes_need_a_writer_of_the_runs_tenant(tenants: dict[str, Any]) -> None:
    """R2-M1-STORAGE: authors wrote, updated and deleted objects of runs in tenants they don't write for."""
    # Supabase's grants, so the policies (not missing privileges) decide.
    _sql("grant select, insert, update, delete on storage.objects to anon, authenticated")
    globex = tenants["globex"]["uuid"]
    alice, carol = _user("alice-st@example.test"), _user("carol-st@example.test")
    get_auth_store().add_member("globex", carol, "viewer")
    for run_id, author in (("run_planted", alice), ("run_viewer", carol)):
        _sql("insert into public.runs (id, author_user_id, tenant_id, config) values (%s, %s, %s, '{}')",
             run_id, author, globex)
        for bucket in ("run-artifacts", "viz-timelines"):
            _sql("insert into storage.objects (bucket_id, name) values (%s, %s)", bucket, f"{run_id}/kept.json")
    for run_id, author in (("run_planted", alice), ("run_viewer", carol)):
        for bucket in ("run-artifacts", "viz-timelines"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                _rowcount_as(author, "insert into storage.objects (bucket_id, name) values (%s, %s)",
                             bucket, f"{run_id}/forged.json")
            assert _rowcount_as(author, "delete from storage.objects where bucket_id = %s and name = %s",
                                bucket, f"{run_id}/kept.json") == 0
        assert _rowcount_as(author, "update storage.objects set metadata = '{}' where bucket_id = "
                            "'viz-timelines' and name = %s", f"{run_id}/kept.json") == 0
    assert _sql("select count(*) from storage.objects where name like '%%/kept.json'") == [(4,)]
    assert _sql("select count(*) from storage.objects where name like '%%/forged.json'") == [(0,)]
    # main's client path: an author uploads, replaces and deletes a personal run's timeline.
    with _as(alice) as conn:
        conn.execute("insert into public.runs (id, author_user_id, config) values ('run_mine', %s, '{}')", (alice,))
        conn.execute("insert into storage.objects (bucket_id, name) values ('viz-timelines', 'run_mine/timeline.json')")
        assert conn.execute("update storage.objects set metadata = '{}' where name = 'run_mine/timeline.json'"
                            ).rowcount == 1
        assert conn.execute("delete from storage.objects where name = 'run_mine/timeline.json'").rowcount == 1


# ── c2: report rows forged before the fixes ───────────────────────────


def test_r2_forged_row_report_lists_and_keeps_forged_rows(tenants: dict[str, Any]) -> None:
    """R2-FORGED-REPORT: nothing listed jobs, runs or objects forged before the fixes."""
    acme, globex = tenants["acme"]["uuid"], tenants["globex"]["uuid"]
    alice = _user("alice-report@example.test")
    JobQueue().enqueue_run(run_id="run_victim", tenant_uuid=globex, kind="qcompass.run", payload={}, label="v",
                           config={"domain": "chemistry", "kind": "qcompass.run"}, enforce_limits=False)
    forged = str(_sql("insert into public.jobs (tenant_id, run_id, kind) values (%s, 'run_victim', "
                      "'qcompass.run') returning id", acme)[0][0])
    _sql("insert into public.runs (id, author_user_id, tenant_id, config) values ('run_planted', %s, %s, '{}')",
         alice, globex)
    _sql("insert into storage.objects (bucket_id, name) values ('run-artifacts', 'run_planted/x.json')")
    report = {(kind, ref) for kind, ref, _t, _d in _sql("select * from public.qcompass_forged_row_report()")}
    assert report == {
        ("job_tenant_differs_from_run", forged),
        ("run_author_not_a_writer", "run_planted"),
        ("storage_object_of_such_run", "run-artifacts/run_planted/x.json"),
        # The fixture's enterprise tiers: every paid tier is listed (20261102120100).
        ("tenant_tier_not_free", acme),
        ("tenant_tier_not_free", globex),
    }
    assert _sql("select count(*) from public.jobs where id = %s", forged) == [(1,)], "reported, not deleted"
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with _as(alice) as conn:
            conn.execute("select * from public.qcompass_forged_row_report()")


# ── c4: approval tokens ───────────────────────────────────────────────


def test_r2_tool_call_log_never_stores_approval_tokens(
    tenants: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R2-TOKEN-LOG: /v1/chat stored approval_token in agent_tool_calls.requestJson, which viewers read."""
    from ucgle_f1.m8_agent import server
    from ucgle_f1.m8_agent.models.base import ChatEvent

    client, acme = tenants["client"], tenants["acme"]["headers"]
    token = client.post("/api/approvals", json={"scopes": ["cancel_run"]}, headers=acme).json()["tokenId"]

    class _Stub:
        def __init__(self, cfg: Any) -> None:
            self.config = cfg

        async def stream(self, messages: Any, tools: Any) -> Any:
            yield ChatEvent(type="tool_call", tool_call={
                "id": "c1", "name": "cancel_run",
                "arguments": {"run_id": "nope", "approval_token": token, "other_token": "s3cret"},
            })
            yield ChatEvent(type="finish")

    monkeypatch.setattr(server, "get_provider", _Stub)
    with client.stream("POST", "/v1/chat", json={"conversationId": "c_tok", "messages": [], "modelId": "s"},
                       headers=acme) as resp:
        "".join(resp.iter_text())
    viewer = _user("viewer-tok@example.test")
    get_auth_store().add_member("acme", viewer, "viewer")
    with _as(viewer) as conn:
        logged = [r[0] for r in conn.execute('select "requestJson" from public.agent_tool_calls').fetchall()]
    assert len(logged) == 1
    assert token not in logged[0] and "s3cret" not in logged[0]
    assert json.loads(logged[0]) == {"run_id": "nope", "approval_token": "[redacted]", "other_token": "[redacted]"}


def test_r2_an_approval_token_is_spent_once_across_instances(tenants: dict[str, Any]) -> None:
    """R2-TOKEN-RACE: two API instances read the token before either marked it consumed; both accepted it."""
    from ucgle_f1.m8_agent.memory.store import ConversationStore

    tok = ConversationStore().issue_approval(["start_run"], 600, tenant="acme").tokenId
    results: list[bool] = []
    instances = [ConversationStore() for _ in range(2)]
    for inst in instances:
        inst._lock = threading.RLock()  # separate processes share no lock

    with psycopg.connect(_url()) as holder:
        # A slow database: the token row is locked while both requests arrive.
        holder.execute('select 1 from public.agent_approval_tokens where "tokenId" = %s for update', (tok,))
        threads = [threading.Thread(target=lambda i=i: results.append(i.consume_approval(tok, "start_run",
                                                                                         tenant="acme")))
                   for i in instances]
        for t in threads:
            t.start()
        try:
            assert _waiting_on_a_lock(2), "both requests reach the token"
        finally:
            holder.rollback()
        for t in threads:
            t.join(30)
    assert sorted(results) == [False, True], f"one-shot token accepted {results.count(True)} times"


def test_r2_approval_tokens_are_one_shot_scoped_and_short_lived(tenants: dict[str, Any]) -> None:
    """R2-TOKEN-TTL: '*' tokens were never spent, any TTL was accepted, a huge one was a 500."""
    from ucgle_f1.m8_agent.memory import get_store

    client, acme = tenants["client"], tenants["acme"]["headers"]
    for body in ({"scopes": ["start_run"], "ttl_seconds": 10 ** 9}, {"scopes": ["start_run"], "ttl_seconds": 1e13},
                 {"scopes": ["start_run"], "ttl_seconds": 3601}, {"scopes": ["start_run"], "ttl_seconds": 0},
                 {"scopes": ["start_run"], "ttl_seconds": -5}, {"scopes": ["start_run"], "ttl_seconds": None},
                 {"scopes": ["*"]}, {"scopes": []}, {"scopes": ["start_run", "everything"]}):
        resp = client.post("/api/approvals", json=body, headers=acme)
        assert resp.status_code == 422, (body, resp.status_code, resp.text)
    ok = client.post("/api/approvals", json={"scopes": ["start_run"], "ttl_seconds": 3600}, headers=acme)
    assert ok.status_code == 200
    store = get_store()
    tok = ok.json()["tokenId"]
    assert store.consume_approval(tok, "cancel_run", tenant="acme") is False
    assert store.consume_approval(tok, "start_run", tenant="acme") is True
    assert store.consume_approval(tok, "start_run", tenant="acme") is False
    # A wildcard or never-expiring token already in the table approves nothing.
    _sql('insert into public.agent_approval_tokens ("tokenId", tenant_id, scopes, "expiresAt") values '
         "('appr_star', %s, '*', now() + interval '1 hour'), ('appr_forever', %s, 'start_run', null)",
         tenants["acme"]["uuid"], tenants["acme"]["uuid"])
    assert [store.consume_approval("appr_star", sc, tenant="acme") for sc in ("start_run", "cancel_run")] == [
        False, False,
    ]
    assert store.consume_approval("appr_forever", "start_run", tenant="acme") is False


def test_r2_start_run_validates_before_spending_and_needs_the_tenants_hypothesis(
    tenants: dict[str, Any],
) -> None:
    """R2-START-ORDER: start_run spent the token before validating, and linked any hypothesisId."""
    from ucgle_f1.m8_agent.memory import get_store

    client, acme = tenants["client"], tenants["acme"]["headers"]
    token = client.post("/api/approvals", json={"scopes": ["start_run"]}, headers=acme).json()["tokenId"]
    cfg = json.loads(RUN_FIXTURE.read_text())["config"]
    foreign = get_store().record_hypothesis("c_g", "globex's hypothesis", tenant="globex").hypothesisId
    for hypothesis in (foreign, "hyp_never_recorded", None):
        if hypothesis is None:
            cfg.pop("agent", None)
        else:
            cfg["agent"] = {"conversationId": "c_a", "hypothesisId": hypothesis}
        resp = client.post("/api/runs", json={"config": cfg, "approval_token": token}, headers=acme)
        assert resp.status_code == 409 and resp.json()["detail"]["code"] == "AUDIT_VIOLATION", hypothesis
    assert _sql("select count(*) from public.runs") == [(0,)]
    own = get_store().record_hypothesis("c_a", "acme's hypothesis", tenant="acme").hypothesisId
    cfg["agent"] = {"conversationId": "c_a", "hypothesisId": own}
    resp = client.post("/api/runs", json={"config": cfg, "approval_token": token}, headers=acme)
    assert resp.status_code == 200, "the refused requests did not spend the token"
    assert get_store().run_link(resp.json()["runId"], tenant="acme").hypothesisId == own  # type: ignore[union-attr]


# ── c4 LOW: run ids are one global, client-chosen namespace ───────────


def test_r2_run_ids_are_per_tenant_aliases(tenants: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """R2-RUN-ID: a tenant, or any user through PostgREST, took a runId another tenant would submit."""
    monkeypatch.setenv("QCOMPASS_STREAM_IDLE_SECONDS", "0.5")  # no worker here: the stream ends idle
    client = tenants["client"]
    acme, globex = tenants["acme"]["headers"], tenants["globex"]["headers"]
    assert _submit(client, acme, runId="kawai-kim-natural").status_code == 202
    taken = _submit(client, globex, runId="kawai-kim-natural")
    assert taken.status_code == 202, "another tenant's runId does not block this one"
    # Any signed-up user can insert a personal run with any id through PostgREST.
    eve = _user("eve-runid@example.test")
    with _as(eve) as conn:
        conn.execute("insert into public.runs (id, author_user_id, config) values ('acme-next-run', %s, '{}')",
                     (eve,))
    squatted = _submit(client, acme, runId="acme-next-run")
    assert squatted.status_code == 202, "a PostgREST row does not block the API"
    run_id = squatted.json()["runId"]
    assert run_id != "acme-next-run" and squatted.json()["clientRunId"] == "acme-next-run"
    # The alias and the id name the same run, for its tenant only.
    for name in (run_id, "acme-next-run"):
        got = client.get(f"/api/qcompass/domains/cosmology/runs/{name}", headers=acme)
        assert got.status_code == 200 and got.json()["id"] == run_id
        assert client.get(f"/api/qcompass/domains/cosmology/runs/{name}", headers=globex).status_code == 404
    with client.stream("GET", "/api/qcompass/domains/cosmology/runs/acme-next-run/stream", headers=acme) as resp:
        assert resp.status_code == 200
        text = "".join(resp.iter_text())
    assert f'"runId": "{run_id}"' in text and "event: status" in text, text[:300]
    # Reusing an alias inside one's own tenant is the only conflict.
    again = _submit(client, acme, runId="acme-next-run")
    assert again.status_code == 409 and again.json()["detail"]["code"] == "CONFLICT"


# ── c4 NIT: agent_plans.path ──────────────────────────────────────────


def test_r2_plans_stay_in_the_tenant_sandbox_and_store_a_relative_path(tenants: dict[str, Any]) -> None:
    """R2-PLAN-PATH: save_plan joined an unsanitised conversation id and stored an absolute server path."""
    from ucgle_f1.m8_agent.memory import get_store

    root = Path(os.environ["UCGLE_F1_ARTIFACTS"])
    store = get_store()
    for bad in ("../../escaped", "/abs", "a/b", ".."):
        with pytest.raises(ValueError):
            store.save_plan(bad, {"steps": []}, tenant="acme")
    assert not (root.parent / "escaped").exists() and not (root / "escaped").exists()
    plans = {t: store.save_plan("c_shared", {"t": t}, tenant=t) for t in ("acme", "globex")}
    for tenant, plan in plans.items():
        assert not Path(plan.path).is_absolute() and str(root) not in plan.path
        # Keyed by the tenant's UUID, which a rename can't take over (round 3B).
        assert plan.path == f"agent-sandbox/{tenants[tenant]['uuid']}/c_shared/plans/{plan.planId}.json"
        assert json.loads((root / plan.path).read_text()) == {"t": tenant}


# ── every migration of this lane is reversible ────────────────────────


@pytest.mark.parametrize("version", ["20261102100000", "20261102100100", "20261102100200", "20261102100300"])
def test_r2_migrations_are_reversible(version: str, tenants: dict[str, Any]) -> None:
    """Each round-2 migration has a down migration; re-applying it restores the same schema (R13)."""
    _submit(tenants["client"], tenants["acme"]["headers"], runId="kept-alias")

    def schema() -> list[tuple[Any, ...]]:
        return _sql(
            "select 'policy', tablename || ':' || policyname, coalesce(qual, '') || coalesce(with_check, '') "
            "from pg_policies union all "
            "select 'constraint', conname, pg_get_constraintdef(oid) from pg_constraint "
            "where conrelid = 'public.tenants'::regclass union all "
            "select 'trigger', tgname, '' from pg_trigger where tgrelid = 'public.tenants'::regclass "
            "and not tgisinternal union all "
            "select 'column', table_name || '.' || column_name, '' from information_schema.columns "
            "where table_schema = 'public' and table_name = 'runs' union all "
            "select 'function', proname, '' from pg_proc where proname like 'qcompass\\_%%' order by 1, 2"
        )

    before = schema()
    with _rolled_back_from(version):
        assert schema() != before
    assert schema() == before
    alias = _sql("select client_run_id from public.runs where client_run_id is not null")
    assert alias == [("kept-alias",)], "R13: the alias column keeps its data across down and up"
