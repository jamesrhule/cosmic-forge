"""P3-06 API hardening: CORS allowlist, health probes, size limits, one
error envelope, typed responses and an OpenAPI lint."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi import HTTPException
from fastapi.testclient import TestClient

from ucgle_f1.domain import ServiceError
from ucgle_f1.m8_agent import health
from ucgle_f1.m8_agent.server import build_app


@pytest.fixture
def isolated(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    monkeypatch.setenv("UCGLE_F1_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("QCOMPASS_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("QCOMPASS_ENV", raising=False)
    monkeypatch.delenv("QCOMPASS_MAX_BODY_BYTES", raising=False)
    monkeypatch.delenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", raising=False)
    from ucgle_f1.m8_agent.auth import reset_auth_store
    from ucgle_f1.m8_agent.scans import reset_scan_registry

    reset_auth_store()
    reset_scan_registry()


def _key_headers() -> dict[str, str]:
    """A real tenant API key (P3-04: protected routes need a principal)."""
    from ucgle_f1.m8_agent.auth import get_auth_store

    tok = get_auth_store().issue("acme", scopes=["read", "run"])
    return {"Authorization": f"Bearer {tok.token_id}", "X-QCompass-Tenant": "acme"}


class _AuthedClient(TestClient):
    def request(self, method, url, **kw):  # type: ignore[override]
        headers = {**_key_headers(), **(kw.pop("headers", None) or {})}
        return super().request(method, url, headers=headers, **kw)


def _client() -> TestClient:
    return _AuthedClient(build_app(), raise_server_exceptions=False)


def _assert_envelope(body: dict[str, Any], code: str) -> None:
    assert set(body) == {"detail"}, body
    assert body["detail"]["code"] == code
    assert isinstance(body["detail"]["message"], str)


# ── CORS ────────────────────────────────────────────────────────


def _preflight(client: TestClient, origin: str) -> str | None:
    resp = client.options(
        "/api/benchmarks",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    return resp.headers.get("access-control-allow-origin")


def test_cors_closed_by_default_in_production(isolated: None) -> None:
    client = _client()
    assert _preflight(client, "https://evil.example") is None
    assert _preflight(client, "http://localhost:8080") is None


def test_cors_allowlist_from_env(isolated: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QCOMPASS_CORS_ORIGINS", "https://app.example, https://staging.example/")
    client = _client()
    assert _preflight(client, "https://app.example") == "https://app.example"
    assert _preflight(client, "https://staging.example") == "https://staging.example"
    assert _preflight(client, "https://evil.example") is None


def test_cors_wildcard_only_in_dev(isolated: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QCOMPASS_CORS_ORIGINS", "*")
    assert _preflight(_client(), "https://evil.example") is None
    monkeypatch.setenv("QCOMPASS_ENV", "dev")
    assert _preflight(_client(), "https://evil.example") is not None


def test_cors_dev_defaults_to_local_origins(isolated: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QCOMPASS_ENV", "dev")
    client = _client()
    assert _preflight(client, "http://localhost:8080") == "http://localhost:8080"
    assert _preflight(client, "https://evil.example") is None


# ── Health ──────────────────────────────────────────────────────


def test_healthz(isolated: None) -> None:
    resp = _client().get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readyz_ready(isolated: None) -> None:
    resp = _client().get("/readyz")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready"
    assert set(body["checks"]) == {"database", "storage", "queue"}
    assert all(c["ok"] for c in body["checks"].values())


def test_readyz_not_ready_when_a_dependency_fails(
    isolated: None, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    def broken() -> None:
        raise ConnectionError("db down at db.internal:5432 for user postgres")

    monkeypatch.setitem(health.CHECKS, "database", broken)
    with caplog.at_level("WARNING", logger="ucgle_f1.m8_agent.health"):
        resp = _client().get("/readyz")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"]["ok"] is False
    # SEC-L1: the public body names the failing check only; the exception
    # text (host, user) goes to the log.
    assert body["checks"]["database"]["detail"] == "unavailable"
    assert "db down" not in resp.text and "db.internal" not in resp.text and "postgres" not in resp.text
    assert "db down at db.internal" in caplog.text
    assert body["checks"]["storage"]["ok"] is True


# ── Size limits ─────────────────────────────────────────────────


def test_body_over_limit_is_413_with_envelope(isolated: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QCOMPASS_MAX_BODY_BYTES", "64")
    resp = _client().post("/api/scans", json={"domain": "hep", "kind": "x", "payload": {"pad": "y" * 200}})
    assert resp.status_code == 413
    _assert_envelope(resp.json(), "PAYLOAD_TOO_LARGE")


def test_chunked_body_over_limit_is_413(isolated: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QCOMPASS_MAX_BODY_BYTES", "64")

    def chunks():  # no Content-Length: the middleware must count bytes
        for _ in range(10):
            yield b'{"domain": "hep", "kind": "x"}'

    resp = _client().post("/api/scans", content=chunks(), headers={"Content-Type": "application/json"})
    assert resp.status_code == 413
    _assert_envelope(resp.json(), "PAYLOAD_TOO_LARGE")


def test_body_under_limit_passes(isolated: None) -> None:
    resp = _client().post("/api/scans", json={"domain": "hep", "kind": "grid"})
    assert resp.status_code == 201, resp.text


# ── One error envelope ──────────────────────────────────────────


def test_unknown_route_uses_envelope(isolated: None) -> None:
    resp = _client().get("/api/does-not-exist")
    assert resp.status_code == 404
    _assert_envelope(resp.json(), "NOT_FOUND")


def test_validation_error_uses_envelope(isolated: None) -> None:
    resp = _client().post("/api/approvals", json={"scopes": "not-a-list"})
    assert resp.status_code == 422
    body = resp.json()
    _assert_envelope(body, "INVALID_INPUT")
    assert body["detail"]["errors"], "field-level errors are reported"


def test_string_http_exception_uses_envelope(isolated: None) -> None:
    resp = _client().get("/api/scans/no-such-scan")
    assert resp.status_code == 404
    _assert_envelope(resp.json(), "NOT_FOUND")


def test_service_error_and_unexpected_error_use_envelope(isolated: None) -> None:
    app = build_app()

    @app.get("/_test/service-error")
    def _se() -> dict:
        raise ServiceError("APPROVAL_REQUIRED", "needs approval")

    @app.get("/_test/boom")
    def _boom() -> dict:
        raise RuntimeError("secret internal detail")

    @app.get("/_test/http-dict")
    def _hd() -> dict:
        raise HTTPException(409, detail={"code": "AUDIT_VIOLATION", "message": "nope"})

    client = TestClient(app, raise_server_exceptions=False)
    r1 = client.get("/_test/service-error")
    assert r1.status_code == 403
    _assert_envelope(r1.json(), "APPROVAL_REQUIRED")
    r2 = client.get("/_test/boom")
    assert r2.status_code == 500
    _assert_envelope(r2.json(), "INTERNAL")
    assert "secret internal detail" not in r2.text
    r3 = client.get("/_test/http-dict")
    assert r3.status_code == 409
    _assert_envelope(r3.json(), "AUDIT_VIOLATION")


# ── OpenAPI lint: complete and typed ────────────────────────────


def _resolve(spec: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        schema = spec["components"]["schemas"][name]
    return schema


def _is_typed(spec: dict[str, Any], schema: dict[str, Any]) -> bool:
    if not schema:
        return False
    s = _resolve(spec, schema)
    if s.get("type") == "array":
        return _is_typed(spec, s.get("items", {}))
    if "oneOf" in s or "anyOf" in s:
        return all(_is_typed(spec, x) for x in s.get("oneOf", s.get("anyOf", [])))
    if "discriminator" in s:
        return True
    return bool(s.get("properties")) or s.get("type") in {"object", "string"} and (
        "properties" in s or "additionalProperties" in s or s.get("type") == "string"
    )


def test_openapi_document_is_valid_and_every_route_is_typed(isolated: None) -> None:
    from openapi_spec_validator import validate

    spec = build_app().openapi()
    validate(spec)  # raises on an invalid OpenAPI document

    untyped: list[str] = []
    no_errors: list[str] = []
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            responses = op.get("responses", {})
            ok = [c for c in responses if str(c).startswith("2")]
            if not ok:
                untyped.append(f"{method.upper()} {path}: no 2xx response")
                continue
            for code in ok:
                content = responses[code].get("content", {})
                if "text/event-stream" in content or "text/plain" in content:
                    continue
                schema = content.get("application/json", {}).get("schema", {})
                if not _is_typed(spec, schema):
                    untyped.append(f"{method.upper()} {path} {code}: untyped body {schema}")
            if not {"4XX", "5XX"} <= set(responses):
                no_errors.append(f"{method.upper()} {path}")
    assert not untyped, "routes without a typed response:\n" + "\n".join(untyped)
    assert not no_errors, "routes not documenting the error envelope:\n" + "\n".join(no_errors)
    assert spec["components"]["schemas"]["ErrorEnvelope"]["properties"]["detail"]
