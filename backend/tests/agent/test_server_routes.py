"""Smoke-tests for the FastAPI + MCP server routes.

We drive the app with ``fastapi.testclient.TestClient`` so the tests
never open a real socket. Provider streaming is covered separately
with a stub ChatProvider.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ucgle_f1.m8_agent.server import build_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(build_app())


def test_mcp_tools_listing(client: TestClient) -> None:
    resp = client.get("/mcp/tools")
    assert resp.status_code == 200
    tools = resp.json()
    names = {t["name"] for t in tools}
    for required in {
        "list_benchmarks", "start_run", "stream_run",
        "propose_patch", "dry_run_patch",
        "list_tools", "describe_tool", "get_capabilities",
    }:
        assert required in names


def test_get_capabilities(client: TestClient) -> None:
    resp = client.post("/mcp/tools/get_capabilities", json={})
    assert resp.status_code == 200
    body = resp.json()["output"]
    assert body["schemaVersion"] == "1"
    assert "start_run" in body["approvalScopesRequired"]


def test_validate_config(client: TestClient) -> None:
    payload = {
        "config": {
            "potential": {"kind": "natural", "params": {"f_a": 1.0, "Lambda": 0.001}},
            "couplings": {"xi": 1e-3, "theta_grav": 1e-3, "f_a": 1e17,
                          "M_star": 1e18, "M1": 1e12, "S_E2": 1.0},
            "reheating": {"Gamma_phi": 1e-6, "T_reh_GeV": 1e13},
            "precision": "standard",
            "agent": {"conversationId": "c", "hypothesisId": "h"},
        },
    }
    resp = client.post("/mcp/tools/validate_config", json=payload)
    assert resp.status_code == 200
    diags = resp.json()["output"]
    assert diags["valid"] is True


def test_approval_issue(client: TestClient) -> None:
    resp = client.post("/api/approvals", json={"scopes": ["start_run"], "ttl_seconds": 60})
    assert resp.status_code == 200
    assert resp.json()["tokenId"].startswith("appr_")
