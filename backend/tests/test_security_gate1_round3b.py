"""Gate 1 security review, round 3B (lane DB3: database and authorisation residuals).

One regression test per finding (LEDGER decision 14). Each test drives HTTP,
SQL or APIs that existed on the lane's base 15e4e3c, so it fails there on the
bug itself; with the fix it passes. IDs match ``docs/build/lanes/W1-db3.md``
and ``docs/build/evidence/W1-db3.md``.
"""

from __future__ import annotations

import json
import os
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

_COSMOLOGY_PROBLEM = {
    "potential": {"kind": "starobinsky", "params": {"M": 1.0e-5}},
    "couplings": {"xi": 1.0e-3, "theta_grav": 1.0e-3, "f_a": 1.0e17,
                  "M_star": 1.0e18, "M1": 1.0e12, "S_E2": 1.0},
    "reheating": {"Gamma_phi": 1.0e-6, "T_reh_GeV": 1.0e13},
    "precision": "fast",
}
_CHEMISTRY_CFG = json.dumps({"domain": "chemistry", "kind": "qcompass.run"})


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
def _as(user_id: str) -> Iterator[psycopg.Connection]:
    """A connection acting as a verified Supabase ``authenticated`` user (PostgREST's convention)."""
    with psycopg.connect(_url()) as conn:
        conn.execute("set local role authenticated")
        claims = {"sub": user_id, "role": "authenticated", "email_verified": True}
        conn.execute("select set_config('request.jwt.claims', %s, true)", (json.dumps(claims),))
        yield conn


@contextmanager
def _tenant_checks_suspended() -> Iterator[None]:
    """Drop every CHECK constraint on public.tenants for the block, then restore each with its
    own definition; builds rows that predate the slug guards without naming any migration."""
    saved = _sql(
        "select conname, pg_get_constraintdef(oid) from pg_constraint "
        "where conrelid = 'public.tenants'::regclass and contype = 'c'"
    )
    for name, _ in saved:
        _sql(f'alter table public.tenants drop constraint "{name}"')
    try:
        yield
    finally:
        for name, definition in saved:
            _sql(f'alter table public.tenants drop constraint if exists "{name}"')
            _sql(f'alter table public.tenants add constraint "{name}" {definition}')


