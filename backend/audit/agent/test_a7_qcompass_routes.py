"""A7 — qcompass HTTP + WS routes contract (PROMPT 8 v2 §D).

Pins the v2 §DoD invariants:

  - Each new endpoint returns valid JSON-Schema'd payload.
  - Provenance sidecar is created on POST runs.
  - SSE stream replays history before live-tailing.
  - WS frames are valid (decoded via cosmic_forge_viz.protocol).
  - Scan registry round-trips POST → GET → DELETE.

These tests use starlette's TestClient against the in-process
FastAPI app, so no real network. The cosmology-only A1-A6 audits
stay byte-stable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("starlette")

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from cosmic_forge_viz.protocol import decode
from ucgle_f1.m8_agent.scans import reset_scan_registry
from ucgle_f1.m8_agent.server import build_app


@pytest.fixture(scope="module")
def app_client() -> TestClient:
    reset_scan_registry()
    app = build_app()
    return TestClient(app)


@pytest.mark.a_audit
def test_list_domains_returns_known_set(app_client: TestClient) -> None:
    resp = app_client.get("/api/qcompass/domains")
    assert resp.status_code == 200
    body = resp.json()
    ids = {d["id"] for d in body["domains"]}
    # The v2 stable set: cosmology + chemistry are always present
    # because their plugins ship in the workspace.
    assert "cosmology" in ids or any("cosmology" in i for i in ids)
    assert "chemistry" in ids


@pytest.mark.a_audit
def test_domain_schema_is_json_object(app_client: TestClient) -> None:
    resp = app_client.get("/api/qcompass/domains/chemistry/schema")
    assert resp.status_code == 200
    schema = resp.json()
    assert isinstance(schema, dict)
    assert schema.get("type") in {"object", None} or "$ref" in schema


@pytest.mark.a_audit
def test_post_run_writes_provenance_sidecar(app_client: TestClient) -> None:
    resp = app_client.post(
        "/api/qcompass/domains/chemistry/runs",
        json={
            "manifest": {
                "domain": "chemistry",
                "version": "1.0",
                "problem": {
                    "molecule": "H2",
                    "basis": "sto-3g",
                    "active_space": [2, 2],
                    "backend_preference": "classical",
                    "reference": "FCI",
                    "shots": 1,
                    "seed": 0,
                    "geometry": "H 0 0 0\nH 0 0 0.74\n",
                    "charge": 0,
                    "spin": 0,
                },
                "backend_request": {"kind": "classical"},
            },
        },
    )
    assert resp.status_code in {200, 202}
    body = resp.json()
    assert body["domain"] == "chemistry"
    assert body["runId"]
    sidecar = Path(body["provenanceSidecar"])
    assert sidecar.exists(), f"sidecar missing at {sidecar}"
    payload = json.loads(sidecar.read_text())
    assert payload["domain"] == "chemistry"
    assert payload["runId"] == body["runId"]
    assert "manifest" in payload
    assert "provenance" in payload


@pytest.mark.a_audit
def test_get_run_returns_sidecar_payload(app_client: TestClient) -> None:
    sub = app_client.post(
        "/api/qcompass/domains/cosmology/runs",
        json={"manifest": {"problem": {}}},
    ).json()
    run_id = sub["runId"]
    resp = app_client.get(f"/api/qcompass/domains/cosmology/runs/{run_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["runId"] == run_id
    assert body["domain"] == "cosmology"


@pytest.mark.a_audit
def test_get_run_404_when_unknown(app_client: TestClient) -> None:
    resp = app_client.get(
        "/api/qcompass/domains/chemistry/runs/qc_does_not_exist",
    )
    assert resp.status_code == 404


@pytest.mark.a_audit
def test_sse_stream_replays_history_then_status(
    app_client: TestClient,
) -> None:
    sub = app_client.post(
        "/api/qcompass/domains/chemistry/runs",
        json={"manifest": {"problem": {"molecule": "H2", "basis": "sto-3g"}}},
    ).json()
    run_id = sub["runId"]
    with app_client.stream(
        "GET",
        f"/api/qcompass/domains/chemistry/runs/{run_id}/stream",
    ) as resp:
        assert resp.status_code == 200
        text = "".join(resp.iter_text())
    assert "history" in text   # event name
    assert "status" in text


@pytest.mark.a_audit
def test_visualization_endpoint_returns_typed_timeline(
    app_client: TestClient,
) -> None:
    resp = app_client.get(
        "/api/qcompass/domains/hep/runs/schwinger-1plus1d/visualization?max_frames=8",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["domain"] == "hep"
    assert body["n_frames"] >= 1
    # Each frame must carry the BaseFrame fields.
    for frame in body["frames"]:
        assert "tau" in frame
        assert "phase" in frame
        assert "active_terms" in frame


@pytest.mark.a_audit
def test_visualization_unknown_domain_404(app_client: TestClient) -> None:
    resp = app_client.get(
        "/api/qcompass/domains/gravity/runs/foo/visualization",
    )
    assert resp.status_code == 404


@pytest.mark.a_audit
def test_ws_visualization_streams_decodable_frames(
    app_client: TestClient,
) -> None:
    sub = app_client.post(
        "/api/qcompass/domains/cosmology/runs",
        json={"manifest": {"problem": {}}},
    ).json()
    run_id = sub["runId"]
    seen_header = False
    seen_end = False
    n_frames = 0
    with app_client.websocket_connect(
        f"/ws/qcompass/domains/cosmology/runs/{run_id}/visualization",
    ) as ws:
        try:
            while True:
                msg = decode(ws.receive_bytes())
                if msg["type"] == "header":
                    seen_header = True
                    assert msg["payload"]["domain"] == "cosmology"
                elif msg["type"] == "frame":
                    n_frames += 1
                elif msg["type"] == "end":
                    seen_end = True
                    break
        except WebSocketDisconnect:
            pass
    assert seen_header
    assert seen_end
    assert n_frames >= 1


# ── Scans ─────────────────────────────────────────────────────────


@pytest.mark.a_audit
def test_scan_create_get_list_delete_round_trip(
    app_client: TestClient,
) -> None:
    create = app_client.post("/api/scans", json={
        "domain": "cosmology",
        "kind": "xi-theta",
        "axes": {"x": "xi", "y": "theta"},
        "payload": {"eta_B_grid": [[1e-10, 2e-10], [3e-10, 4e-10]]},
        "provenance": {"classical_reference_hash": "deadbeef"},
    })
    assert create.status_code == 201
    record = create.json()
    scan_id = record["scanId"]
    assert record["domain"] == "cosmology"
    assert record["kind"] == "xi-theta"

    got = app_client.get(f"/api/scans/{scan_id}")
    assert got.status_code == 200
    assert got.json()["scanId"] == scan_id

    listed = app_client.get("/api/scans?domain=cosmology")
    assert listed.status_code == 200
    ids = [s["scanId"] for s in listed.json()["scans"]]
    assert scan_id in ids

    deleted = app_client.delete(f"/api/scans/{scan_id}")
    assert deleted.status_code == 200

    after = app_client.get(f"/api/scans/{scan_id}")
    assert after.status_code == 404


@pytest.mark.a_audit
def test_scan_post_requires_domain_and_kind(
    app_client: TestClient,
) -> None:
    resp = app_client.post("/api/scans", json={"axes": {}, "payload": {}})
    assert resp.status_code == 422
