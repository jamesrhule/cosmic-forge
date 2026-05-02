"""A8 — bearer-token auth + tenancy + budget gate (PROMPT 10 v2 §A).

Pins:
  - Every /api/qcompass/* endpoint rejects unauthenticated requests.
  - Token + X-QCompass-Tenant must agree.
  - Tenant budget gate fires when an estimate would exceed the
    monthly cap.
  - WS /ws/qcompass/.../visualization rejects unauthenticated
    connections (1008 policy violation close).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from ucgle_f1.m8_agent.auth import (
    AuthError,
    AuthStore,
    gate_spend,
    get_auth_store,
    parse_bearer,
    require_auth,
    reset_auth_store,
)
from ucgle_f1.m8_agent.server import build_app


@pytest.fixture(autouse=True)
def _no_dev_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", raising=False)
    reset_auth_store()


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AuthStore:
    monkeypatch.setenv("UCGLE_F1_STATE_DIR", str(tmp_path))
    reset_auth_store()
    return get_auth_store()


@pytest.fixture
def client(store: AuthStore) -> TestClient:
    return TestClient(build_app())


# ── Pure-function helpers ──────────────────────────────────────


@pytest.mark.a_audit
def test_parse_bearer_rejects_missing_header() -> None:
    with pytest.raises(AuthError, match="missing"):
        parse_bearer(None)


@pytest.mark.a_audit
def test_parse_bearer_rejects_malformed_header() -> None:
    with pytest.raises(AuthError, match="Bearer"):
        parse_bearer("Token deadbeef")


@pytest.mark.a_audit
def test_require_auth_rejects_unknown_token(store: AuthStore) -> None:
    with pytest.raises(AuthError, match="Unknown"):
        require_auth(
            store,
            authorization="Bearer qcompass-tok_unknown",
            tenant_header="acme",
        )


@pytest.mark.a_audit
def test_require_auth_enforces_tenant_match(store: AuthStore) -> None:
    tok = store.issue("acme", scopes=["qcompass:read"])
    with pytest.raises(AuthError, match="tenant"):
        require_auth(
            store,
            authorization=f"Bearer {tok.token_id}",
            tenant_header="someone-else",
        )


@pytest.mark.a_audit
def test_gate_spend_fires_above_budget(store: AuthStore) -> None:
    store.upsert_budget("acme", monthly_budget_usd=10.0)
    # Spend $9, then attempt $5 — should fail.
    store.record_spend("acme", 9.0)
    with pytest.raises(AuthError, match="budget"):
        gate_spend(store, "acme", 5.0)


# ── HTTP gates ─────────────────────────────────────────────────


@pytest.mark.a_audit
def test_qcompass_domains_requires_bearer(client: TestClient) -> None:
    resp = client.get("/api/qcompass/domains")
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert detail["code"] == "AUTH_REQUIRED"


@pytest.mark.a_audit
def test_qcompass_domains_rejects_tenant_mismatch(
    client: TestClient, store: AuthStore,
) -> None:
    tok = store.issue("acme", scopes=["qcompass:read"])
    resp = client.get(
        "/api/qcompass/domains",
        headers={
            "Authorization": f"Bearer {tok.token_id}",
            "X-QCompass-Tenant": "evil-corp",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "TENANT_MISMATCH"


@pytest.mark.a_audit
def test_qcompass_domains_accepts_valid_token(
    client: TestClient, store: AuthStore,
) -> None:
    tok = store.issue("acme", scopes=["qcompass:read"])
    resp = client.get(
        "/api/qcompass/domains",
        headers={
            "Authorization": f"Bearer {tok.token_id}",
            "X-QCompass-Tenant": "acme",
        },
    )
    assert resp.status_code == 200
    assert "domains" in resp.json()


@pytest.mark.a_audit
def test_qcompass_run_post_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/qcompass/domains/chemistry/runs",
        json={"manifest": {"problem": {"molecule": "H2"}}},
    )
    assert resp.status_code == 401


@pytest.mark.a_audit
def test_chat_endpoint_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/v1/chat",
        json={
            "conversationId": "c1",
            "messages": [],
            "modelId": "m",
        },
    )
    assert resp.status_code == 401


@pytest.mark.a_audit
def test_legacy_runs_endpoint_unaffected(client: TestClient) -> None:
    """The legacy /api/runs path is intentionally unauthenticated.

    PROMPT 10 v2 §A explicitly scopes auth to /api/qcompass/* and
    /v1/chat. The cosmology workbench keeps its existing path.
    """
    resp = client.get("/api/benchmarks")
    # Either the route returns data (200) or the legacy stub
    # surfaces a typed error — but it must NOT be 401.
    assert resp.status_code != 401


# ── WS gate ────────────────────────────────────────────────────


@pytest.mark.a_audit
def test_ws_visualization_rejects_unauthenticated(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/ws/qcompass/domains/cosmology/runs/foo/visualization",
        ):
            pass
    # 1008 = policy violation; the server uses this for auth fail.
    assert exc.value.code == 1008


@pytest.mark.a_audit
def test_ws_visualization_accepts_valid_token(
    client: TestClient, store: AuthStore,
) -> None:
    tok = store.issue("acme", scopes=["qcompass:read"])
    with client.websocket_connect(
        "/ws/qcompass/domains/cosmology/runs/kawai-kim-natural/visualization",
        headers={
            "Authorization": f"Bearer {tok.token_id}",
            "X-QCompass-Tenant": "acme",
        },
    ) as ws:
        try:
            blob = ws.receive_bytes()
            assert blob, "expected at least one envelope from the WS handler"
        except WebSocketDisconnect:
            pytest.fail("authenticated WS connection was rejected")


# ── PricingEngine budget hook ──────────────────────────────────


@pytest.mark.a_audit
def test_pricing_engine_consults_tenant_budget_hook(
    store: AuthStore, tmp_path: Path,
) -> None:
    pytest.importorskip("qcompass_router")
    from qcompass_router import PricingEngine, set_tenant_budget_hook

    store.upsert_budget("acme", monthly_budget_usd=1.0)
    store.record_spend("acme", 0.95)

    def gate(tenant_id: str | None, amount_usd: float) -> None:
        gate_spend(store, tenant_id, amount_usd)

    set_tenant_budget_hook(gate)
    try:
        engine = PricingEngine(cache_dir=tmp_path / "cache")
        # Braket / IonQ Forte at 4096 shots ≈ $328.30 — paid backend
        # (no free_tier flag), so the budget gate fires.
        with pytest.raises(AuthError, match="budget"):
            engine.estimate(
                "braket", "ionq_forte_1",
                circuit=None, shots=4096, tenant_id="acme",
            )
    finally:
        set_tenant_budget_hook(None)
