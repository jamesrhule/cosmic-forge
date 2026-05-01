"""Live-pricing adapter (PROMPT 6B).

For now this module is a thin wrapper over :mod:`pricing_stub`
that exposes a uniform fetch interface and an on-disk cache. The
actual provider HTTP fetchers are intentionally placeholder
methods that raise ``NotImplementedError`` — production wiring
needs vendor-specific endpoints + auth that lives outside the
PROMPT 6B audit fence.

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
from pathlib import Path
from typing import Any

from . import pricing_stub


def _default_cache_dir() -> Path:
    env = os.environ.get("QCOMPASS_PRICING_CACHE")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "qcompass" / "pricing"


class LivePricing:
    """Live pricing facade.

    PROMPT 6B ships the cache + fallback path; the actual provider
    HTTP fetchers raise ``NotImplementedError``. Tests use
    ``respx`` to stub them out (see PROMPT 6C).
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
        """
        msg = (
            f"Live pricing fetcher for {provider!r} is not yet wired. "
            "PROMPT 6C lands per-provider HTTP fetchers."
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
