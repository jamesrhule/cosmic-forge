"""Live-pricing adapter (PROMPT 6B + PROMPT 6 v2).

For now this module is a thin wrapper over :mod:`pricing_stub`
that exposes a uniform fetch interface and an on-disk cache. The
actual provider HTTP fetchers are intentionally placeholder
methods that raise ``NotImplementedError`` — production wiring
needs vendor-specific endpoints + auth that lives outside the
PROMPT 6B audit fence.

PROMPT 6 v2 layers on:
  - :class:`Cost` dataclass: structured estimate carrying the
    breakdown (per-shot, per-task, etc.) and free-tier metadata.
  - :class:`PricingEngine`: v2-canonical class. ``estimate(provider,
    backend, circuit, shots) -> Cost`` swaps the v1 ``LivePricing``
    signature; ``refresh_live(providers)`` accepts a multi-provider
    list. Live HTTP fetchers MUST go through :mod:`ssl_pin`.

Cache layout:
  ${QCOMPASS_PRICING_CACHE:-~/.cache/qcompass/pricing}/
    <provider>.json     # last-known pricing entries

Every cloud HTTP call MUST go through :mod:`ssl_pin`. The audit
``A-router-2`` greps :mod:`providers` for non-pinned httpx use,
and any new fetcher added to this module MUST also use
``ssl_pin.client()``.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import pricing_stub
from . import ssl_pin


def _default_cache_dir() -> Path:
    env = os.environ.get("QCOMPASS_PRICING_CACHE")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "qcompass" / "pricing"


@dataclass(frozen=True)
class Cost:
    """Structured cost estimate (PROMPT 6 v2).

    The dollar total is in :attr:`total_usd`; :attr:`breakdown`
    records the per-axis contribution (per_shot / per_task /
    per_run / per_second / per_credit / min_program). The free-tier
    flag mirrors :class:`pricing_stub.PricingEntry.is_free_tier` so
    the router can prefer free-tier candidates without re-asking the
    seed.
    """

    provider: str
    backend: str
    shots: int
    total_usd: float
    breakdown: dict[str, float] = field(default_factory=dict)
    free_tier: bool = False
    source: str = "seed"   # "seed" | "cache" | "live"
    notes: str = ""


class LivePricing:
    """Live pricing facade (PROMPT 6B baseline).

    PROMPT 6B ships the cache + fallback path; the actual provider
    HTTP fetchers raise ``NotImplementedError``. Tests use
    ``respx`` to stub them out.
    """

    def __init__(self, cache_dir: Path | None = None, ttl_seconds: int = 86_400) -> None:
        self._cache_dir = cache_dir or _default_cache_dir()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl_seconds

    # ── Public API ───────────────────────────────────────────────

    def estimate(self, provider: str, backend: str, shots: int) -> float:
        """Live-or-cache lookup, falling back to the static seed."""
        cached = self._load_cache(provider)
        if cached and self._cache_fresh(cached):
            entry = cached.get("entries", {}).get(backend)
            if entry:
                return _estimate_from_entry(entry, shots)
        # No fresh cache → fall back to stub seed.
        return pricing_stub.estimate(provider, backend, shots)

    def refresh(self, provider: str) -> None:
        """Trigger a live fetch for ``provider`` (Phase-1: stub)."""
        try:
            entries = self._fetch_live(provider)
        except NotImplementedError:
            # Live fetcher not wired yet; populate the cache from the
            # static seed so subsequent ``estimate`` calls hit the
            # in-memory path without re-reading the YAML.
            entries = {
                e.backend: dict(e.raw)
                for e in pricing_stub.list_entries()
                if e.provider == provider
            }
        self._save_cache(provider, entries)

    # ── Internals ────────────────────────────────────────────────

    def _fetch_live(self, provider: str) -> dict[str, dict[str, Any]]:
        """Live fetcher — Phase-1 stub.

        Concrete implementations land under provider-specific
        modules (e.g. pricing_ibm.py) and use ``ssl_pin.client``.
        Even the stub path documents the SSL-pinned client to
        satisfy the v2 §A-router-2 invariant.
        """
        # Touch ssl_pin so the dependency is structural; live
        # fetchers replace this stub but MUST use the same client.
        _ = ssl_pin.client  # noqa: F841 — structural binding for A-router-2
        msg = (
            f"Live pricing fetcher for {provider!r} is not yet wired. "
            "Subclass PricingEngine and override _fetch_live to use "
            "ssl_pin.client() for the per-provider HTTP path."
        )
        raise NotImplementedError(msg)

    def _cache_path(self, provider: str) -> Path:
        return self._cache_dir / f"{provider}.json"

    def _load_cache(self, provider: str) -> dict[str, Any] | None:
        path = self._cache_path(provider)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None

    def _cache_fresh(self, cached: dict[str, Any]) -> bool:
        ts = float(cached.get("recorded_at_epoch", 0.0))
        return (time.time() - ts) < self._ttl

    def _save_cache(self, provider: str, entries: dict[str, Any]) -> None:
        payload = {
            "recorded_at_epoch": time.time(),
            "entries": entries,
        }
        self._cache_path(provider).write_text(json.dumps(payload, indent=2))


class PricingEngine(LivePricing):
    """v2-canonical pricing engine.

    Drop-in extension of :class:`LivePricing` with the v2 signatures
    the spec mandates. The legacy ``LivePricing.estimate(provider,
    backend, shots) -> float`` continues to work for v1 call sites;
    v2 call sites use ``PricingEngine.estimate(provider, backend,
    circuit, shots) -> Cost``.
    """

    def estimate(  # type: ignore[override]
        self,
        provider: str,
        backend: str,
        circuit: Any | None = None,
        shots: int = 1024,
    ) -> Cost:  # type: ignore[override]
        """Return a structured :class:`Cost` for the request.

        ``circuit`` is currently unused by the seed-based estimator
        (kept for v2-API compatibility). When PricingEngine is later
        extended to circuit-aware pricing (depth / 2Q-gate count
        scaling), the parameter feeds the heuristic without changing
        callers.
        """
        if shots < 1:
            msg = f"shots must be >= 1; got {shots}"
            raise ValueError(msg)

        cached = self._load_cache(provider)
        source = "seed"
        breakdown: dict[str, float] = {}
        free_tier = False
        if cached and self._cache_fresh(cached):
            entry = cached.get("entries", {}).get(backend)
            if entry:
                total, breakdown = _estimate_with_breakdown(entry, shots)
                free_tier = bool(
                    entry.get("free_minutes_per_month")
                    or entry.get("free_credits_per_month")
                    or entry.get("free_tier"),
                )
                source = "cache"
                return Cost(
                    provider=provider, backend=backend, shots=shots,
                    total_usd=total, breakdown=breakdown,
                    free_tier=free_tier, source=source,
                )
        # Fall back to the seed.
        seed_entry = pricing_stub.lookup(provider, backend)
        if seed_entry is None:
            msg = f"No pricing for {provider}/{backend}"
            raise KeyError(msg)
        total, breakdown = _estimate_with_breakdown(seed_entry.raw, shots)
        return Cost(
            provider=provider, backend=backend, shots=shots,
            total_usd=total, breakdown=breakdown,
            free_tier=seed_entry.is_free_tier, source=source,
        )

    def refresh_live(self, providers: Iterable[str]) -> None:
        """v2 multi-provider refresh; falls back per-provider on failure."""
        for provider in providers:
            self.refresh(provider)


def _estimate_from_entry(entry: dict[str, Any], shots: int) -> float:
    cost = 0.0
    if entry.get("per_shot_usd"):
        cost += float(entry["per_shot_usd"]) * shots
    if entry.get("per_task_usd"):
        cost += float(entry["per_task_usd"])
    if entry.get("per_run_usd"):
        cost += float(entry["per_run_usd"])
    if entry.get("per_second_usd"):
        cost += float(entry["per_second_usd"]) * (shots / 1024.0)
    if entry.get("per_credit_usd"):
        cost += float(entry["per_credit_usd"]) * (shots / 1024.0)
    if entry.get("min_program_usd"):
        cost = max(cost, float(entry["min_program_usd"]))
    return cost


def _estimate_with_breakdown(
    entry: dict[str, Any], shots: int,
) -> tuple[float, dict[str, float]]:
    """Same calculation as :func:`_estimate_from_entry` with axis-level
    breakdown the v2 :class:`Cost` exposes.
    """
    breakdown: dict[str, float] = {}
    cost = 0.0
    if entry.get("per_shot_usd"):
        contrib = float(entry["per_shot_usd"]) * shots
        breakdown["per_shot"] = contrib
        cost += contrib
    if entry.get("per_task_usd"):
        contrib = float(entry["per_task_usd"])
        breakdown["per_task"] = contrib
        cost += contrib
    if entry.get("per_run_usd"):
        contrib = float(entry["per_run_usd"])
        breakdown["per_run"] = contrib
        cost += contrib
    if entry.get("per_second_usd"):
        contrib = float(entry["per_second_usd"]) * (shots / 1024.0)
        breakdown["per_second"] = contrib
        cost += contrib
    if entry.get("per_credit_usd"):
        contrib = float(entry["per_credit_usd"]) * (shots / 1024.0)
        breakdown["per_credit"] = contrib
        cost += contrib
    if entry.get("min_program_usd"):
        floor = float(entry["min_program_usd"])
        if cost < floor:
            breakdown["min_program_floor"] = floor - cost
            cost = floor
    return cost, breakdown


__all__ = ["Cost", "LivePricing", "PricingEngine"]
