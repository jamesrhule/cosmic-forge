"""Verdict endpoints are admin-only via a verified Supabase session (correction 9).

Signing keys are generated locally and served through a fake JWKS fetcher;
roles come from a fake PostgREST fetcher. No network (R8).
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("qcompass_core")

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from ucgle_f1.m8_agent import supabase_auth
from ucgle_f1.m8_agent.server import build_app

SUPA = "https://proj.supabase.test"
KID = "test-key-1"


@pytest.fixture
def keys() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def client(
    keys: ec.EllipticCurvePrivateKey, monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> Iterator[TestClient]:
    monkeypatch.setenv("SUPABASE_URL", SUPA)
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "publishable-test-key")
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path))
    public_jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(keys.public_key()))
    public_jwk.update({"kid": KID, "alg": "ES256", "use": "sig"})
    seen_urls: list[str] = []

    def fake_jwks(url: str) -> dict:
        seen_urls.append(url)
        return {"keys": [public_jwk]}

    roles = {"admin-user": ["admin"], "plain-user": []}

    def fake_roles(base: str, apikey: str, token: str, user_id: str) -> list[str]:
        assert base == SUPA and apikey == "publishable-test-key" and token
        return roles.get(user_id, [])

    supabase_auth.set_jwks_fetcher(fake_jwks)
    supabase_auth.set_roles_fetcher(fake_roles)
    try:
        yield TestClient(build_app(), raise_server_exceptions=False)
    finally:
        supabase_auth.set_jwks_fetcher(None)
        supabase_auth.set_roles_fetcher(None)
    assert all(u == f"{SUPA}/auth/v1/.well-known/jwks.json" for u in seen_urls)


def _token(key, sub: str, *, exp_in: int = 600, iss: str = f"{SUPA}/auth/v1",
           aud: str = "authenticated", kid: str = KID) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": sub, "aud": aud, "iss": iss, "iat": now, "exp": now + exp_in, "role": "authenticated"},
        key, algorithm="ES256", headers={"kid": kid},
    )


def _auth(tok: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}"}


def test_admin_reads_verdict_by_id_and_latest(client: TestClient, keys) -> None:
    tok = _token(keys, "admin-user")
    r = client.get("/api/verdict/sample", headers=_auth(tok))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rows"] and body["reviewer"]
    latest = client.get("/api/qcompass/verdict", headers=_auth(tok))
    assert latest.status_code == 200
    assert latest.json() == body


def test_signed_out_is_401(client: TestClient) -> None:
    r = client.get("/api/verdict/sample")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_non_admin_is_403(client: TestClient, keys) -> None:
    r = client.get("/api/verdict/sample", headers=_auth(_token(keys, "plain-user")))
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize("variant", ["wrong-key", "expired", "wrong-aud", "wrong-iss", "unknown-kid"])
def test_bad_tokens_are_rejected(client: TestClient, keys, variant: str) -> None:
    if variant == "wrong-key":
        tok = _token(ec.generate_private_key(ec.SECP256R1()), "admin-user")
    elif variant == "expired":
        tok = _token(keys, "admin-user", exp_in=-60)
    elif variant == "wrong-aud":
        tok = _token(keys, "admin-user", aud="anon")
    elif variant == "wrong-iss":
        tok = _token(keys, "admin-user", iss="https://evil.test/auth/v1")
    else:
        tok = _token(keys, "admin-user", kid="other")
    r = client.get("/api/verdict/sample", headers=_auth(tok))
    assert r.status_code == 401, (variant, r.text)


def test_symmetric_and_none_algorithms_are_refused(client: TestClient) -> None:
    now = int(time.time())
    claims = {"sub": "admin-user", "aud": "authenticated", "iss": f"{SUPA}/auth/v1", "exp": now + 600}
    hs = jwt.encode(claims, "shared-secret-that-is-long-enough-for-hs256", algorithm="HS256", headers={"kid": KID})
    assert client.get("/api/verdict/sample", headers=_auth(hs)).status_code == 401
    none = jwt.encode(claims, None, algorithm="none")
    assert client.get("/api/verdict/sample", headers=_auth(none)).status_code == 401


def test_missing_supabase_config_is_blocked_on_james_not_a_crash(
    client: TestClient, keys, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUPABASE_URL")
    r = client.get("/api/verdict/sample", headers=_auth(_token(keys, "admin-user")))
    assert r.status_code == 503
    assert r.json()["detail"]["message"] == "BLOCKED-ON-JAMES:SUPABASE_URL"


def test_unsafe_and_unknown_verdict_ids(client: TestClient, keys) -> None:
    tok = _token(keys, "admin-user")
    assert client.get("/api/verdict/..hidden", headers=_auth(tok)).status_code == 400
    assert client.get("/api/verdict/nope", headers=_auth(tok)).status_code == 404
