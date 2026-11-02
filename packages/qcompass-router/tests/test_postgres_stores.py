"""P3-01: the router's calibration history, pricing cache and free-tier
ledger live in Postgres (RLS, restart-safe, shared between processes)."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

import psycopg
import pytest
from sqlalchemy import Engine, text

from qcompass_router.calibration import (
    CalibrationCache,
    CalibrationSnapshot,
    DeviceCalibration,
)
from qcompass_router.pricing import HOUSE_ACCOUNT, FreeTierLedger, PricingEngine


def _libpq(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False).replace(
        "postgresql+psycopg://", "postgresql://",
    )


def _as_user(conn: psycopg.Connection, user_id: str) -> None:
    conn.execute("set local role authenticated")
    conn.execute(
        "select set_config('request.jwt.claims', %s, true)",
        (json.dumps({"sub": user_id, "role": "authenticated"}),),
    )


def test_calibration_round_trips_and_survives_a_new_cache(pg_engine: Engine) -> None:
    t0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    first = CalibrationCache(pg_engine)
    first.record_device(DeviceCalibration("ibm", "ibm_torino", t0, 0.01, 0.02, 100.0, 90.0))
    first.record(CalibrationSnapshot("ibm", "ibm_torino", date(2026, 10, 1), 0.01, 0.02, 95.0))

    # A fresh cache (a restarted process) reads the same rows.
    again = CalibrationCache(pg_engine)
    latest = again.latest_device("ibm", "ibm_torino")
    assert latest == DeviceCalibration("ibm", "ibm_torino", t0, 0.01, 0.02, 100.0, 90.0)
    assert latest.recorded_at.tzinfo is not None
    assert again._snapshot("ibm", "ibm_torino", date(2026, 10, 1)) == CalibrationSnapshot(
        "ibm", "ibm_torino", date(2026, 10, 1), 0.01, 0.02, 95.0,
    )
    # Upsert on the same key replaces, never duplicates.
    again.record_device(DeviceCalibration("ibm", "ibm_torino", t0, 0.03, 0.02, 100.0, 90.0))
    hist = again.device_history("ibm", "ibm_torino", anchor=t0 + timedelta(seconds=1))
    assert [h.two_q_error for h in hist] == [0.03]


def test_pricing_cache_is_shared_through_postgres(pg_engine: Engine, tmp_path) -> None:
    engine_a = PricingEngine(cache_dir=tmp_path / "unused", engine=pg_engine)
    engine_a.refresh_live(["ibm"])
    assert not (tmp_path / "unused").exists(), "no file cache when an engine is injected"
    with pg_engine.connect() as conn:
        row = conn.execute(
            text("select origin, entries from public.router_pricing_cache where provider = 'ibm'"),
        ).one()
    assert row.origin == "seed"
    assert row.entries, "the seed entries are cached"

    # A second engine instance (another worker) reads the cached price.
    engine_b = PricingEngine(engine=pg_engine)
    backend = next(iter(row.entries))
    cost = engine_b.estimate("ibm", backend, shots=1000)
    assert cost.source == "cache"
    assert cost.cache_age_s >= 0
    assert cost.total_usd == engine_a.estimate("ibm", backend, shots=1000).total_usd


def test_free_tier_ledger_persists_and_consumes_atomically(pg_engine: Engine) -> None:
    ledger = FreeTierLedger.persisted(pg_engine)
    assert ledger.buckets, "seeded from the pricing seed's free_tiers"
    tier = next(iter(ledger.buckets))
    start = ledger.remaining(tier)
    assert start > 0

    other = FreeTierLedger.persisted(pg_engine)  # a second worker
    ledger.consume(tier, 1.0)
    other.consume(tier, 2.0)  # decrements the shared balance, not its stale copy
    assert other.remaining(tier) == pytest.approx(start - 3.0)

    reloaded = FreeTierLedger.persisted(pg_engine)
    assert reloaded.remaining(tier) == pytest.approx(start - 3.0)
    assert list(reloaded.buckets) == list(ledger.buckets), "seed tier order kept"

    reloaded.set_remaining(tier, 0.0)
    assert FreeTierLedger.persisted(pg_engine).tier_for_backend(
        next(iter(ledger.buckets[tier].applicable_backends), "none"),
    ) != tier

    with pg_engine.connect() as conn:
        accounts = {r[0] for r in conn.execute(text("select account from public.router_free_tier_ledger"))}
    assert accounts == {HOUSE_ACCOUNT}


def test_pricing_engine_with_engine_uses_the_persisted_house_ledger(pg_engine: Engine) -> None:
    ledger = FreeTierLedger.persisted(pg_engine)
    tier = next(iter(ledger.buckets))
    ledger.set_remaining(tier, 0.5)
    assert PricingEngine(engine=pg_engine).ledger.remaining(tier) == pytest.approx(0.5)


def test_rls_free_tier_rows_are_tenant_scoped_and_platform_data_read_only(
    pg_engine: Engine,
) -> None:
    url = _libpq(pg_engine)
    with psycopg.connect(url, autocommit=True) as conn:
        alice = str(conn.execute(
            "insert into auth.users (email) values ('alice@example.test') returning id",
        ).fetchone()[0])
        acme = str(conn.execute(
            "insert into public.tenants (name, slug) values ('Acme', 'acme-rls') returning id",
        ).fetchone()[0])
        globex = str(conn.execute(
            "insert into public.tenants (name, slug) values ('Globex', 'globex-rls') returning id",
        ).fetchone()[0])
        conn.execute(
            "insert into public.tenant_members (tenant_id, user_id, role) values (%s, %s, 'member')",
            (acme, alice),
        )
    FreeTierLedger.persisted(pg_engine)  # house
    FreeTierLedger.persisted(pg_engine, tenant_id=acme)
    FreeTierLedger.persisted(pg_engine, tenant_id=globex)
    CalibrationCache(pg_engine).record_device(
        DeviceCalibration("ibm", "ibm_torino", datetime.now(UTC), 0.01, 0.02, 1.0, 1.0),
    )
    PricingEngine(engine=pg_engine).refresh_live(["ibm"])

    with psycopg.connect(url) as conn:
        _as_user(conn, alice)
        accounts = {r[0] for r in conn.execute("select account from public.router_free_tier_ledger")}
        calib = conn.execute("select count(*) from public.router_calibration_devices").fetchone()[0]
        prices = conn.execute("select count(*) from public.router_pricing_cache").fetchone()[0]
        conn.rollback()
    assert accounts == {f"tenant:{acme}"}, "members see only their tenant's account"
    assert calib == 1
    assert prices == 1

    for stmt in (
        "insert into public.router_calibration_devices values ('x', 'y', now(), 0, 0, 0, 0)",
        "insert into public.router_pricing_cache (provider) values ('evil')",
        "update public.router_free_tier_ledger set units = 1e9",
    ):
        with psycopg.connect(url) as conn:
            _as_user(conn, alice)
            if stmt.startswith("update"):
                # RLS has no update policy: the update matches no rows.
                assert conn.execute(stmt).rowcount == 0
            else:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    conn.execute(stmt)
            conn.rollback()
