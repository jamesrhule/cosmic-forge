"""P3-02 / P3-03: runs go through main's Postgres queue and a real worker.

- the API enqueues and returns 202; it never runs the simulation;
- a run started before an API restart completes and streams its events
  from a fresh app, and its stored result reloads byte-identical (P3-03);
- progress comes from modules as they finish (never pre-emitted);
- leases: heartbeat renewal, janitor requeue, dead-letter with an incident;
- 50 concurrent fixture runs complete with two worker processes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from ucgle_f1.db import reset_engine
from ucgle_f1.jobs import JobQueue, reset_queue
from ucgle_f1.m8_agent.auth import get_auth_store, reset_auth_store
from ucgle_f1.m8_agent.server import build_app

H2 = {
    "manifest": {
        "domain": "chemistry",
        "version": "1.0",
        "problem": {
            "molecule": "H2", "basis": "sto-3g", "active_space": [2, 2],
            "backend_preference": "classical", "reference": "FCI", "shots": 1,
            "seed": 0, "geometry": "H 0 0 0\nH 0 0 0.74\n", "charge": 0, "spin": 0,
        },
        "backend_request": {"kind": "classical"},
    },
}


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("BLOCKED-ON-JAMES:DATABASE_URL (no test Postgres)")
    return url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, dict[str, str]]:
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    monkeypatch.delenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", raising=False)
    tok = get_auth_store().issue("acme", scopes=["read", "run"])
    headers = {"Authorization": f"Bearer {tok.token_id}", "X-QCompass-Tenant": "acme"}
    return TestClient(build_app()), headers


def _restart() -> TestClient:
    """Drop every in-process handle (engine, queue, stores) and build a new app."""
    reset_engine()
    reset_queue()
    reset_auth_store()
    return TestClient(build_app())


def _wait(pred, timeout: float = 120.0) -> None:  # type: ignore[no-untyped-def]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return
        time.sleep(0.1)
    raise AssertionError("timed out")


def test_submit_enqueues_and_returns_202_without_computing(api) -> None:  # type: ignore[no-untyped-def]
    client, headers = api
    resp = client.post("/api/qcompass/domains/chemistry/runs", json=H2, headers=headers)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    with psycopg.connect(_url()) as conn:
        kind, status, run_status = conn.execute(
            "select j.kind, j.status::text, r.status::text from public.jobs j "
            "join public.runs r on r.id = j.run_id where j.run_id = %s", (body["runId"],),
        ).fetchone()
    assert (kind, status, run_status) == ("qcompass.run", "queued", "queued")
    got = client.get(f"/api/qcompass/domains/chemistry/runs/{body['runId']}", headers=headers)
    assert got.json()["status"] == "queued"
    assert JobQueue().result(body["runId"]) is None, "nothing ran inside the request"


def test_invalid_manifest_is_422(api) -> None:  # type: ignore[no-untyped-def]
    client, headers = api
    resp = client.post(
        "/api/qcompass/domains/chemistry/runs",
        json={"manifest": {"domain": "chemistry", "version": "1.0"}}, headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_INPUT"


def test_run_survives_api_restart_and_streams_then_reloads_byte_identical(
    api, request: pytest.FixtureRequest,  # type: ignore[no-untyped-def]
) -> None:
    client, headers = api
    run_id = client.post("/api/qcompass/domains/chemistry/runs", json=H2, headers=headers).json()["runId"]
    del client
    fresh = _restart()  # the API restarts while the run is queued

    request.getfixturevalue("inprocess_worker")  # a worker comes up afterwards
    with fresh.stream("GET", f"/api/qcompass/domains/chemistry/runs/{run_id}/stream", headers=headers) as resp:
        assert resp.status_code == 200
        text = "".join(resp.iter_text())
    events = [line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("event:")]
    assert events[0] == "history"
    assert events[-1] == "end"
    progress = [json.loads(line.split(":", 1)[1]) for line in text.splitlines()
                if line.startswith("data:") and '"stage"' in line]
    assert [p["stage"] for p in progress] == ["prepare", "run"]
    assert all(p["seconds"] >= 0 for p in progress)
    assert events.index("progress") > events.index("status"), "progress only after the run starts"

    first = fresh.get(f"/api/qcompass/domains/chemistry/runs/{run_id}", headers=headers)
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "completed"
    assert body["provenance"]["classical_reference_hash"]
    assert body["payload"]["result"], "the full result is stored"

    again = _restart()  # P3-03: reload after another restart
    second = again.get(f"/api/qcompass/domains/chemistry/runs/{run_id}", headers=headers)
    assert second.content == first.content
    listed = again.get("/api/qcompass/domains/chemistry/runs", headers=headers).json()
    assert [r["id"] for r in listed] == [run_id]
    assert listed[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_cosmology_progress_comes_from_modules_as_they_finish(inprocess_worker: object) -> None:
    from ucgle_f1.domain import Couplings, Potential, Reheating, RunConfig
    from ucgle_f1.m8_agent.runs import get_registry

    cfg = RunConfig(
        potential=Potential(kind="starobinsky", params={"M": 1.0e-5}),
        couplings=Couplings(xi=1.0e-3, theta_grav=1.0e-3, f_a=1.0e17, M_star=1.0e18, M1=1.0e12, S_E2=1.0),
        reheating=Reheating(Gamma_phi=1.0e-6, T_reh_GeV=1.0e13),
        precision="standard",
    )
    reg = get_registry()
    rid = await reg.submit(cfg)
    seen = [ev async for ev in reg.stream(rid)]
    kinds = [ev.type for ev in seen]
    assert kinds[0] == "status" and seen[0].status == "queued"
    assert seen[1].type == "status" and seen[1].status == "running"
    progress = [ev for ev in seen if ev.type == "progress"]
    assert [p.module for p in progress] == ["M1", "M2", "M3", "M4", "M5", "M6"]
    assert [p.fraction for p in progress] == pytest.approx([1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6, 1.0])
    assert all("finished in" in (p.detail or "") for p in progress)
    assert kinds[-1] == "result"
    assert reg.result(rid) is not None
    # Wall-clock order: each progress row was written after the previous one.
    rows = JobQueue().events(rid)
    stamps = [r.created_at for r in rows if r.type == "progress"]
    assert stamps == sorted(stamps)


def _job(q: JobQueue, *, max_attempts: int) -> str:
    tenant = get_auth_store().ensure_tenant("acme")
    q.enqueue_run(
        run_id=f"run_lease_{max_attempts}", tenant_uuid=tenant, kind="qcompass.run",
        payload={"domain": "chemistry", "manifest": H2["manifest"]}, label="lease",
        config={"domain": "chemistry", "kind": "qcompass.run"}, max_attempts=max_attempts,
    )
    return f"run_lease_{max_attempts}"


def test_heartbeat_janitor_requeue_and_dead_letter() -> None:
    q = JobQueue()
    _job(q, max_attempts=2)
    job = q.claim("dead-worker", ["cpu"], lease_seconds=1)
    assert job is not None and job.attempts == 1
    assert q.heartbeat(job.id, "dead-worker", 1) is True
    assert q.heartbeat(job.id, "someone-else", 1) is False, "only the lease holder renews"
    time.sleep(1.2)  # the worker died: no more heartbeats
    assert q.reap() == 1
    assert q.job_status(job.id) == "queued", "requeued for another worker"
    again = q.claim("dead-worker-2", ["cpu"], lease_seconds=1)
    assert again is not None and again.id == job.id and again.attempts == 2
    time.sleep(1.2)
    assert q.reap() == 1
    assert q.job_status(job.id) == "failed", "dead-lettered at max_attempts"
    with psycopg.connect(_url()) as conn:
        error = conn.execute("select error from public.jobs where id = %s", (job.id,)).fetchone()[0]
        incidents = conn.execute(
            "select title, body from public.system_incidents where title like %s", (f"%{job.id}%",),
        ).fetchall()
    assert error.startswith("dead-letter")
    assert len(incidents) == 1 and "max_attempts=2" in incidents[0][1]
    # A stale worker can't complete a job the janitor already failed.
    q.complete(job.id, result={"late": True})
    assert q.job_status(job.id) == "failed"


def test_cancel_stops_the_lease() -> None:
    q = JobQueue()
    run_id = _job(q, max_attempts=3)
    job = q.claim("w", ["cpu"], lease_seconds=30)
    assert job is not None
    assert q.cancel_run(run_id) is True
    assert q.heartbeat(job.id, "w", 30) is False, "a cancelled job's heartbeat tells the worker to stop"
    assert q.get_run(run_id).status == "canceled"  # type: ignore[union-attr]


def test_fifty_concurrent_runs_complete_with_two_worker_processes(api) -> None:  # type: ignore[no-untyped-def]
    client, headers = api
    env = {**os.environ, "DATABASE_URL": os.environ["DATABASE_URL"]}
    procs = [
        subprocess.Popen(
            [sys.executable, "-m", "qcompass_worker", "--classes", "cpu", "--poll-seconds", "0.05"],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        for _ in range(2)
    ]
    try:
        # Both workers are polling before the burst arrives.
        time.sleep(3.0)
        run_ids = [
            client.post("/api/qcompass/domains/chemistry/runs", json=H2, headers=headers).json()["runId"]
            for _ in range(50)
        ]
        q = JobQueue()

        def all_done() -> bool:
            return all(q.get_run(r).status in {"completed", "failed"} for r in run_ids)  # type: ignore[union-attr]

        _wait(all_done, timeout=300)
        statuses = {q.get_run(r).status for r in run_ids}  # type: ignore[union-attr]
        assert statuses == {"completed"}
        with psycopg.connect(_url()) as conn:
            workers = conn.execute(
                "select count(distinct locked_by) from public.jobs where run_id = any(%s)", (run_ids,),
            ).fetchone()[0]
        assert workers == 2, "both workers took jobs"
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()
        for p in procs:
            err = p.stderr.read().decode()[-2000:] if p.stderr else ""
            if p.stderr:
                p.stderr.close()
            assert p.returncode in (0, -15), err


def test_run_events_stream_over_websocket(api, inprocess_worker: object) -> None:  # type: ignore[no-untyped-def]
    client, headers = api
    run_id = client.post("/api/qcompass/domains/chemistry/runs", json=H2, headers=headers).json()["runId"]
    got = []
    with client.websocket_connect(
        f"/ws/qcompass/domains/chemistry/runs/{run_id}/events", headers=headers,
    ) as ws:
        while True:
            try:
                msg = ws.receive_json()
            except Exception:  # noqa: BLE001 - server closed after the terminal status
                break
            got.append(msg)
            if msg["event"] == "status" and msg["data"]["status"] == "completed":
                break
    assert [m["event"] for m in got][:2] == ["status", "status"]
    assert [m["data"]["stage"] for m in got if m["event"] == "progress"] == ["prepare", "run"]
    assert got[-1]["data"]["status"] == "completed"
