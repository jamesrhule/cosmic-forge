"""P3-01: the bench leaderboard lives in Postgres (public read, service write)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from sqlalchemy import Engine

from qcompass_bench import BenchEntry, LeaderboardStore


def _entry(fixture: str, started_at: datetime, **kw: object) -> BenchEntry:
    base = {
        "domain": "chemistry", "fixture": fixture, "package_version": "0.2.0",
        "started_at": started_at, "wall_seconds": 1.5, "classical_energy": -1.137,
        "quantum_energy": None, "provenance_hash": "abc", "ok": True, "notes": "",
    }
    base.update(kw)
    return BenchEntry(**base)  # type: ignore[arg-type]


def test_record_and_read_back_newest_first(pg_engine: Engine) -> None:
    now = datetime.now(UTC)
    store = LeaderboardStore(pg_engine)
    old = _entry("h2", now - timedelta(days=10))
    new = _entry("lih", now - timedelta(hours=1), ok=False, notes="solver missing")
    first_id = store.record(old)
    second_id = store.record(new)
    assert second_id == first_id + 1

    # A fresh store (a restarted process) sees the same rows.
    again = LeaderboardStore(pg_engine)
    assert again.all() == [new, old]
    assert again.recent(since=timedelta(days=1)) == [new]


def test_naive_started_at_is_taken_as_utc(pg_engine: Engine) -> None:
    store = LeaderboardStore(pg_engine)
    store.record(_entry("h2", datetime(2026, 10, 1, 12, 0)))
    (row,) = store.all()
    assert row.started_at == datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def test_leaderboard_is_publicly_readable_but_not_writable(pg_engine: Engine) -> None:
    LeaderboardStore(pg_engine).record(_entry("h2", datetime.now(UTC)))
    url = pg_engine.url.render_as_string(hide_password=False).replace(
        "postgresql+psycopg://", "postgresql://",
    )
    with psycopg.connect(url) as conn:
        conn.execute("set local role anon")
        assert conn.execute("select count(*) from public.bench_runs").fetchone()[0] == 1
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "insert into public.bench_runs (domain, fixture, package_version, started_at,"
                " wall_seconds, provenance_hash, ok) values ('x','y','0',now(),0,'h',true)",
            )
        conn.rollback()


def test_missing_database_url_is_blocked_on_james(monkeypatch: pytest.MonkeyPatch) -> None:
    from qcompass_core.db import DatabaseNotConfigured

    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(DatabaseNotConfigured, match="BLOCKED-ON-JAMES:DATABASE_URL"):
        LeaderboardStore()
