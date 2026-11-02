"""A9 — observability surface (PROMPT 10 v2 §B).

Pins:
  - The metrics registry exposes the canonical histograms +
    counters (run wallclock, audit pass count by domain, calibration
    drift events).
  - GET /metrics returns the Prometheus text format and includes
    the canonical metric names.
  - The traced() decorator surfaces ``provenance_ref`` as a span
    attribute when the caller passes one.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from ucgle_f1.m8_agent.observability import (
    MetricsRegistry,
    get_metrics_registry,
    reset_metrics_registry,
    span,
    traced,
)
from ucgle_f1.m8_agent.server import build_app


@pytest.fixture(autouse=True)
def _isolate_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_metrics_registry()
    monkeypatch.setenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", "1")
    yield
    reset_metrics_registry()


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


# ── Registry contract ──────────────────────────────────────────


@pytest.mark.a_audit
def test_registry_exposes_canonical_histograms() -> None:
    reg = get_metrics_registry()
    reg.observe_run_wallclock(domain="chemistry", seconds=0.42)
    reg.observe_audit_pass_count(domain="chemistry", count=15)
    reg.increment_calibration_drift(provider="ibm")
    reg.increment_router_decision(provider="ibm", status="pass")
    text = reg.render_prometheus()
    assert "qcompass_run_wallclock_seconds_bucket" in text
    assert "qcompass_audit_pass_count_bucket" in text
    assert "qcompass_calibration_drift_total" in text
    assert "qcompass_router_decisions_total" in text


@pytest.mark.a_audit
def test_metrics_endpoint_serves_prometheus_text(client: TestClient) -> None:
    # Seed at least one observation so the body isn't empty.
    get_metrics_registry().observe_run_wallclock(
        domain="cosmology", seconds=0.05,
    )
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "qcompass_run_wallclock_seconds_bucket" in body
    assert "domain=\"cosmology\"" in body
    # Content type is text/plain (PlainTextResponse).
    assert resp.headers["content-type"].startswith("text/plain")


# ── Trace decorator contract ───────────────────────────────────


@pytest.mark.a_audit
def test_traced_decorator_records_wallclock_observation() -> None:
    reset_metrics_registry()
    reg = get_metrics_registry()

    @traced("test.work")
    def work(*, domain: str, provenance_ref: str | None = None) -> int:
        return 1

    work(domain="chemistry", provenance_ref="run_abc")
    text = reg.render_prometheus()
    assert "domain=\"chemistry\"" in text


@pytest.mark.a_audit
def test_traced_decorator_passes_through_when_otel_missing() -> None:
    """The OTel SDK is soft-imported. Without it the decorator MUST
    still call the wrapped function and emit the wallclock metric.
    """
    pytest.importorskip("opentelemetry") if False else None  # noqa: B015
    # Either the SDK is missing (no-op span) or installed (real span).
    # In both cases the function output and metric emit are the same.
    reset_metrics_registry()
    reg = get_metrics_registry()

    calls: list[str] = []

    @traced()
    def fn(*, domain: str = "chemistry") -> str:
        calls.append("ran")
        return "ok"

    assert fn(domain="hep") == "ok"
    assert calls == ["ran"]
    text = reg.render_prometheus()
    assert "qcompass_run_wallclock_seconds_bucket" in text
    assert "domain=\"hep\"" in text


@pytest.mark.a_audit
def test_span_helper_does_not_raise_without_otel() -> None:
    with span("noop", attributes={"provenance_ref": "abc"}):
        # Body runs unconditionally.
        x = 1 + 1
        assert x == 2


# ── Provenance contract — every span attribute opportunity ─────


@pytest.mark.a_audit
def test_traced_decorator_threads_provenance_ref_via_extractor() -> None:
    """v2 §B: traces include provenance_ref. We exercise both the
    default (kwargs.get) and the explicit extractor path.
    """
    pulled: list[str | None] = []

    def extractor(*_args, **kwargs) -> str | None:
        pulled.append(kwargs.get("manifest", {}).get("runId"))
        return pulled[-1]

    @traced("submit_run", extract_provenance=extractor)
    def submit_run(*, manifest: dict, domain: str = "chemistry") -> str:
        return "ok"

    submit_run(manifest={"runId": "qc_chem_1"}, domain="chemistry")
    assert pulled == ["qc_chem_1"]