@pytest.fixture
def tenants(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Two tenants (acme, globex) with run-scope API keys, production mode, free plan."""
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
    return out


def _submit(client: TestClient, headers: dict[str, str], **extra: Any) -> Any:
    return client.post("/api/qcompass/domains/cosmology/runs",
                       json={"manifest": _COSMOLOGY_PROBLEM, **extra}, headers=headers)


# ── R3B-API-ORIGIN: "no author" was taken as "the API wrote it" ───────


def test_r3b_client_runs_stay_client_runs_after_the_authors_account_is_deleted(
    tenants: dict[str, Any],
) -> None:
    """A member's PostgREST runs became platform runs once the member's account was deleted
    (runs.author_user_id is ON DELETE SET NULL): served by the API, counted against the quota."""
    client, globex = tenants["client"], tenants["globex"]
    dave = _user("dave-leaver@example.test")
    get_auth_store().add_member("globex", dave, "member")
    with _as(dave) as conn:
        conn.execute("insert into public.runs (id, author_user_id, tenant_id, status, config) "
                     "values ('qc_planted', %s, %s, 'completed', %s)", (dave, globex["uuid"], _CHEMISTRY_CFG))
        conn.execute("insert into public.run_results (run_id, payload) values ('qc_planted', '{\"forged\": true}')")
        conn.execute("insert into public.runs (id, author_user_id, tenant_id, config, created_at) "
                     "select 'junk_' || g, %s, %s, '{}', '2099-12-31' from generate_series(1, 25) g",
                     (dave, globex["uuid"]))
    _sql("delete from auth.users where id = %s", dave)  # offboarding, or a GDPR erasure
    assert _sql("select count(*) from public.runs where author_user_id is null and tenant_id = %s",
                globex["uuid"]) == [(26,)]
    headers = globex["headers"]
    assert client.get("/api/qcompass/domains/chemistry/runs/qc_planted", headers=headers).status_code == 404
    assert client.get("/api/qcompass/domains/chemistry/runs", headers=headers).json() == []
    assert JobQueue().result("qc_planted", tenant_uuid=globex["uuid"]) is None
    _sql("update public.tenants set subscription_tier = 'free' where id = %s", globex["uuid"])
    resp = _submit(client, headers)
    assert resp.status_code == 202, f"the deleted member's rows count against the quota: {resp.text}"


def test_r3b_clients_cannot_mark_a_run_as_the_apis(tenants: dict[str, Any]) -> None:
    """The marker the API trusts is out of every client's reach, on insert and on update."""
    globex = tenants["globex"]["uuid"]
    dave = _user("dave-origin@example.test")
    get_auth_store().add_member("globex", dave, "member")
    with _as(dave) as conn:
        conn.execute("insert into public.runs (id, author_user_id, tenant_id, config, origin, client_run_id) "
                     "values ('qc_mine', %s, %s, %s, 'api', 'q-alias')", (dave, globex, _CHEMISTRY_CFG))
    assert _sql("select origin, client_run_id from public.runs where id = 'qc_mine'") == [("client", None)]
    for column, value in (("origin", "api"), ("client_run_id", "q-alias")):
        with pytest.raises(psycopg.errors.InsufficientPrivilege), _as(dave) as conn:
            conn.execute(f"update public.runs set {column} = %s where id = 'qc_mine'", (value,))
    # The client's own flow (simulator.ts setRunStatus) still works.
    with _as(dave) as conn:
        assert conn.execute("update public.runs set status = 'running' where id = 'qc_mine'").rowcount == 1
    # The API's own runs carry the marker.
    run_id = _submit(tenants["client"], tenants["globex"]["headers"]).json()["runId"]
    assert _sql("select origin from public.runs where id = %s", run_id) == [("api",)]


# ── R3B-ALIAS-INDEX: a member made their own account undeletable ──────


def test_r3b_a_members_account_stays_deletable(tenants: dict[str, Any]) -> None:
    """A client row reusing an API run's alias collided with it in runs_tenant_client_run_id_key
    once account deletion set its author to null, so the deletion failed."""
    client, globex = tenants["client"], tenants["globex"]
    api = _submit(client, globex["headers"], runId="q3")
    assert api.status_code == 202
    eve = _user("eve-alias@example.test")
    get_auth_store().add_member("globex", eve, "member")
    with _as(eve) as conn:
        conn.execute("insert into public.runs (id, author_user_id, tenant_id, config, client_run_id) "
                     "values ('eve_r', %s, %s, '{}', 'q3')", (eve, globex["uuid"]))
    _sql("delete from auth.users where id = %s", eve)  # must not fail
    assert _sql("select count(*) from auth.users where id = %s", eve) == [(0,)]
    got = client.get("/api/qcompass/domains/cosmology/runs/q3", headers=globex["headers"])
    assert got.status_code == 200 and got.json()["id"] == api.json()["runId"]


# ── R3B-SLUG-SQUAT: issue() adopted any tenant with the slug ──────────


def test_r3b_a_key_is_never_bound_to_a_squatted_slug(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A user renamed their own tenant to a customer's slug; the operator's issue(slug) bound the
    customer's key to the squatter's tenant."""
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    monkeypatch.delenv("QCOMPASS_ENV", raising=False)
    mallory = _user("mallory-squat@example.test")
    mine = _personal_tenant(mallory)
    with _as(mallory) as conn:  # main's "owners update tenants"
        assert conn.execute("update public.tenants set slug = 'newcustomer' where id = %s", (mine,)).rowcount == 1
    store = get_auth_store()
    with pytest.raises(AuthError) as refused:
        store.issue("newcustomer", scopes=["read", "run"])
    assert refused.value.code == "TENANT_RESERVED"
    assert _sql("select count(*) from public.api_keys where tenant_id = %s", mine) == [(0,)]
    # A slug nobody holds still gets a new tenant of the service's own.
    fresh = store.issue("othercustomer", scopes=["read"])
    assert fresh.tenant_id == "othercustomer"
    assert _sql("select created_by from public.tenants where slug = 'othercustomer'") == [(None,)]
    # Once the service gave a tenant members, a key for it is issued by UUID only.
    store.add_member("othercustomer", mallory, "member")
    with pytest.raises(AuthError):
        store.issue("othercustomer", scopes=["read"])
    other = store.ensure_tenant("othercustomer")
    assert store.issue(other, scopes=["read"]).tenant_id == "othercustomer"


# ── R3B-TENANT-RESERVED: AuthError TENANT_RESERVED answered 500 ───────


def test_r3b_a_user_owned_dev_tenant_answers_409(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Under QCOMPASS_ENV=dev, a request that reaches a user-owned 'dev' tenant got a 500."""
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    monkeypatch.setenv("QCOMPASS_ENV", "dev")
    monkeypatch.setenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", "1")
    mallory = _user("mallory-dev409@example.test")
    with _tenant_checks_suspended():  # a row from before the guard (main allowed it)
        squatted = str(_sql("insert into public.tenants (name, slug, created_by) values ('m', 'dev', %s) "
                            "returning id", mallory)[0][0])
        try:
            client = TestClient(build_app(), raise_server_exceptions=False)
            resp = client.post("/api/qcompass/domains/cosmology/runs", json={"manifest": _COSMOLOGY_PROBLEM})
            assert resp.status_code == 409, resp.text
            assert resp.json()["detail"]["code"] == "TENANT_RESERVED"
            assert "BLOCKED-ON-JAMES:rename-user-owned-dev-tenant" in resp.json()["detail"]["message"]
        finally:
            _sql("delete from public.tenants where id = %s", squatted)


# ── R3B-AGENT-DEV-GUARD: a re-run of 20261031200400's backfill ────────


@pytest.mark.parametrize("owned_by", ["creator", "member"])
def test_r3b_agent_rows_never_land_in_a_user_owned_dev_tenant(owned_by: str) -> None:
    """A single-version down/up of 20261031200400 re-ran its backfill and handed every tenant-less
    agent row (including those 20261102100100 had set back to null) to a user-owned 'dev'."""
    mallory = _user("mallory-rerun@example.test")
    with _tenant_checks_suspended():
        squatted = str(_sql(
            "insert into public.tenants (name, slug, created_by) values ('m', 'dev', %s) returning id",
            mallory if owned_by == "creator" else None,
        )[0][0])
        _sql("insert into public.tenant_members (tenant_id, user_id, role) values (%s, %s, 'owner')",
             squatted, mallory)
        try:
            _sql('insert into public.agent_tool_calls ("conversationId", tool, "requestJson", "responseJson", '
                 'ok, "createdAt") values (\'victim-convo\', \'get_run\', \'{}\', \'{}\', true, now())')
            rollback("20261031200400", _url())  # one version down, later ones stay applied
            assert apply_migrations(_url()) == ["20261031200400"]
            with _as(mallory) as conn:
                seen = conn.execute('select "conversationId" from public.agent_tool_calls').fetchall()
            assert seen == [], f"the user-owned 'dev' reads another customer's agent rows: {seen}"
            assert _sql("select tenant_id from public.agent_tool_calls") == [(None,)]
            # Direct writes are kept off it too; the service's own tenants are unaffected.
            _sql('update public.agent_tool_calls set tenant_id = %s', squatted)
            assert _sql("select tenant_id from public.agent_tool_calls") == [(None,)]
            acme = get_auth_store().ensure_tenant("acme")
            _sql('update public.agent_tool_calls set tenant_id = %s', acme)
            assert _sql("select tenant_id::text from public.agent_tool_calls") == [(acme,)]
        finally:
            _sql("delete from public.agent_tool_calls")
            _sql("delete from public.tenants where id = %s", squatted)


# ── R3B-REDACT: secret-named keys other than '*_token' were logged ────


def test_r3b_tool_call_log_redacts_every_secret_named_key(
    tenants: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RunConfig's agent.approvalTokenId (and tokenId, apiKey, client_secret, password) reached
    agent_tool_calls.requestJson, which every member of the tenant, viewers included, reads."""
    from ucgle_f1.m8_agent import server
    from ucgle_f1.m8_agent.memory.store import redact_secrets
    from ucgle_f1.m8_agent.models.base import ChatEvent

    client, acme = tenants["client"], tenants["acme"]["headers"]
    token = client.post("/api/approvals", json={"scopes": ["start_run"]}, headers=acme).json()["tokenId"]
    secrets_sent = {
        "config": {"agent": {"conversationId": "c", "approvalTokenId": token}},
        "tokenId": "appr_z", "apiKey": "k-1", "API_KEY": "k-2", "client_secret": "s-1",
        "Password": "p-1", "items": [{"refresh-token": "r-1"}],
    }

    class _Stub:
        def __init__(self, cfg: Any) -> None:
            self.config = cfg

        async def stream(self, messages: Any, tools: Any) -> Any:
            yield ChatEvent(type="tool_call", tool_call={"id": "c1", "name": "validate_config",
                                                         "arguments": secrets_sent})
            yield ChatEvent(type="finish")

    monkeypatch.setattr(server, "get_provider", _Stub)
    with client.stream("POST", "/v1/chat", json={"conversationId": "c_red", "messages": [], "modelId": "s"},
                       headers=acme) as resp:
        "".join(resp.iter_text())
    viewer = _user("viewer-red@example.test")
    get_auth_store().add_member("acme", viewer, "viewer")
    with _as(viewer) as conn:
        logged = [r[0] for r in conn.execute('select "requestJson" from public.agent_tool_calls').fetchall()]
    assert len(logged) == 1
    for secret in (token, "appr_z", "k-1", "k-2", "s-1", "p-1", "r-1"):
        assert secret not in logged[0], f"{secret!r} is readable in the tool-call log"
    assert json.loads(logged[0]) == {
        "config": {"agent": {"conversationId": "c", "approvalTokenId": "[redacted]"}},
        "tokenId": "[redacted]", "apiKey": "[redacted]", "API_KEY": "[redacted]",
        "client_secret": "[redacted]", "Password": "[redacted]", "items": [{"refresh-token": "[redacted]"}],
    }
    assert redact_secrets({"run_id": "r", "approval": {"Approval-Token-Id": "appr_q"}}) == {
        "run_id": "r", "approval": {"Approval-Token-Id": "[redacted]"},
    }


# ── R3B-TIER-REPORT: the forged-row report missed self-raised tiers ───


def test_r3b_forged_row_report_lists_paid_tiers_and_author_less_client_runs(tenants: dict[str, Any]) -> None:
    """qcompass_forged_row_report had no kind for a non-free tier (owners could raise their own
    until 20261102100000, and no billing sets tiers), nor for client runs whose author is gone."""
    acme, globex = tenants["acme"]["uuid"], tenants["globex"]["uuid"]
    _sql("update public.tenants set subscription_tier = 'enterprise' where id = %s", globex)
    dave = _user("dave-report@example.test")
    get_auth_store().add_member("acme", dave, "member")
    with _as(dave) as conn:
        conn.execute("insert into public.runs (id, author_user_id, tenant_id, config) values ('run_left', %s, %s, '{}')",
                     (dave, acme))
    _sql("delete from auth.users where id = %s", dave)
    report = {(kind, ref) for kind, ref, _t, _d in _sql("select * from public.qcompass_forged_row_report()")}
    assert ("tenant_tier_not_free", globex) in report, "a paid tier nobody billed is not listed"
    assert ("tenant_tier_not_free", acme) not in report, "a free tenant is listed"
    assert ("client_run_without_author", "run_left") in report
    assert _sql("select count(*) from public.runs where id = 'run_left'") == [(1,)], "reported, not deleted"


# ── R3B-PLAN-PATH: the plan sandbox was keyed by a renameable slug ────


def test_r3b_a_later_tenant_with_the_same_slug_gets_its_own_plan_sandbox(tenants: dict[str, Any]) -> None:
    """agent-sandbox/<slug>/: after acme renamed itself, a new tenant called 'acme' wrote its plans
    into the directory that holds the first acme's plans."""
    from ucgle_f1.m8_agent.memory import get_store

    root = Path(os.environ["UCGLE_F1_ARTIFACTS"])
    store = get_store()
    first = store.save_plan("c_shared", {"t": "first"}, tenant="acme")
    _sql("update public.tenants set slug = 'acme-renamed' where id = %s", tenants["acme"]["uuid"])
    second_uuid = get_auth_store().ensure_tenant("acme")
    assert second_uuid != tenants["acme"]["uuid"]
    second = store.save_plan("c_shared", {"t": "second"}, tenant="acme")
    first_dir, second_dir = (root / first.path).parent, (root / second.path).parent
    assert first_dir != second_dir, "two tenants share one plan sandbox"
    assert [p.name for p in first_dir.iterdir()] == [Path(first.path).name]
    assert json.loads((root / first.path).read_text()) == {"t": "first"}


# ── every migration of this lane is reversible ────────────────────────


@pytest.mark.parametrize("version", ["20261102120000", "20261102120100", "20261102120200"])
def test_r3b_migrations_are_reversible(version: str, tenants: dict[str, Any]) -> None:
    """Each round-3B migration has a down migration that restores the previous version, and
    re-applying it restores the same schema without losing data (R13)."""
    _submit(tenants["client"], tenants["acme"]["headers"], runId="kept-alias")
    _sql("update public.tenants set subscription_tier = 'pro' where id = %s", tenants["globex"]["uuid"])

    def schema() -> list[tuple[Any, ...]]:
        return _sql(
            "select 'policy', tablename || ':' || policyname, coalesce(qual, '') || coalesce(with_check, '') "
            "from pg_policies union all "
            "select 'index', indexname, indexdef from pg_indexes where schemaname = 'public' union all "
            "select 'constraint', conname, pg_get_constraintdef(oid) from pg_constraint "
            "where connamespace = 'public'::regnamespace union all "
            "select 'trigger', tgrelid::regclass::text || ':' || tgname, '' from pg_trigger "
            "where not tgisinternal union all "
            "select 'column', table_name || '.' || column_name, '' from information_schema.columns "
            "where table_schema = 'public' union all "
            "select 'function', p.proname, md5(p.prosrc) from pg_proc p "
            "where p.pronamespace = 'public'::regnamespace and p.proname like 'qcompass\\_%%' order by 1, 2"
        )

    versions = [r[0] for r in _sql(
        "select version from supabase_migrations.schema_migrations where version >= %s order by version", version,
    )]
    before = schema()
    for v in reversed(versions):
        rollback(v, _url())
    try:
        assert schema() != before
        if version == "20261102120000":
            # 20261102100300's alias index is back, and the marker's data is kept, renamed.
            assert _sql("select indexdef from pg_indexes where indexname = 'runs_tenant_client_run_id_key'")[0][0] \
                .endswith("WHERE ((client_run_id IS NOT NULL) AND (author_user_id IS NULL))")
            assert _sql("select _deprecated_origin_20261102120000 from public.runs "
                        "where client_run_id = 'kept-alias'") == [("api",)]
        if version <= "20261102120100":
            kinds = {r[0] for r in _sql("select kind from public.qcompass_forged_row_report()")}
            assert "tenant_tier_not_free" not in kinds, "down restores 20261102100200's report"
    finally:
        assert apply_migrations(_url()) == versions
    assert schema() == before
    assert _sql("select origin from public.runs where client_run_id = 'kept-alias'") == [("api",)]
    kinds = {r[0] for r in _sql("select kind from public.qcompass_forged_row_report()")}
    assert "tenant_tier_not_free" in kinds
