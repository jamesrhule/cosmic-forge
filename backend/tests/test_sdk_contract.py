"""P4-02: the TypeScript SDK's generated types and the live workbench path.

- ``packages/ts/qcompass-frontend-sdk/openapi.json`` is exactly what
  ``scripts/dump_openapi.py`` writes for this backend (CI's
  ``scripts/gen_sdk_types.sh --check`` also checks the generated ``.ts``).
- Short domain names resolve to their plugins, so the workbench's cosmology
  run (``POST /api/qcompass/domains/cosmology.ucglef1/runs``) runs in the
  worker (``cosmology.ucglef1`` is the plugin's registered name) and the
  schema route serves the cosmology manifest schema.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("qcompass_core")

REPO = Path(__file__).resolve().parents[2]
SDK_OPENAPI = REPO / "packages" / "ts" / "qcompass-frontend-sdk" / "openapi.json"


def test_committed_openapi_matches_the_app() -> None:
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "dump_openapi.py")],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO,
    ).stdout
    assert out == SDK_OPENAPI.read_text(encoding="utf-8"), (
        "SDK OpenAPI is stale: run scripts/gen_sdk_types.sh"
    )


def test_dump_is_deterministic() -> None:
    runs = [
        subprocess.run(
            [sys.executable, str(REPO / "scripts" / "dump_openapi.py")],
            capture_output=True,
            text=True,
            check=True,
            cwd=REPO,
            env={"PATH": "/usr/bin:/bin", "QCOMPASS_ENV": env, "QCOMPASS_DEV_ALLOW_ANONYMOUS": "1"},
        ).stdout
        for env in ("dev", "production")
    ]
    assert runs[0] == runs[1]


def test_short_domain_names_resolve_to_their_plugins() -> None:
    from ucgle_f1.adapters.qcompass import LeptogenesisSimulation
    from ucgle_f1.worker import resolve_simulation

    assert resolve_simulation("cosmology") is LeptogenesisSimulation
    assert resolve_simulation("cosmology.ucglef1") is LeptogenesisSimulation
    assert resolve_simulation("chemistry").__name__  # registered under its short name
    with pytest.raises(Exception):  # noqa: B017 - the registry's own error type
        resolve_simulation("no-such-domain")


def test_cosmology_schema_route_serves_the_manifest_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from ucgle_f1.m8_agent.server import build_app

    monkeypatch.setenv("QCOMPASS_ENV", "dev")
    monkeypatch.setenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", "1")
    resp = TestClient(build_app()).get("/api/qcompass/domains/cosmology.ucglef1/schema")
    assert resp.status_code == 200
    schema = resp.json()
    assert set(schema["required"]) >= {"potential", "couplings", "reheating"}
    assert schema["properties"]["precision"]["enum"] == ["fast", "standard", "high"]
