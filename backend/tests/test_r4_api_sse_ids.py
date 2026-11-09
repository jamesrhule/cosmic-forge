"""W1 round 4, lane R4-API, item R4-6: run event streams carry SSE ``id:``.

The round-3B FE3 verifier (WORKER NIT, partial): the frontend's
``runEventStream`` recognises a replayed event by its SSE id, but neither
server route that streams run events sent one, so production reconnects still
deduplicated by count, and an event that committed late was delivered twice
while another was lost. Each event read from ``public.job_events`` now carries
its row id as ``id:``; events the route makes up (``history``, ``end``, a
``STREAM_ABORTED`` error, a status for a run that ended without one) carry
none, so the client's count-based fallback still covers them.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from ucgle_f1.jobs import JobQueue
from ucgle_f1.m8_agent.auth import get_auth_store
from ucgle_f1.m8_agent.server import build_app

RUN_FIXTURE = Path(__file__).resolve().parent / "data" / "gate1_run_result.json"


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("BLOCKED-ON-JAMES:DATABASE_URL (no test Postgres)")
    return url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture
def acme(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    monkeypatch.delenv("QCOMPASS_ENV", raising=False)
    monkeypatch.delenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", raising=False)
    store = get_auth_store()
    tok = store.issue("acme", scopes=["read", "run"])
    tenant_uuid = store.ensure_tenant("acme")
    return {
        "client": TestClient(build_app()),
        "headers": {"Authorization": f"Bearer {tok.token_id}", "X-QCompass-Tenant": "acme"},
        "uuid": str(tenant_uuid),
    }


def _blocks(text: str) -> list[dict[str, str]]:
    """Each SSE block's fields (``id``, ``event``, ``data``)."""
    out = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if ":" in line and not line.startswith(":"):
                key, value = line.split(":", 1)
                fields[key] = value[1:] if value.startswith(" ") else value
        if "event" in fields:
            out.append(fields)
    return out


def _event_ids(run_id: str) -> list[tuple[int, str]]:
    with psycopg.connect(_url()) as conn:
        rows = conn.execute(
            "select id, type from public.job_events where run_id = %s order by id", (run_id,),
        ).fetchall()
    return [(int(i), t) for i, t in rows]


def test_r4_6_domain_run_stream_sends_each_events_row_id(acme: dict[str, Any]) -> None:
    run_id = f"qc_r4_sse_{uuid.uuid4().hex[:12]}"
    q = JobQueue()
    q.enqueue_run(
        run_id=run_id, tenant_uuid=acme["uuid"], kind="qcompass.run",
        payload={"domain": "chemistry", "manifest": {}}, label=run_id,
        config={"domain": "chemistry", "kind": "qcompass.run", "manifest": {}}, enforce_limits=False,
    )
    q.emit(None, run_id, acme["uuid"], "status", {"status": "running"})
    q.emit(None, run_id, acme["uuid"], "heartbeat", {})
    q.emit(None, run_id, acme["uuid"], "progress", {"stage": "run", "fraction": 0.5})
    q.emit(None, run_id, acme["uuid"], "status", {"status": "completed"})
    with acme["client"].stream(
        "GET", f"/api/qcompass/domains/chemistry/runs/{run_id}/stream", headers=acme["headers"],
    ) as resp:
        assert resp.status_code == 200
        blocks = _blocks("".join(resp.iter_text()))
    rows = [(i, t) for i, t in _event_ids(run_id) if t != "heartbeat"]  # with enqueue's 'queued'
    assert [t for _, t in rows][-3:] == ["status", "progress", "status"]
    assert [b["event"] for b in blocks] == ["history", *(t for _, t in rows), "end"]
    assert "id" not in blocks[0] and "id" not in blocks[-1], "made-up events carry no id"
    assert [(int(b["id"]), b["event"]) for b in blocks[1:-1]] == rows
    assert json.loads(blocks[-3]["data"]) == {"stage": "run", "fraction": 0.5}


def test_r4_6_cosmology_run_stream_sends_each_events_row_id(acme: dict[str, Any]) -> None:
    run_id = f"run_r4_sse_{uuid.uuid4().hex[:12]}"
    q = JobQueue()
    payload = json.loads(RUN_FIXTURE.read_text())
    payload["id"] = run_id
    q.enqueue_run(
        run_id=run_id, tenant_uuid=acme["uuid"], kind="ucgle_f1.run", payload={"config": payload["config"]},
        label=run_id, config={"kind": "ucgle_f1.run", "domain": "cosmology"}, enforce_limits=False,
    )
    q.emit(None, run_id, acme["uuid"], "status", {"status": "running", "at": "2026-11-02T19:00:00Z"})
    q.emit(None, run_id, acme["uuid"], "log",
           {"module": "M1", "level": "info", "text": "background", "at": "2026-11-02T19:00:01Z"})
    q.save_result(run_id, payload)
    q.emit(None, run_id, acme["uuid"], "result", {"type": "result"})
    with acme["client"].stream("GET", f"/api/runs/{run_id}/stream", headers=acme["headers"]) as resp:
        assert resp.status_code == 200
        blocks = _blocks("".join(resp.iter_text()))
    rows = _event_ids(run_id)  # with enqueue's 'queued' status
    assert [t for _, t in rows][-3:] == ["status", "log", "result"]
    assert [(int(b["id"]), b["event"]) for b in blocks] == rows
    assert json.loads(blocks[-1]["data"])["payload"]["id"] == run_id
