"""Gate 1 security review (R16) of Wave 1: one regression test per finding.

Each test failed on 3d2355a (the reviewed head) and passes with the fix.
IDs match ``docs/build/lanes/W1-platform.md`` and
``docs/build/evidence/W1-security-fixes.md``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from ucgle_f1.db.migrate import apply_migrations, rollback
from ucgle_f1.jobs import JobQueue
from ucgle_f1.m8_agent.auth import active_tenant, get_auth_store
from ucgle_f1.m8_agent.server import build_app

REPO = Path(__file__).resolve().parents[2]
# A frozen RunResult-shaped payload (copied from the 3d2355a run fixture, which
# the physics lane now owns), so these tests never depend on that file.
RUN_FIXTURE = Path(__file__).resolve().parent / "data" / "gate1_run_result.json"


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("BLOCKED-ON-JAMES:DATABASE_URL (no test Postgres)")
    return url.replace("postgresql+psycopg://", "postgresql://")


def _user(conn: psycopg.Connection, email: str) -> str:
    return str(conn.execute("insert into auth.users (email) values (%s) returning id", (email,)).fetchone()[0])


def _as(conn: psycopg.Connection, user_id: str, *, verified: bool = False) -> None:
    """Act as a Supabase ``authenticated`` user (PostgREST's convention)."""
    conn.execute("set local role authenticated")
    claims: dict[str, Any] = {"sub": user_id, "role": "authenticated"}
    if verified:
        claims["email_verified"] = True
    conn.execute("select set_config('request.jwt.claims', %s, true)", (json.dumps(claims),))


@pytest.fixture
def tenants(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Two tenants with API keys, in a production configuration."""
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
    # No plan caps here (P3-05 limits are tested in test_plan_limits.py).
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute("update public.tenants set subscription_tier = 'enterprise' where slug in ('acme', 'globex')")
    return out


def _seed_ucgle_run(tenant_uuid: str, run_id: str) -> None:
    """A completed legacy (``ucgle_f1.run``) run with a stored RunResult and its events."""
    q = JobQueue()
    payload = json.loads(RUN_FIXTURE.read_text())
    payload["id"] = run_id
    q.enqueue_run(
        run_id=run_id, tenant_uuid=tenant_uuid, kind="ucgle_f1.run", payload={"config": payload["config"]},
        label=run_id, config={"kind": "ucgle_f1.run", "domain": "cosmology"}, enforce_limits=False,
    )
    q.save_result(run_id, payload)
    q.emit(None, run_id, tenant_uuid, "result", {"type": "result"})


def _seed_domain_run(tenant_uuid: str, run_id: str, domain: str = "chemistry") -> None:
    JobQueue().enqueue_run(
        run_id=run_id, tenant_uuid=tenant_uuid, kind="qcompass.run",
        payload={"domain": domain, "manifest": {}}, label=run_id,
        config={"domain": domain, "kind": "qcompass.run", "manifest": {}}, enforce_limits=False,
    )


# ── SEC-H1: the principal's tenant reaches every run path ─────────────


def test_h1_principal_tenant_reaches_sync_endpoints(tenants: dict[str, Any]) -> None:
    """The ContextVar set by require_scope is visible in a sync endpoint (threadpool)."""
    from ucgle_f1.m8_agent.principal import require_scope

    app = FastAPI()

    @app.get("/who", dependencies=[Depends(require_scope("read"))])
    def who() -> dict[str, str | None]:
        return {"tenant": active_tenant()}

    client = TestClient(app)
    assert client.get("/who", headers=tenants["acme"]["headers"]).json() == {"tenant": "acme"}
    assert client.get("/who", headers=tenants["globex"]["headers"]).json() == {"tenant": "globex"}


def test_h1_legacy_runs_are_tenant_scoped(tenants: dict[str, Any]) -> None:
    client = tenants["client"]
    _seed_ucgle_run(tenants["acme"]["uuid"], "run_acme_legacy")
    acme, globex = tenants["acme"]["headers"], tenants["globex"]["headers"]

    got = client.get("/api/runs/run_acme_legacy", headers=acme)
    assert got.status_code == 200, got.text
    assert got.json()["id"] == "run_acme_legacy"
    assert client.get("/api/runs/run_acme_legacy/audit", headers=acme).status_code == 200
    with client.stream("GET", "/api/runs/run_acme_legacy/stream", headers=acme) as resp:
        assert resp.status_code == 200
        assert "event: result" in "".join(resp.iter_text())

    for path in ("", "/audit", "/stream"):
        resp = client.get(f"/api/runs/run_acme_legacy{path}", headers=globex)
        assert resp.status_code == 404, (path, resp.status_code)


def test_h1_post_api_runs_files_the_run_under_the_callers_tenant(tenants: dict[str, Any]) -> None:
    client = tenants["client"]
    acme, globex = tenants["acme"]["headers"], tenants["globex"]["headers"]
    approval = client.post("/api/approvals", json={"scopes": ["start_run"]}, headers=acme).json()
    cfg = json.loads(RUN_FIXTURE.read_text())["config"]
    cfg["agent"] = {"conversationId": "c_sec", "hypothesisId": "h_sec"}
    resp = client.post("/api/runs", json={"config": cfg, "approval_token": approval["tokenId"]}, headers=acme)
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["runId"]
    rec = JobQueue().get_run(run_id)
    assert rec is not None and rec.tenant_id == tenants["acme"]["uuid"], "filed under acme, not 'dev'"
    assert get_auth_store().resolve_tenant("dev") is None, "no shared dev tenant is created"
    assert client.get(f"/api/runs/{run_id}/stream", headers=globex).status_code == 404


def test_h1_mcp_get_run_is_tenant_scoped(tenants: dict[str, Any]) -> None:
    client = tenants["client"]
    _seed_ucgle_run(tenants["acme"]["uuid"], "run_acme_mcp")
    ok = client.post("/mcp/tools/get_run", json={"run_id": "run_acme_mcp"}, headers=tenants["acme"]["headers"])
    assert ok.status_code == 200 and ok.json()["output"]["id"] == "run_acme_mcp"
    other = client.post("/mcp/tools/get_run", json={"run_id": "run_acme_mcp"}, headers=tenants["globex"]["headers"])
    assert other.status_code == 404


def test_h1_chat_tool_calls_are_tenant_scoped(tenants: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    from ucgle_f1.m8_agent import server
    from ucgle_f1.m8_agent.models.base import ChatEvent

    class _Stub:
        def __init__(self, cfg: Any) -> None:
            self.config = cfg

        async def stream(self, messages: Any, tools: Any) -> Any:
            yield ChatEvent(type="tool_call", tool_call={
                "id": "call_1", "name": "get_run", "arguments": {"run_id": "run_acme_chat"},
            })
            yield ChatEvent(type="finish")

    monkeypatch.setattr(server, "get_provider", _Stub)
    client = tenants["client"]
    _seed_ucgle_run(tenants["acme"]["uuid"], "run_acme_chat")
    body = {"conversationId": "c1", "messages": [], "modelId": "stub"}

    def tool_result(headers: dict[str, str]) -> dict[str, Any]:
        with client.stream("POST", "/v1/chat", json=body, headers=headers) as resp:
            assert resp.status_code == 200
            text = "".join(resp.iter_text())
        line = next(ln for ln in text.splitlines() if ln.startswith("data:") and '"tool_result"' in ln)
        return json.loads(line[len("data:"):])["result"]

    assert tool_result(tenants["acme"]["headers"])["ok"] is True
    leaked = tool_result(tenants["globex"]["headers"])
    assert leaked["ok"] is False and leaked["output"]["code"] == "NOT_FOUND"


def test_h1_no_dev_tenant_fallback_outside_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    from ucgle_f1.m8_agent.principal import TenantNotBound
    from ucgle_f1.m8_agent.runs import RunRegistry

    monkeypatch.delenv("QCOMPASS_ENV", raising=False)
    with pytest.raises(TenantNotBound):
        RunRegistry().get("run_x")
    monkeypatch.setenv("QCOMPASS_ENV", "dev")
    assert RunRegistry().get("run_x") is None  # dev only: the dev tenant


def test_h1_tenant_slug_dev_and_uuid_shapes_are_reserved() -> None:
    url = _url()
    with psycopg.connect(url, autocommit=True) as conn:
        mallory = _user(conn, "mallory@example.test")
    shaped = ("dev", "0b9c0e1e-6a8e-4c1e-9d52-0d6a3c1b2f10", "0B9C0E1E6A8E4C1E9D520D6A3C1B2F10",
              "{0b9c0e1e-6a8e-4c1e-9d52-0d6a3c1b2f10}")
    for slug in shaped:
        with psycopg.connect(url) as conn:
            _as(conn, mallory, verified=True)
            with pytest.raises(psycopg.errors.CheckViolation):
                conn.execute(
                    "insert into public.tenants (name, slug, created_by) values ('x', %s, %s)", (slug, mallory),
                )
    with psycopg.connect(url) as conn:
        _as(conn, mallory, verified=True)
        conn.execute("insert into public.tenants (name, slug, created_by) values ('m', 'mallory-co', %s)", (mallory,))
        conn.commit()
    with psycopg.connect(url) as conn, pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("update public.tenants set slug = 'dev' where slug = 'mallory-co'")
    # The service's own dev tenant (QCOMPASS_ENV=dev) is still possible.
    assert get_auth_store().ensure_tenant("dev")


def test_h1_resolve_tenant_prefers_the_id_match_and_slug_guard_is_reversible() -> None:
    url = _url()
    store = get_auth_store()
    victim = store.ensure_tenant("victim")
    rollback("20261031200000", url)  # constraint gone: a UUID-shaped slug can exist
    try:
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("insert into public.tenants (name, slug) values ('shadow', %s)", (victim,))
        for _ in range(5):
            assert store.resolve_tenant(victim) == (victim, "victim")
    finally:
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("delete from public.tenants where name = 'shadow'")
        assert apply_migrations(url) == ["20261031200000"]
    with psycopg.connect(url) as conn:
        assert conn.execute(
            "select convalidated from pg_constraint where conname = 'tenants_slug_reserved_check'"
        ).fetchone() == (True,)


# ── SEC-H2: only the service role enqueues; forged jobs are refused ───


def test_h2_member_cannot_insert_jobs_directly(tenants: dict[str, Any]) -> None:
    url = _url()
    _seed_domain_run(tenants["globex"]["uuid"], "run_victim_rls")
    with psycopg.connect(url, autocommit=True) as conn:
        alice = _user(conn, "alice@example.test")
    get_auth_store().add_member("acme", alice, "member")
    for run_id in (None, "run_victim_rls"):
        with psycopg.connect(url) as conn:
            _as(conn, alice)
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(
                    "insert into public.jobs (tenant_id, run_id, kind, payload, compute_class, priority, "
                    "max_attempts, created_by, status) values (%s, %s, 'qcompass.run', '{}', 'gpu_large', "
                    "1000, 99, %s, 'queued')",
                    (tenants["acme"]["uuid"], run_id, alice),
                )


def test_h2_forged_cross_tenant_job_does_not_touch_the_victim_run(tenants: dict[str, Any]) -> None:
    from ucgle_f1.worker import Worker

    url = _url()
    victim = tenants["globex"]["uuid"]
    _seed_domain_run(victim, "run_victim")
    q = JobQueue()
    with psycopg.connect(url, autocommit=True) as conn:
        # The victim's own job is not claimable by this worker's class.
        conn.execute("update public.jobs set compute_class = 'edge' where run_id = 'run_victim'")
        forged = str(conn.execute(
            "insert into public.jobs (tenant_id, run_id, kind, payload) values (%s, 'run_victim', "
            "'qcompass.run', '{}') returning id", (tenants["acme"]["uuid"],),
        ).fetchone()[0])
    events_before = len(q.events("run_victim"))
    calls: list[str] = []

    def overwrite(ctx: Any) -> dict[str, Any]:
        calls.append(ctx.run_id)
        ctx.queue.set_run_status(ctx.run_id, "completed")
        ctx.queue.save_result(ctx.run_id, {"pwned": True})
        ctx.emit("status", {"status": "completed"})
        return {}

    worker = Worker(q, ("cpu",), handlers={"qcompass.run": overwrite}, poll_seconds=0.05)
    assert worker.run_once() is True
    assert calls == [], "the handler never ran"
    assert q.job_status(forged) == "failed"
    with psycopg.connect(url) as conn:
        error = conn.execute("select error from public.jobs where id = %s", (forged,)).fetchone()[0]
    assert error.startswith("JOB_TENANT_MISMATCH")
    assert q.get_run("run_victim").status == "queued"  # type: ignore[union-attr]
    assert q.result("run_victim") is None
    assert len(q.events("run_victim")) == events_before


def test_h2_run_reads_ignore_rows_written_under_another_tenant(tenants: dict[str, Any]) -> None:
    q = JobQueue()
    victim, attacker = tenants["globex"]["uuid"], tenants["acme"]["uuid"]
    _seed_domain_run(victim, "run_mixed")
    q.emit(None, "run_mixed", attacker, "status", {"status": "completed", "forged": True})
    q.save_result("run_mixed", {"status_detail": "completed"})
    assert all(not e.payload.get("forged") for e in q.events("run_mixed", tenant_uuid=victim))
    assert q.result("run_mixed", tenant_uuid=attacker) is None
    assert q.result("run_mixed", tenant_uuid=victim) == {"status_detail": "completed"}
    assert q.result_text("run_mixed", tenant_uuid=attacker) is None


def test_h2_jobs_policy_migration_is_reversible() -> None:
    url = _url()

    def policies() -> set[str]:
        with psycopg.connect(url) as conn:
            return {r[0] for r in conn.execute(
                "select policyname from pg_policies where schemaname = 'public' and tablename = 'jobs'"
            )}

    assert "tenant members enqueue jobs" not in policies()
    rollback("20261031200100", url)
    try:
        assert "tenant members enqueue jobs" in policies(), "down restores main's policy"
        assert "service role enqueues jobs" not in policies()
    finally:
        assert apply_migrations(url) == ["20261031200100"]
    assert {"tenant members read jobs", "service role enqueues jobs"} <= policies()


# ── SEC-M1: run and result writes stay inside the writer's tenants ────


def test_m1_runs_and_results_cannot_be_written_into_another_tenant(tenants: dict[str, Any]) -> None:
    url = _url()
    acme, globex = tenants["acme"]["uuid"], tenants["globex"]["uuid"]
    with psycopg.connect(url, autocommit=True) as conn:
        alice = _user(conn, "alice-m1@example.test")
        conn.execute(
            "insert into public.runs (id, author_user_id, tenant_id, config) values ('run_planted', %s, %s, '{}')",
            (alice, globex),
        )
    get_auth_store().add_member("acme", alice, "member")

    def as_alice(sql: str, *params: Any) -> None:
        with psycopg.connect(url) as conn:
            _as(conn, alice)
            conn.execute(sql, params)
            conn.commit()

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        as_alice("insert into public.runs (id, author_user_id, tenant_id, config) values "
                 "('run_into_globex', %s, %s, '{}')", alice, globex)
    as_alice("insert into public.runs (id, author_user_id, tenant_id, config) values ('run_acme', %s, %s, '{}')",
             alice, acme)
    as_alice("insert into public.runs (id, author_user_id, config) values ('run_personal', %s, '{}')", alice)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        as_alice("update public.runs set tenant_id = %s where id = 'run_acme'", globex)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        as_alice("insert into public.run_results (run_id, payload) values ('run_planted', '{}')")
    as_alice("insert into public.run_results (run_id, payload) values ('run_acme', '{}')")
    as_alice("insert into public.run_results (run_id, payload) values ('run_personal', '{}')")


def test_m1_runs_policy_migration_is_reversible() -> None:
    url = _url()

    def check(policy: str) -> str:
        with psycopg.connect(url) as conn:
            return str(conn.execute(
                "select with_check from pg_policies where schemaname = 'public' and policyname = %s", (policy,),
            ).fetchone()[0])

    assert "is_tenant_member" in check("authenticated users create runs")
    rollback("20261031200200", url)
    try:
        for policy in ("authenticated users create runs", "authors update own runs", "authors write results"):
            assert "is_tenant_member" not in check(policy), f"down restores main's {policy!r}"
    finally:
        assert apply_migrations(url) == ["20261031200200"]
    for policy in ("authenticated users create runs", "authors update own runs", "authors write results"):
        assert "is_tenant_member" in check(policy)


# ── SEC-L2: a colliding runId is not an existence oracle ──────────────


def test_l2_run_id_collision_does_not_reveal_another_tenants_run(tenants: dict[str, Any]) -> None:
    client = tenants["client"]
    body = {"runId": "qc_shared_id", "manifest": {"problem": {}}}
    assert client.post("/api/qcompass/domains/cosmology/runs", json=body,
                       headers=tenants["globex"]["headers"]).status_code == 202
    foreign = client.post("/api/qcompass/domains/cosmology/runs", json=body, headers=tenants["acme"]["headers"])
    own = client.post("/api/qcompass/domains/cosmology/runs", json=body, headers=tenants["globex"]["headers"])
    assert foreign.status_code == own.status_code == 409
    assert foreign.json() == own.json(), "same answer whoever holds the id"
    message = foreign.json()["detail"]["message"]
    assert "exist" not in message and "qc_shared_id" not in message


# ── SEC-L3: wall-clock limit per job; bounded custom potentials ───────


def test_l3_hung_handler_is_abandoned_and_the_job_fails_with_job_timeout(tenants: dict[str, Any]) -> None:
    from ucgle_f1.worker import Worker

    q = JobQueue()
    _seed_domain_run(tenants["acme"]["uuid"], "run_hang")
    release = threading.Event()
    late: list[str] = []

    def hang(ctx: Any) -> dict[str, Any]:
        release.wait(60)
        try:
            ctx.queue.save_result(ctx.run_id, {"late": True})
        except Exception as exc:  # noqa: BLE001
            late.append(type(exc).__name__)
        return {}

    worker = Worker(q, ("cpu",), handlers={"qcompass.run": hang}, job_timeout_seconds=0.5, poll_seconds=0.05)
    t = threading.Thread(target=worker.run_once, daemon=True)
    started = time.monotonic()
    t.start()
    t.join(15)
    try:
        assert not t.is_alive(), "the loop returned although the handler hangs"
        assert time.monotonic() - started < 15
        assert q.get_run("run_hang").status == "failed"  # type: ignore[union-attr]
        with psycopg.connect(_url()) as conn:
            status, error = conn.execute(
                "select status::text, error from public.jobs where run_id = 'run_hang'"
            ).fetchone()
        assert status == "failed" and error.startswith("JOB_TIMEOUT")
        assert worker.healthy() is False, "a wedged handler thread makes /healthz fail"
    finally:
        release.set()
    deadline = time.monotonic() + 10
    while not late and time.monotonic() < deadline:
        time.sleep(0.05)
    assert late == ["JobCancelled"], "the abandoned handler can't write"
    assert q.result("run_hang") is None
    assert worker.healthy() is True


def test_l3_job_timeout_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    from ucgle_f1.worker import DEFAULT_JOB_TIMEOUT_SECONDS, Worker, job_timeout_seconds_default

    monkeypatch.delenv("QCOMPASS_JOB_TIMEOUT_SECONDS", raising=False)
    assert job_timeout_seconds_default() == DEFAULT_JOB_TIMEOUT_SECONDS == 3600
    for raw in ("0", "-5", "soon"):
        monkeypatch.setenv("QCOMPASS_JOB_TIMEOUT_SECONDS", raw)
        assert job_timeout_seconds_default() == 3600, "no way to disable the limit"
    monkeypatch.setenv("QCOMPASS_JOB_TIMEOUT_SECONDS", "90")
    assert Worker(JobQueue(), ("cpu",)).job_timeout_seconds == 90
    assert Worker(JobQueue(), ("cpu",), job_timeout_seconds=5).job_timeout_seconds == 5


@pytest.mark.parametrize("source", [
    "phi**(9**9**9)", "9**(64*64*64*64)", "((9**64)**64)**64", "phi**65", "1e31*phi", "'x'*phi",
    "phi + " * 600 + "phi",
])
def test_l3_custom_potential_rejects_unbounded_expressions_quickly(source: str) -> None:
    code = (
        "import sys\n"
        "from ucgle_f1.m2_scalar.potentials import _custom_expr\n"
        "try:\n"
        "    _custom_expr(sys.argv[1])\n"
        "except ValueError as exc:\n"
        "    print('rejected:', exc)\n"
        "else:\n"
        "    print('accepted')\n"
    )
    try:
        out = subprocess.run(
            [sys.executable, "-c", code, source], capture_output=True, text=True, timeout=60, check=True,
        ).stdout
    except subprocess.TimeoutExpired:
        pytest.fail(f"parsing {source[:40]!r} did not finish")
    assert out.startswith("rejected: custom potential:"), out


def test_l3_custom_potential_still_accepts_real_potentials() -> None:
    from ucgle_f1.m2_scalar.potentials import _custom_expr

    for source in ("m**2*phi**2/2", "a * phi**2 + b * cos(phi)", "L**4*(1 - cos(phi/f_a))",
                   "phi**64", "(phi**2)**30", "Rational(3, 4)*M**2*(1 - exp(-sqrt(Rational(2, 3))*phi))**2",
                   "1e-10*phi**4 + 1.3e-5"):
        assert _custom_expr(source) is not None


# ── SEC-L4: visualization only for the caller's runs; no server paths ─


def test_l4_visualization_requires_a_run_of_the_callers_tenant(tenants: dict[str, Any]) -> None:
    client = tenants["client"]
    _seed_domain_run(tenants["globex"]["uuid"], "run_globex_viz", domain="hep")
    _seed_domain_run(tenants["acme"]["uuid"], "run_acme_viz", domain="hep")
    acme = tenants["acme"]["headers"]
    for run_id in ("never_submitted", "run_globex_viz"):
        resp = client.get(f"/api/qcompass/domains/hep/runs/{run_id}/visualization", headers=acme)
        assert resp.status_code == 404, run_id
        with pytest.raises(WebSocketDisconnect) as closed:
            with client.websocket_connect(
                f"/ws/qcompass/domains/hep/runs/{run_id}/visualization", headers=acme,
            ) as ws:
                ws.receive_bytes()
        assert closed.value.code == 1008
    acme_root = tenants["artifacts"] / "qcompass" / "acme"
    written = list(acme_root.rglob("*")) if acme_root.exists() else []
    assert written == [], f"nothing is written for a run the caller doesn't own: {written}"
    ok = client.get("/api/qcompass/domains/hep/runs/run_acme_viz/visualization?max_frames=4", headers=acme)
    assert ok.status_code == 200 and ok.json()["n_frames"] >= 1


def test_l4_submit_returns_a_logical_sidecar_reference(tenants: dict[str, Any]) -> None:
    client = tenants["client"]
    resp = client.post("/api/qcompass/domains/cosmology/runs", json={"manifest": {"problem": {}}},
                       headers=tenants["acme"]["headers"])
    assert resp.status_code == 202
    ref = resp.json()["provenanceSidecar"]
    run_id = resp.json()["runId"]
    assert ref == f"qcompass/acme/cosmology/{run_id}.provenance.json"
    assert str(tenants["artifacts"]) not in resp.text
    assert (tenants["artifacts"] / ref).is_file()


# ── Gate 1 code review ────────────────────────────────────────────────


def test_b2_visualization_frames_are_labelled_synthetic(tenants: dict[str, Any]) -> None:
    from cosmic_forge_viz.protocol import decode

    client = tenants["client"]
    _seed_domain_run(tenants["acme"]["uuid"], "run_b2", domain="hep")
    acme = tenants["acme"]["headers"]
    body = client.get("/api/qcompass/domains/hep/runs/run_b2/visualization?max_frames=4", headers=acme).json()
    assert body["synthetic"] is True and body["source"] == "synthetic-bake"
    with client.websocket_connect("/ws/qcompass/domains/hep/runs/run_b2/visualization", headers=acme) as ws:
        header = decode(ws.receive_bytes())
    assert header["type"] == "header" and header["payload"]["synthetic"] is True


def _lease_job(q: JobQueue, tenant_uuid: str, run_id: str, *, max_attempts: int = 3) -> None:
    q.enqueue_run(
        run_id=run_id, tenant_uuid=tenant_uuid, kind="qcompass.run",
        payload={"domain": "chemistry", "manifest": {}}, label=run_id,
        config={"domain": "chemistry", "kind": "qcompass.run"}, max_attempts=max_attempts, enforce_limits=False,
    )


def test_sf1_dead_letter_fails_the_run_and_writes_a_terminal_event(tenants: dict[str, Any]) -> None:
    q = JobQueue()
    _lease_job(q, tenants["acme"]["uuid"], "run_dead", max_attempts=1)
    job = q.claim("dying-worker", ["cpu"], lease_seconds=1)
    assert job is not None
    q.set_run_status("run_dead", "running", job_id=job.id, worker_id="dying-worker")
    time.sleep(1.2)
    assert q.reap() == 1
    assert q.job_status(job.id) == "failed"
    assert q.get_run("run_dead").status == "failed"  # type: ignore[union-attr]
    last = q.events("run_dead", tenant_uuid=tenants["acme"]["uuid"])[-1]
    assert last.type == "status" and last.payload["status"] == "failed"
    # The stream now ends on its own.
    with tenants["client"].stream(
        "GET", "/api/qcompass/domains/chemistry/runs/run_dead/stream", headers=tenants["acme"]["headers"],
    ) as resp:
        text = "".join(resp.iter_text())
    assert "event: end" in text


def _bounded(fn: Any, timeout: float = 30.0) -> Any:
    out: dict[str, Any] = {}

    def run() -> None:
        try:
            out["value"] = fn()
        except BaseException as exc:  # noqa: BLE001
            out["error"] = exc

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    assert not t.is_alive(), "the stream never ended"
    if "error" in out:
        raise out["error"]
    return out["value"]


def test_sf1_streams_end_with_an_error_event_when_idle(
    tenants: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio

    from ucgle_f1.domain import ServiceError
    from ucgle_f1.m8_agent.runs import RunRegistry

    monkeypatch.setenv("QCOMPASS_STREAM_IDLE_SECONDS", "0.5")
    client, acme = tenants["client"], tenants["acme"]["headers"]
    _seed_domain_run(tenants["acme"]["uuid"], "run_idle")  # queued; no worker

    def sse() -> str:
        with client.stream("GET", "/api/qcompass/domains/chemistry/runs/run_idle/stream", headers=acme) as r:
            return "".join(r.iter_text())

    text = _bounded(sse)
    assert "event: error" in text and "STREAM_ABORTED" in text and text.rstrip().endswith("data: {}")

    def ws() -> list[dict[str, Any]]:
        got = []
        with client.websocket_connect("/ws/qcompass/domains/chemistry/runs/run_idle/events", headers=acme) as w:
            try:
                while True:
                    got.append(w.receive_json())
            except WebSocketDisconnect:
                return got

    msgs = _bounded(ws)
    assert msgs[-1]["event"] == "error" and msgs[-1]["data"]["code"] == "STREAM_ABORTED"

    JobQueue().enqueue_run(
        run_id="run_idle_legacy", tenant_uuid=tenants["acme"]["uuid"], kind="ucgle_f1.run", payload={},
        label="x", config={"kind": "ucgle_f1.run", "domain": "cosmology"}, enforce_limits=False,
    )

    async def legacy() -> None:
        async for _ in RunRegistry().stream("run_idle_legacy", tenant="acme"):
            pass

    with pytest.raises(ServiceError) as aborted:
        _bounded(lambda: asyncio.run(legacy()))
    assert aborted.value.code == "STREAM_ABORTED"


def test_sf2_a_stale_worker_cannot_touch_a_reclaimed_job(tenants: dict[str, Any]) -> None:
    q = JobQueue()
    _lease_job(q, tenants["acme"]["uuid"], "run_reclaimed")
    a = q.claim("worker-a", ["cpu"], lease_seconds=1)
    assert a is not None
    time.sleep(1.2)
    assert q.reap() == 1  # A's lease expired: requeued
    b = q.claim("worker-b", ["cpu"], lease_seconds=30)
    assert b is not None and b.id == a.id
    assert q.set_run_status("run_reclaimed", "running", job_id=b.id, worker_id="worker-b") is True
    # Worker A wakes up and tries to finish.
    assert q.complete(a.id, worker_id="worker-a", result={"from": "a"}) is False
    assert q.complete(a.id, worker_id="worker-a", error="boom") is False
    assert q.set_run_status("run_reclaimed", "failed", job_id=a.id, worker_id="worker-a") is False
    assert q.save_result("run_reclaimed", {"from": "a"}, job_id=a.id, worker_id="worker-a") is False
    assert q.emit(a, "run_reclaimed", a.tenant_id, "status", {"status": "failed"}, worker_id="worker-a") is False
    assert q.job_status(b.id) == "running"
    assert q.get_run("run_reclaimed").status == "running"  # type: ignore[union-attr]
    assert q.result("run_reclaimed") is None
    # B, the lease holder, completes it.
    assert q.save_result("run_reclaimed", {"from": "b"}, job_id=b.id, worker_id="worker-b") is True
    assert q.complete(b.id, worker_id="worker-b", result={}) is True
    assert q.job_status(b.id) == "succeeded"
    with psycopg.connect(_url()) as conn, pytest.raises(psycopg.errors.RaiseException):
        conn.execute("select set_config('request.jwt.claims', '{\"role\":\"service_role\"}', true)")
        conn.execute("select public.complete_job(%s::uuid, null::jsonb, null::text)", (b.id,))


def test_sf2_cancel_racing_completion_keeps_the_run_canceled(tenants: dict[str, Any]) -> None:
    from ucgle_f1.worker import Worker

    q = JobQueue()
    _lease_job(q, tenants["acme"]["uuid"], "run_race")
    in_handler, cancelled = threading.Event(), threading.Event()
    outcome: list[str] = []

    def finish_after_cancel(ctx: Any) -> dict[str, Any]:
        ctx.queue.set_run_status(ctx.run_id, "running")
        in_handler.set()
        cancelled.wait(20)
        try:
            ctx.queue.save_result(ctx.run_id, {"late": True})
            ctx.queue.set_run_status(ctx.run_id, "completed")
            outcome.append("wrote")
        except Exception as exc:  # noqa: BLE001
            outcome.append(type(exc).__name__)
            raise
        return {}

    worker = Worker(q, ("cpu",), handlers={"qcompass.run": finish_after_cancel}, heartbeat_seconds=60)
    t = threading.Thread(target=worker.run_once, daemon=True)
    t.start()
    assert in_handler.wait(20)
    assert q.cancel_run("run_race") is True
    cancelled.set()
    t.join(20)
    assert outcome == ["JobCancelled"]
    assert q.get_run("run_race").status == "canceled"  # type: ignore[union-attr]
    assert q.result("run_race") is None
    # Nothing, lease or not, moves a canceled run.
    assert q.set_run_status("run_race", "completed") is False
    assert q.get_run("run_race").status == "canceled"  # type: ignore[union-attr]


def test_sf1_sf2_queue_migration_is_reversible() -> None:
    url = _url()

    def procs() -> set[str]:
        with psycopg.connect(url) as conn:
            return {r[0] for r in conn.execute(
                "select pg_get_function_identity_arguments(oid) from pg_proc where proname = 'complete_job'"
            )}

    assert "_job_id uuid, _worker_id text, _result jsonb, _error text" in procs()
    rollback("20261031200300", url)
    try:
        assert procs() == {"_job_id uuid, _result jsonb, _error text"}
        with psycopg.connect(url) as conn:
            body = conn.execute("select prosrc from pg_proc where proname = 'reap_expired_jobs'").fetchone()[0]
        assert "job_events" not in body, "down restores the 20261031180000 janitor"
    finally:
        assert apply_migrations(url) == ["20261031200300"]
    assert len(procs()) == 2


def test_sf4_agent_memory_is_tenant_scoped(tenants: dict[str, Any]) -> None:
    from ucgle_f1.m8_agent.memory import get_store

    client = tenants["client"]
    acme, globex = tenants["acme"]["headers"], tenants["globex"]["headers"]
    # Approval tokens verify only in the tenant that issued them.
    token = client.post("/api/approvals", json={"scopes": ["start_run"]}, headers=acme).json()["tokenId"]
    cfg = json.loads(RUN_FIXTURE.read_text())["config"]
    cfg["agent"] = {"conversationId": "c_sf4", "hypothesisId": "h_sf4"}
    stolen = client.post("/api/runs", json={"config": cfg, "approval_token": token}, headers=globex)
    assert stolen.status_code == 403 and stolen.json()["detail"]["code"] == "APPROVAL_REQUIRED"
    assert client.post("/api/runs", json={"config": cfg, "approval_token": token}, headers=acme).status_code == 200
    # Patches and hypotheses: another tenant can't see or act on them.
    patch = client.post("/mcp/tools/propose_patch", headers=acme, json={
        "conversation_id": "c_sf4", "target_path": "x.py", "rationale": "r", "unified_diff": "--- a\n+++ b\n",
    }).json()["output"]["patchId"]
    for tool in ("dry_run_patch", "request_human_review"):
        resp = client.post(f"/mcp/tools/{tool}", json={"patch_id": patch, "in_docker": False}, headers=globex)
        assert resp.status_code == 404, tool
    assert client.post("/mcp/tools/request_human_review", json={"patch_id": patch}, headers=acme).status_code == 200
    hyp = client.post("/mcp/tools/record_hypothesis", headers=acme,
                      json={"conversation_id": "c_sf4", "text": "t"}).json()["output"]["hypothesisId"]
    store = get_store()
    assert store.get_hypothesis(hyp, tenant="acme") is not None
    assert store.get_hypothesis(hyp, tenant="globex") is None
    assert store.run_link(client.get("/api/qcompass/domains/cosmology/runs", headers=acme).json()[0]["id"],
                          tenant="globex") is None
    store.record_tool_call("c_sf4", "t", {}, {}, True, tenant="acme")
    assert len(store.tool_calls("c_sf4", tenant="acme")) == 1
    assert store.tool_calls("c_sf4", tenant="globex") == []
    # RLS: members read their own tenant's agent rows only.
    url = _url()
    with psycopg.connect(url, autocommit=True) as conn:
        alice, mallory = _user(conn, "alice-sf4@example.test"), _user(conn, "mallory-sf4@example.test")
    get_auth_store().add_member("acme", alice, "member")
    get_auth_store().add_member("globex", mallory, "member")
    for user, expected in ((alice, 1), (mallory, 0)):
        with psycopg.connect(url) as conn:
            _as(conn, user)
            assert conn.execute("select count(*) from public.agent_patches").fetchone()[0] == expected
            assert conn.execute("select count(*) from public.agent_approval_tokens").fetchone()[0] == 0
            conn.rollback()


def test_sf4_agent_tenancy_migration_is_reversible_without_data_loss(tenants: dict[str, Any]) -> None:
    from ucgle_f1.m8_agent.memory import get_store

    url = _url()
    hyp = get_store().record_hypothesis("c_keep", "keep me", tenant="acme").hypothesisId
    rollback("20261031200400", url)
    try:
        with psycopg.connect(url) as conn:
            kept = conn.execute(
                'select _deprecated_tenant_id_20261031200400::text from public.agent_hypotheses '
                'where "hypothesisId" = %s', (hyp,),
            ).fetchone()[0]
        assert kept == tenants["acme"]["uuid"], "R13: the tenant column is renamed, not dropped"
    finally:
        assert apply_migrations(url) == ["20261031200400"]
    assert get_store().get_hypothesis(hyp, tenant="acme") is not None
