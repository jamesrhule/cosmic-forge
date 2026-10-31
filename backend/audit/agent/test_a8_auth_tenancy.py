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


# ── P3-04: hashed keys, scopes, dev gating, Supabase members, isolation ──


def _hdr(tok_id: str, tenant: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok_id}", "X-QCompass-Tenant": tenant}


@pytest.mark.a_audit
def test_api_keys_are_stored_only_as_hashes(store: AuthStore, tmp_path: Path) -> None:
    import sqlite3

    tok = store.issue("acme", scopes=["read"])
    db = sqlite3.connect(str(tmp_path / "auth.db"))
    dump = "\n".join(db.iterdump())
    assert tok.token_id not in dump, "plaintext API key persisted"
    assert store.lookup(tok.token_id) is not None


@pytest.mark.a_audit
def test_revoked_key_is_rejected(client: TestClient, store: AuthStore) -> None:
    tok = store.issue("acme", scopes=["read"])
    assert client.get("/api/qcompass/domains", headers=_hdr(tok.token_id, "acme")).status_code == 200
    assert store.revoke(tok.token_id)
    resp = client.get("/api/qcompass/domains", headers=_hdr(tok.token_id, "acme"))
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "AUTH_INVALID"


@pytest.mark.a_audit
def test_scopes_are_enforced(client: TestClient, store: AuthStore) -> None:
    viewer = store.issue("acme", scopes=["read"])
    resp = client.post(
        "/api/qcompass/domains/cosmology/runs",
        json={"manifest": {"problem": {}}},
        headers=_hdr(viewer.token_id, "acme"),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"
    member = store.issue("acme", scopes=["read", "run"])
    ok = client.post(
        "/api/qcompass/domains/cosmology/runs",
        json={"manifest": {"problem": {}}},
        headers=_hdr(member.token_id, "acme"),
    )
    assert ok.status_code in {200, 202}
    # admin-only routes refuse a member
    assert client.delete("/api/models/x", headers=_hdr(member.token_id, "acme")).status_code == 403


@pytest.mark.a_audit
def test_dev_anonymous_flag_is_ignored_outside_dev(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", "1")
    monkeypatch.delenv("QCOMPASS_ENV", raising=False)  # defaults to production
    assert client.get("/api/qcompass/domains").status_code == 401
    monkeypatch.setenv("QCOMPASS_ENV", "staging")
    assert client.get("/api/qcompass/domains").status_code == 401
    monkeypatch.setenv("QCOMPASS_ENV", "dev")
    assert client.get("/api/qcompass/domains").status_code == 200


@pytest.mark.a_audit
def test_cross_tenant_runs_and_scans_are_404(
    client: TestClient, store: AuthStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ucgle_f1.m8_agent.scans import reset_scan_registry

    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    reset_scan_registry()
    a = store.issue("acme", scopes=["read", "run"])
    b = store.issue("globex", scopes=["read", "run"])
    run = client.post(
        "/api/qcompass/domains/cosmology/runs",
        json={"manifest": {"problem": {}}},
        headers=_hdr(a.token_id, "acme"),
    ).json()["runId"]
    scan = client.post(
        "/api/qcompass/scans", json={"domain": "hep", "kind": "grid"}, headers=_hdr(a.token_id, "acme"),
    ).json()["scanId"]

    # Owner sees both.
    assert client.get(f"/api/qcompass/domains/cosmology/runs/{run}", headers=_hdr(a.token_id, "acme")).status_code == 200
    assert client.get(f"/api/qcompass/scans/{scan}", headers=_hdr(a.token_id, "acme")).status_code == 200

    # Another tenant gets 404 — never 403, never the data.
    for path in (f"/api/qcompass/domains/cosmology/runs/{run}", f"/api/qcompass/scans/{scan}"):
        resp = client.get(path, headers=_hdr(b.token_id, "globex"))
        assert resp.status_code == 404, path
        assert resp.json()["detail"]["code"] == "NOT_FOUND"
    assert client.delete(f"/api/qcompass/scans/{scan}", headers=_hdr(b.token_id, "globex")).status_code == 404
    runs_b = client.get("/api/qcompass/domains/cosmology/runs", headers=_hdr(b.token_id, "globex")).json()
    assert run not in {r["id"] for r in runs_b}
    scans_b = client.get("/api/qcompass/scans", headers=_hdr(b.token_id, "globex")).json()["scans"]
    assert scan not in {s["scanId"] for s in scans_b}
    # A key can't be pointed at another tenant via the header.
    assert client.get("/api/qcompass/domains", headers=_hdr(a.token_id, "globex")).status_code == 403


@pytest.fixture
def supabase_keys(monkeypatch: pytest.MonkeyPatch):
    import json as _json

    import jwt
    from cryptography.hazmat.primitives.asymmetric import ec

    from ucgle_f1.m8_agent import supabase_auth

    key = ec.generate_private_key(ec.SECP256R1())
    jwk = _json.loads(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key()))
    jwk.update({"kid": "k1", "alg": "ES256"})
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.test")
    supabase_auth.set_jwks_fetcher(lambda _url: {"keys": [jwk]})
    yield key
    supabase_auth.set_jwks_fetcher(None)


def _supabase_token(key, sub: str) -> str:
    import time

    import jwt

    now = int(time.time())
    return jwt.encode(
        {"sub": sub, "aud": "authenticated", "iss": "https://proj.supabase.test/auth/v1",
         "iat": now, "exp": now + 600},
        key, algorithm="ES256", headers={"kid": "k1"},
    )


@pytest.mark.a_audit
def test_supabase_users_resolve_tenants_through_membership(
    client: TestClient, store: AuthStore, supabase_keys,
) -> None:
    store.add_member("acme", "user-1", "viewer")
    tok = _supabase_token(supabase_keys, "user-1")
    # Member with read: ok.
    assert client.get("/api/qcompass/domains", headers=_hdr(tok, "acme")).status_code == 200
    # Viewer can't run.
    resp = client.post(
        "/api/qcompass/domains/cosmology/runs", json={"manifest": {"problem": {}}}, headers=_hdr(tok, "acme"),
    )
    assert resp.status_code == 403
    # Not a member of the requested tenant: 404, not 403 (no existence leak).
    resp = client.get("/api/qcompass/domains", headers=_hdr(tok, "globex"))
    assert resp.status_code == 404
    # Tenant header required for a user session.
    resp = client.get("/api/qcompass/domains", headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "TENANT_REQUIRED"
    # Tenants lists the user's memberships.
    store.add_member("initech", "user-1", "admin")
    tenants = client.get("/api/qcompass/tenants", headers=_hdr(tok, "acme")).json()
    assert tenants == [
        {"id": "acme", "label": "acme", "role": "viewer"},
        {"id": "initech", "label": "initech", "role": "admin"},
    ]


@pytest.mark.a_audit
def test_ws_rejects_supabase_non_member(client: TestClient, store: AuthStore, supabase_keys) -> None:
    tok = _supabase_token(supabase_keys, "user-2")
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/ws/qcompass/domains/cosmology/runs/foo/visualization", headers=_hdr(tok, "acme"),
        ):
            pass
    assert exc.value.code == 1008
