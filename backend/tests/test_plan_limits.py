"""P3-05: plan limits at enqueue and QPU budgets in the router, at and over
each boundary, with machine-readable codes."""

from __future__ import annotations

import os
import re
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from ucgle_f1.jobs import JobQueue
from ucgle_f1.m8_agent.api_errors import status_for
from ucgle_f1.m8_agent.auth import AuthError, get_auth_store, install_budget_hook
from ucgle_f1.m8_agent.server import build_app
from ucgle_f1.plans import PLAN_LIMITS, PlanLimitExceeded, check_timeline_bytes

BILLING_TS = Path(__file__).resolve().parents[2] / "src" / "lib" / "billing.ts"


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("BLOCKED-ON-JAMES:DATABASE_URL (no test Postgres)")
    return url.replace("postgresql+psycopg://", "postgresql://")


def _tenant(tier: str) -> str:
    uuid = get_auth_store().ensure_tenant("acme")
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute("update public.tenants set subscription_tier = %s where id = %s", (tier, uuid))
    return uuid


def _enqueue(q: JobQueue, tenant: str, n: int, *, cls: str = "cpu", kind: str = "qcompass.run",
             payload: dict | None = None) -> None:
    q.enqueue_run(
        run_id=f"run_limit_{n}", tenant_uuid=tenant, kind=kind, payload=payload or {},
        label="limit", config={"domain": "chemistry", "kind": kind}, compute_class=cls,
    )


def _finish_all_jobs() -> None:
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute("update public.jobs set status = 'succeeded', finished_at = now()")


def test_backend_plan_limits_match_the_pricing_page() -> None:
    ts = BILLING_TS.read_text(encoding="utf-8")
    for tier, lim in PLAN_LIMITS.items():
        block = re.search(tier + r": \{(.*?)\}", ts, re.DOTALL)
        assert block, tier
        body = block.group(1)

        def num(key: str, body: str = body) -> float:
            raw = re.search(key + r": ([^,]+),", body).group(1).strip()  # type: ignore[union-attr]
            if raw == "Number.POSITIVE_INFINITY":
                return float("inf")
            return float(eval(raw.replace("_", ""), {"__builtins__": {}}))  # noqa: S307 - digits and *

        assert num("maxRunsPerMonth") == lim.maxRunsPerMonth, tier
        assert num("maxConcurrentJobs") == lim.maxConcurrentJobs, tier
        assert num("maxTimelineBytes") == lim.maxTimelineBytes, tier
        assert re.search(r"gpuAccess: (true|false)", body).group(1) == str(lim.gpuAccess).lower()  # type: ignore[union-attr]


def test_concurrent_jobs_at_and_over_the_boundary() -> None:
    q = JobQueue()
    tenant = _tenant("pro")  # 4 concurrent
    for i in range(4):
        _enqueue(q, tenant, i)  # 0..3 active before each → allowed (the 4th reaches the limit)
    with pytest.raises(PlanLimitExceeded) as exc:
        _enqueue(q, tenant, 4)
    assert exc.value.code == "PLAN_CONCURRENT_JOBS_EXCEEDED"
    assert (exc.value.limit, exc.value.used) == (4, 4)
    assert status_for(exc.value.code) == 429
    _finish_all_jobs()
    _enqueue(q, tenant, 5)  # finished jobs free the slots


def test_runs_per_month_at_and_over_the_boundary() -> None:
    q = JobQueue()
    tenant = _tenant("free")  # 25 runs / month, 1 concurrent
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute(
            "insert into public.runs (id, tenant_id, config, created_at) "
            "select 'run_old_' || g, %s, '{}', date_trunc('month', now()) - interval '1 day' "
            "from generate_series(1, 30) g", (tenant,),
        )  # last month's runs don't count
        conn.execute(
            "insert into public.runs (id, tenant_id, config) "
            "select 'run_now_' || g, %s, '{}' from generate_series(1, 24) g", (tenant,),
        )
    _enqueue(q, tenant, 25)  # the 25th run this month: allowed
    _finish_all_jobs()
    with pytest.raises(PlanLimitExceeded) as exc:
        _enqueue(q, tenant, 26)
    assert exc.value.code == "PLAN_RUNS_PER_MONTH_EXCEEDED"
    assert (exc.value.limit, exc.value.used) == (25, 25)
    assert status_for(exc.value.code) == 429


def test_gpu_access_by_tier() -> None:
    q = JobQueue()
    tenant = _tenant("free")
    with pytest.raises(PlanLimitExceeded) as exc:
        _enqueue(q, tenant, 1, cls="gpu_small")
    assert exc.value.code == "PLAN_GPU_REQUIRED"
    assert status_for(exc.value.code) == 402
    _tenant("pro")
    _enqueue(q, tenant, 2, cls="gpu_small")


def test_timeline_bytes_at_and_over_the_boundary() -> None:
    limit = PLAN_LIMITS["free"].maxTimelineBytes
    check_timeline_bytes("free", limit)
    with pytest.raises(PlanLimitExceeded) as exc:
        check_timeline_bytes("free", limit + 1)
    assert exc.value.code == "PLAN_TIMELINE_BYTES_EXCEEDED"
    assert status_for(exc.value.code) == 402
    q = JobQueue()
    tenant = _tenant("free")
    with pytest.raises(PlanLimitExceeded):
        _enqueue(q, tenant, 1, kind="viz.bake", payload={"timeline_bytes": limit + 1})
    _enqueue(q, tenant, 2, kind="viz.bake", payload={"timeline_bytes": limit})


def test_api_returns_machine_readable_429(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    _tenant("free")
    tok = get_auth_store().issue("acme", scopes=["read", "run"])
    headers = {"Authorization": f"Bearer {tok.token_id}", "X-QCompass-Tenant": "acme"}
    client = TestClient(build_app())
    from tests.test_worker_queue import H2 as body
    assert client.post("/api/qcompass/domains/chemistry/runs", json=body, headers=headers).status_code == 202
    resp = client.post("/api/qcompass/domains/chemistry/runs", json=body, headers=headers)
    assert resp.status_code == 429
    assert resp.json()["detail"]["code"] == "PLAN_CONCURRENT_JOBS_EXCEEDED"


def test_router_enforces_tenant_qpu_budget_at_and_over_the_boundary() -> None:
    pytest.importorskip("qcompass_router")
    from qcompass_router import pricing as qr_pricing
    from qcompass_router.pricing import PricingEngine

    from ucgle_f1.m8_agent.auth import reset_active_tenant, set_active_tenant

    engine = PricingEngine()
    paid = next(
        (e for e in qr_pricing.pricing_stub.list_entries()
         if not e.is_free_tier and engine.estimate(e.provider, e.backend, shots=1000).total_usd > 0),
    )
    qr_pricing.set_tenant_budget_hook(None)
    cost = engine.estimate(paid.provider, paid.backend, shots=1000).total_usd
    store = get_auth_store()
    store.ensure_tenant("acme")
    store.upsert_budget("acme", cost)  # remaining == cost: allowed
    assert install_budget_hook()
    token = set_active_tenant("acme")
    try:
        engine.estimate(paid.provider, paid.backend, shots=1000)
        store.record_spend("acme", cost * 1e-3)  # now just under the estimate
        with pytest.raises(AuthError) as exc:
            engine.estimate(paid.provider, paid.backend, shots=1000)
        assert exc.value.code == "BUDGET_EXCEEDED"
        assert status_for(exc.value.code) == 402
    finally:
        reset_active_tenant(token)
        qr_pricing.set_tenant_budget_hook(None)
