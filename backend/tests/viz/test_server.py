"""FastAPI server REST + SSE + WS smoke tests."""

from __future__ import annotations

import json
import time

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from cosmic_forge_viz.protocol import decode_frame, has_msgpack  # noqa: E402
from cosmic_forge_viz.server import create_app  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(default_total_frames=60))


def test_manifest_endpoint(client: TestClient) -> None:
    res = client.get("/api/runs/chemistry/chem-test/manifest")
    assert res.status_code == 200
    body = res.json()
    assert body["domain"] == "chemistry"
    assert body["run_id"] == "chem-test"
    assert body["frame_count"] == 60
    assert body["formula_variant"] is None


def test_manifest_unknown_domain(client: TestClient) -> None:
    assert client.get("/api/runs/phantom/x/manifest").status_code == 404


def test_manifest_cosmology_variant_inference(client: TestClient) -> None:
    body = client.get("/api/runs/cosmology/ucgle-f3-demo/manifest").json()
    assert body["formula_variant"] == "F3"


def test_full_timeline(client: TestClient) -> None:
    res = client.get("/api/runs/chemistry/chem-test/visualization?total=20")
    assert res.status_code == 200
    body = res.json()
    assert body["manifest"]["frame_count"] == 20
    assert len(body["frames"]) == 20
    assert all(f["domain"] == "chemistry" for f in body["frames"])


def test_full_timeline_with_max_frames(client: TestClient) -> None:
    body = client.get(
        "/api/runs/cosmology/r/visualization?total=60&max_frames=10"
    ).json()
    assert len(body["frames"]) == 10


def test_full_timeline_under_150ms(client: TestClient) -> None:
    """Latency budget for the 60-frame chemistry timeline on localhost."""
    # Warmup once to amortize fixture-cache + JSON serialization paths.
    client.get("/api/runs/chemistry/perf/visualization?total=60")
    start = time.perf_counter()
    res = client.get("/api/runs/chemistry/perf/visualization?total=60")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert res.status_code == 200
    assert elapsed_ms < 150.0, f"full-timeline took {elapsed_ms:.1f} ms (>150 ms)"


def test_render_post(client: TestClient) -> None:
    res = client.post("/api/runs/chemistry/chem-test/visualization/render")
    assert res.status_code == 202
    assert res.json()["status"] == "queued"


def test_sse_stream(client: TestClient) -> None:
    with client.stream(
        "GET", "/sse/runs/chemistry/sse-run/visualization?total=5"
    ) as res:
        assert res.status_code == 200
        events: list[dict] = []
        saw_done = False
        current_event: str | None = None
        data_buf: list[str] = []
        for line in res.iter_lines():
            if line == "":
                if data_buf:
                    payload = "\n".join(data_buf)
                    data_buf = []
                    if current_event == "done":
                        saw_done = True
                        break
                    if current_event == "frame":
                        events.append(json.loads(payload))
                current_event = None
                continue
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_buf.append(line.split(":", 1)[1].lstrip())
    assert saw_done
    assert len(events) == 5
    assert all(e["domain"] == "chemistry" for e in events)


def test_ws_stream(client: TestClient) -> None:
    with client.websocket_connect(
        "/ws/runs/chemistry/ws-run/visualization?total=3"
    ) as ws:
        first = ws.receive_bytes()
        if has_msgpack():
            assert first[0] != ord("{")  # msgpack, not JSON
        decoded = decode_frame(first)
        assert decoded.domain == "chemistry"
        # Drain remaining frames.
        ws.receive_bytes()
        ws.receive_bytes()
        # End sentinel.
        sentinel = ws.receive_text()
        assert sentinel == "__done__"


def test_ws_unknown_domain(client: TestClient) -> None:
    from starlette.testclient import WebSocketDenialResponse  # type: ignore[import-not-found]
    from starlette.websockets import WebSocketDisconnect  # type: ignore[import-not-found]

    with pytest.raises((WebSocketDisconnect, WebSocketDenialResponse, Exception)):
        with client.websocket_connect("/ws/runs/phantom/x/visualization"):
            pass
