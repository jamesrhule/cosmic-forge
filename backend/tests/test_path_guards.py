"""Path-injection guards (CodeQL py/path-injection on PR #3).

Request-supplied run and domain ids must never reach the filesystem
outside their artifacts root.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ucgle_f1._paths import UnsafePathError, safe_component, safe_join


@pytest.mark.parametrize("value", ["h2-sto3g", "kawai-kim-natural", "qc_chemistry_0a1b2c", "cosmology.ucglef1", "F3"])
def test_safe_component_accepts_real_ids(value: str) -> None:
    assert safe_component(value) == value


@pytest.mark.parametrize(
    "value",
    ["", "..", "../etc", "a/b", "a\\b", "/abs", ".hidden", "a..b", "x" * 129, "sp ace", "nul\x00"],
)
def test_safe_component_rejects_traversal_and_junk(value: str) -> None:
    with pytest.raises(UnsafePathError):
        safe_component(value)


def test_safe_join_stays_inside_root(tmp_path: Path) -> None:
    assert safe_join(tmp_path, "chemistry", "r1.json") == Path(os.path.realpath(tmp_path)) / "chemistry" / "r1.json"
    with pytest.raises(UnsafePathError):
        safe_join(tmp_path, "..", "escape.json")
    with pytest.raises(UnsafePathError):
        safe_join(tmp_path, "/etc/passwd")


def test_safe_join_refuses_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(UnsafePathError):
        safe_join(root, "link", "x.json")


# ── HTTP surfaces ───────────────────────────────────────────────────

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def qcompass_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", "1")
    monkeypatch.setenv("QCOMPASS_ENV", "dev")  # P3-04: the flag only works in dev
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    from ucgle_f1.m8_agent.server import build_app

    return TestClient(build_app())


def test_submit_run_rejects_traversal_run_id(qcompass_client: TestClient, tmp_path: Path) -> None:
    resp = qcompass_client.post(
        "/api/qcompass/domains/chemistry/runs",
        json={"runId": "../../../escape", "manifest": {}},
    )
    assert resp.status_code == 400
    assert not list(tmp_path.rglob("escape*"))


@pytest.mark.parametrize("run_id", [".hidden", "a..b", "sp ace"])
def test_get_run_and_viz_reject_unsafe_run_id(qcompass_client: TestClient, run_id: str) -> None:
    assert qcompass_client.get(f"/api/qcompass/domains/chemistry/runs/{run_id}").status_code == 400
    assert qcompass_client.get(f"/api/qcompass/domains/chemistry/runs/{run_id}/stream").status_code == 400
    viz = qcompass_client.get(f"/api/qcompass/domains/chemistry/runs/{run_id}/visualization")
    assert viz.status_code in {400, 503}  # 503 only when cosmic_forge_viz is not installed


def test_viz_server_rejects_unsafe_run_id(tmp_path: Path) -> None:
    pytest.importorskip("cosmic_forge_viz")
    from cosmic_forge_viz.server import create_app

    client = TestClient(create_app(viz_root=tmp_path))
    assert client.get("/api/runs/chemistry/a..b/visualization").status_code == 400
    assert client.get("/api/runs/chemistry/.hidden/manifest").status_code == 400
    assert client.post("/api/runs/chemistry/sp%20ace/visualization/render").status_code == 400
    assert client.get("/api/runs/chemistry/h2-sto3g/visualization").status_code == 200


def test_bake_synthetic_rejects_unsafe_ids(tmp_path: Path) -> None:
    baker = pytest.importorskip("cosmic_forge_viz.baker")
    with pytest.raises(UnsafePathError):
        baker.bake_synthetic("chemistry", "../escape", out_dir=tmp_path)
    with pytest.raises(UnsafePathError):
        baker.bake_synthetic("../chemistry", "r1", out_dir=tmp_path)
