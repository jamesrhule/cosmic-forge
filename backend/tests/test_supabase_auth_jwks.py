"""Gate 1 (c7, LOW): the Supabase JWKS cache survives an outage and a flood.

Before the fix, once the 600 s TTL lapsed while the JWKS endpoint failed,
every Supabase-authenticated request made its own outbound fetch and
answered 503, although a usable key set was cached (50 requests: 50 fetches,
50 x 503). Now:

- stale-if-error: a failed TTL refresh keeps serving the cached set, for at
  most ``_JWKS_STALE_IF_ERROR_S`` past its TTL;
- after a failure no new fetch for ``_JWKS_RETRY_MIN_S``;
- one fetch per URL at a time (single flight): concurrent callers serve the
  cached set or wait for that fetch.

The clock is fake (the module's ``time``), so no test sleeps for the TTL.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from ucgle_f1.m8_agent import supabase_auth

BASE = "https://proj.supabase.test"
TTL = 600.0
RETRY = 30.0
STALE = 3600.0
OLD = ec.generate_private_key(ec.SECP256R1())
NEW = ec.generate_private_key(ec.SECP256R1())


def _jwk(key: Any, kid: str) -> dict[str, Any]:
    out = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key()))
    out.update({"kid": kid, "alg": "ES256"})
    return out


def _token(key: Any, kid: str) -> str:
    now = int(time.time())
    claims = {
        "sub": "u",
        "aud": "authenticated",
        "iss": f"{BASE}/auth/v1",
        "iat": now,
        "exp": now + 600,
    }
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": kid})


def _status(token: str) -> int:
    try:
        supabase_auth.verify_supabase_token(token)
    except HTTPException as exc:
        return exc.status_code
    return 200


class Upstream:
    """A fake JWKS endpoint: counts fetches, can fail, can block."""

    def __init__(self) -> None:
        self.published: dict[str, Any] = {"keys": [_jwk(OLD, "k-old")]}
        self.down = False
        self.calls = 0
        self.gate: threading.Event | None = None  # set → fetches block until it is set
        self.entered = threading.Event()
        self._count = threading.Lock()

    def __call__(self, url: str) -> dict[str, Any]:
        assert url == f"{BASE}/auth/v1/.well-known/jwks.json"
        with self._count:
            self.calls += 1
        self.entered.set()
        if self.gate is not None:
            self.gate.wait(10)
        if self.down:
            raise RuntimeError("jwks endpoint down")
        return json.loads(json.dumps(self.published))


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    now = [1000.0]
    monkeypatch.setattr(supabase_auth, "time", SimpleNamespace(monotonic=lambda: now[0]))
    return now


@pytest.fixture
def upstream(monkeypatch: pytest.MonkeyPatch, clock: list[float]) -> Iterator[Upstream]:
    monkeypatch.setenv("SUPABASE_URL", BASE)
    fake = Upstream()
    supabase_auth.set_jwks_fetcher(fake)
    try:
        yield fake
    finally:
        supabase_auth.set_jwks_fetcher(None)


def test_constants_are_the_documented_bounds() -> None:
    assert supabase_auth._JWKS_TTL_S == TTL
    assert supabase_auth._JWKS_RETRY_MIN_S == RETRY
    assert supabase_auth._JWKS_STALE_IF_ERROR_S == STALE


def test_ttl_refresh_failure_serves_the_cached_set_and_backs_off(
    upstream: Upstream, clock: list[float]
) -> None:
    good = _token(OLD, "k-old")
    assert _status(good) == 200 and upstream.calls == 1
    clock[0] += TTL + 1
    upstream.down = True
    statuses = [_status(good) for _ in range(50)]
    assert statuses == [200] * 50, "stale-if-error: the cached set still verifies"
    assert upstream.calls == 2, "50 requests after the TTL make one outbound fetch, not 50"
    clock[0] += RETRY - 1
    assert [_status(good) for _ in range(10)] == [200] * 10
    assert upstream.calls == 2, "no new fetch within the retry interval"
    clock[0] += 2
    assert _status(good) == 200
    assert upstream.calls == 3, "one retry once the interval has passed"
    upstream.down = False
    clock[0] += RETRY + 1
    upstream.published["keys"].append(_jwk(NEW, "k-new"))
    assert _status(_token(NEW, "k-new")) == 200, "the refresh after recovery brings the new key"
    assert upstream.calls == 4
    assert [_status(good) for _ in range(10)] == [200] * 10
    assert upstream.calls == 4, "fresh again: served from the cache"


def test_stale_if_error_is_bounded(upstream: Upstream, clock: list[float]) -> None:
    good = _token(OLD, "k-old")
    fetched_at = clock[0]
    assert _status(good) == 200
    upstream.down = True
    clock[0] = fetched_at + TTL + STALE - 1
    assert _status(good) == 200, "still inside the stale-if-error bound"
    calls = upstream.calls
    clock[0] = fetched_at + TTL + STALE + 1
    assert _status(good) == 503, "past the bound the cached set is no longer trusted"
    assert upstream.calls == calls, "and the retry interval still holds"
    clock[0] += RETRY + 1
    assert _status(good) == 503
    assert upstream.calls == calls + 1


def test_cold_start_failure_is_rate_limited(upstream: Upstream, clock: list[float]) -> None:
    upstream.down = True
    good = _token(OLD, "k-old")
    assert [_status(good) for _ in range(50)] == [503] * 50
    assert upstream.calls == 1, "nothing cached: one fetch, then 503 without fetching"
    clock[0] += RETRY + 1
    upstream.down = False
    assert _status(good) == 200
    assert upstream.calls == 2


def test_unknown_kid_during_an_outage_is_503_and_rate_limited(
    upstream: Upstream, clock: list[float]
) -> None:
    good = _token(OLD, "k-old")
    assert _status(good) == 200
    upstream.down = True
    assert _status(_token(NEW, "k-new")) == 503, "a forced refetch never settles for a stale set"
    assert upstream.calls == 2
    assert [_status(_token(NEW, f"forged-{i}")) for i in range(20)] == [401] * 20
    assert upstream.calls == 2, "forged kids: no more fetches within the interval"
    assert _status(good) == 200


def _run_concurrently(n: int, token: str) -> tuple[list[threading.Thread], list[int]]:
    results: list[int] = []
    start = threading.Barrier(n + 1)

    def worker() -> None:
        start.wait(10)
        results.append(_status(token))

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    start.wait(10)
    return threads, results


def test_concurrent_cold_start_makes_one_fetch(upstream: Upstream) -> None:
    upstream.gate = threading.Event()
    threads, results = _run_concurrently(16, _token(OLD, "k-old"))
    assert upstream.entered.wait(10)
    time.sleep(0.3)  # let every caller reach the cache while the fetch is in flight
    upstream.gate.set()
    for t in threads:
        t.join(10)
    assert results == [200] * 16
    assert upstream.calls == 1, "single flight: concurrent callers wait for the one fetch"


def test_concurrent_ttl_refresh_makes_one_fetch_and_serves_the_cached_set(
    upstream: Upstream, clock: list[float]
) -> None:
    good = _token(OLD, "k-old")
    assert _status(good) == 200
    clock[0] += TTL + 1
    upstream.gate = threading.Event()
    threads, results = _run_concurrently(16, good)
    assert upstream.entered.wait(10)
    deadline = time.monotonic() + 10
    while len(results) < 15 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert results == [200] * 15, "the others answer from the cached set during the fetch"
    upstream.gate.set()
    for t in threads:
        t.join(10)
    assert results == [200] * 16
    assert upstream.calls == 2, "one refresh for 16 concurrent callers"
