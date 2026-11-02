"""HTTP / WS endpoint tests for cosmic_forge_viz.server."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _ensure_fastapi() -> None:
    """Skip the suite when fastapi / starlette aren't importable."""
    pytest.importorskip("fastapi")
    pytest.importorskip("starlette")


def test_get_timeline_returns_downsampled_payload(tmp_path: Path) -> None:
    _ensure_fastapi()
    from fastapi.testclient import TestClient

    from cosmic_forge_viz.baker import bake_synthetic
    from cosmic_forge_viz.server import create_app

    bake_synthetic(
        "cosmology", "kawai-kim-natural",
        out_dir=tmp_path / "cosmology",
        n_frames=120, tau_max=120.0,
        couplings={"alpha_GB": 1.0, "beta_CS": 1.0},
    )
    app = create_app(viz_root=tmp_path)
    client = TestClient(app)
    response = client.get(
        "/api/runs/cosmology/kawai-kim-natural/visualization?max_frames=20",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["domain"] == "cosmology"
    assert body["run_id"] == "kawai-kim-natural"
    assert body["n_frames"] <= 21
    assert body["frames"]


def test_get_timeline_unknown_domain_404(tmp_path: Path) -> None:
    _ensure_fastapi()
    from fastapi.testclient import TestClient
    from cosmic_forge_viz.server import create_app
    app = create_app(viz_root=tmp_path)
    client = TestClient(app)
    response = client.get("/api/runs/gravity/foo/visualization")
    assert response.status_code == 404


def test_post_render_bakes_from_provenance(tmp_path: Path) -> None:
    _ensure_fastapi()
    from fastapi.testclient import TestClient
    from cosmic_forge_viz.server import create_app
    app = create_app(viz_root=tmp_path)
    client = TestClient(app)
    response = client.post(
        "/api/runs/cosmology/starobinsky-standard/visualization/render",
        json={
            "manifest": {
                "problem": {
                    "couplings": {"alpha_GB": 1.0, "beta_CS": 0.5},
                },
            },
        },
    )
    assert response.status_code == 200
    info = response.json()
    assert info["domain"] == "cosmology"
    assert info["n_frames"] >= 1
    snapshot = json.loads(Path(info["json_path"]).read_text())
    assert snapshot["frames"][0]["active_terms"]


def test_websocket_streams_frames_with_envelope(tmp_path: Path) -> None:
    _ensure_fastapi()
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
    from cosmic_forge_viz.baker import bake_synthetic
    from cosmic_forge_viz.protocol import decode
    from cosmic_forge_viz.server import create_app

    bake_synthetic(
        "hep", "schwinger-1plus1d",
        out_dir=tmp_path / "hep", n_frames=4, tau_max=4.0,
    )
    app = create_app(viz_root=tmp_path)
    client = TestClient(app)
    seen_frames = 0
    saw_end = False
    saw_header = False
    with client.websocket_connect(
        "/ws/runs/hep/schwinger-1plus1d/visualization",
    ) as ws:
        try:
            while True:
                blob = ws.receive_bytes()
                msg = decode(blob)
                if msg["type"] == "header":
                    saw_header = True
                    assert msg["payload"]["domain"] == "hep"
                elif msg["type"] == "frame":
                    seen_frames += 1
                elif msg["type"] == "end":
                    saw_end = True
                    break
        except WebSocketDisconnect:
            # Server closed the channel after `end`; that's the
            # documented end-of-stream behaviour.
            pass
    assert saw_header
    assert saw_end
    assert seen_frames == 4


def test_sse_endpoint_streams_data_blocks(tmp_path: Path) -> None:
    _ensure_fastapi()
    from fastapi.testclient import TestClient
    from cosmic_forge_viz.baker import bake_synthetic
    from cosmic_forge_viz.server import create_app

    bake_synthetic(
        "amo", "rydberg-mis",
        out_dir=tmp_path / "amo", n_frames=4, tau_max=4.0,
    )
    app = create_app(viz_root=tmp_path)
    client = TestClient(app)
    with client.stream(
        "GET",
        "/sse/runs/amo/rydberg-mis/visualization",
    ) as response:
        assert response.status_code == 200
        text = "".join(response.iter_text())
    assert "data:" in text
    assert "\"domain\":\"amo\"" in text
