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

Router-branch 6B layers (merged by P0-02):
  - :class:`FreeTierLedger`: free-tier buckets seeded from the
    ``free_tiers:`` block of the pricing seed; the router prefers a
    backend while its tier covers the job. In memory by default;
    :meth:`FreeTierLedger.persisted` binds it to the Postgres table
    ``public.router_free_tier_ledger`` per provider account (P3-01).
  - live refresh: ``PricingEngine.refresh_live`` fetches provider
    pricing over an SSL-pinned client (``ca_bundle`` or certifi) when
    a ``client_factory`` is injected or ``QCOMPASS_PRICING_LIVE=1``.
    Without either it never touches the network (R8) and seeds the
    cache from the static seed instead. Live failures write nothing
    and never raise; estimates fall back to the seed.

Cache storage (P3-01):
  - with an injected SQLAlchemy ``engine`` (the API and worker always
    pass one): the Postgres table ``public.router_pricing_cache``, one
    row per provider ``(provider, recorded_at, origin, entries)``;
  - without one (the library used standalone, offline): files under
    ${QCOMPASS_PRICING_CACHE:-~/.cache/qcompass/pricing}/
      <provider>.json     # {"recorded_at_epoch", "origin", "entries"}

Every cloud HTTP call MUST go through :mod:`ssl_pin`. The audit
``A-router-2`` greps :mod:`providers` for non-pinned httpx use,
and any new fetcher added to this module MUST also use
``ssl_pin.client()``.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import ssl
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import pricing_stub, ssl_pin

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy import Engine

logger = logging.getLogger(__name__)

_LIVE_ENV = "QCOMPASS_PRICING_LIVE"


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
    # "seed" | "cache" (seed-populated cache) | "live" (live-fetched
    # cache) | "adapter" (adapter price override) | "unpriced"
    source: str = "seed"
    notes: str = ""
    cache_age_s: int = 0

    # Router-branch 6B names for the same data.
    @property
    def usd(self) -> float:
        return self.total_usd

    @property
    def live(self) -> bool:
        return self.source == "live"

    @property
    def pricing_basis(self) -> str:
        """Dominant pricing axis (``"free"`` for a zero estimate)."""
        if self.total_usd <= 0.0 or not self.breakdown:
            return "free"
        return max(self.breakdown, key=lambda axis: self.breakdown[axis])


# ---------------------------------------------------------------------------
# Free-tier ledger (router-branch 6B)
# ---------------------------------------------------------------------------


@dataclass
class _FreeTierBucket:
    units: float = 0.0
    unit_kind: str = "minutes"  # "minutes" | "credits" | "usd" | "hours"
    applicable_backends: tuple[str, ...] = ()


_TIER_UNIT_KEYS: tuple[tuple[str, str], ...] = (
    ("minutes_per_month", "minutes"),
    ("credits_per_month", "credits"),
    ("simulator_hours_per_month", "hours"),
    ("usd", "usd"),
)


HOUSE_ACCOUNT = "house"


@dataclass
class FreeTierLedger:
    """Free-tier ledger.

    Per-tier remaining units (minutes / credits / simulator-hours /
    USD). In memory by default (tests preload it directly); a ledger
    from :meth:`persisted` writes every change through to
    ``public.router_free_tier_ledger`` for one provider account (PHC's
    ``"house"`` account, or a tenant's own account), so balances survive
    restarts and are shared by every worker (P3-01).
    """

    buckets: dict[str, _FreeTierBucket] = field(default_factory=dict)
    _engine: Any = field(default=None, repr=False, compare=False)
    _account: str = field(default=HOUSE_ACCOUNT, repr=False, compare=False)
    _tenant_id: str | None = field(default=None, repr=False, compare=False)

    @classmethod
    def persisted(
        cls,
        engine: Engine,
        *,
        tenant_id: str | None = None,
        seed: dict[str, Any] | None = None,
    ) -> FreeTierLedger:
        """Load (or seed and store) the ledger of one provider account.

        ``tenant_id`` (a ``public.tenants.id`` UUID) selects that tenant's
        own provider account; ``None`` is PHC's house account. Tiers with
        no stored row are seeded from the pricing seed's ``free_tiers``.
        """
        from sqlalchemy import text

        account = f"tenant:{tenant_id}" if tenant_id else HOUSE_ACCOUNT
        seeded = cls.from_seed(seed)
        with engine.begin() as conn:
            for name, b in seeded.buckets.items():
                conn.execute(
                    text(
                        "INSERT INTO public.router_free_tier_ledger "
                        "(account, tier_name, tenant_id, units, unit_kind, applicable_backends) "
                        "VALUES (:account, :tier, CAST(:tenant_id AS uuid), :units, :kind, :backends) "
                        "ON CONFLICT (account, tier_name) DO NOTHING",
                    ),
                    {
                        "account": account, "tier": name, "tenant_id": tenant_id,
                        "units": b.units, "kind": b.unit_kind,
                        "backends": list(b.applicable_backends),
                    },
                )
            rows = conn.execute(
                text(
                    "SELECT tier_name, units, unit_kind, applicable_backends "
                    "FROM public.router_free_tier_ledger WHERE account = :account "
                    "ORDER BY tier_name",
                ),
                {"account": account},
            ).mappings().all()
        # Keep the seed's tier order (the router's preference order), then
        # any tiers only present in the table.
        stored = {r["tier_name"]: r for r in rows}
        order = [n for n in seeded.buckets if n in stored] + [
            n for n in stored if n not in seeded.buckets
        ]
        out = cls(_engine=engine, _account=account, _tenant_id=tenant_id)
        for name in order:
            r = stored[name]
            out.buckets[name] = _FreeTierBucket(
                units=float(r["units"]),
                unit_kind=str(r["unit_kind"]),
                applicable_backends=tuple(r["applicable_backends"] or ()),
            )
        return out

    def _store(self, tier_name: str, *, consume: float | None = None) -> None:
        """Write one bucket through to Postgres (no-op when in memory)."""
        if self._engine is None:
            return
        from sqlalchemy import text

        b = self.buckets[tier_name]
        with self._engine.begin() as conn:
            if consume is not None:
                # Atomic decrement: concurrent workers share the balance.
                units = conn.execute(
                    text(
                        "UPDATE public.router_free_tier_ledger "
                        "SET units = greatest(0, units - :u), updated_at = now() "
                        "WHERE account = :account AND tier_name = :tier RETURNING units",
                    ),
                    {"u": consume, "account": self._account, "tier": tier_name},
                ).scalar_one_or_none()
                if units is not None:
                    b.units = float(units)
                    return
            conn.execute(
                text(
                    "INSERT INTO public.router_free_tier_ledger "
                    "(account, tier_name, tenant_id, units, unit_kind, applicable_backends) "
                    "VALUES (:account, :tier, CAST(:tenant_id AS uuid), :units, :kind, :backends) "
                    "ON CONFLICT (account, tier_name) DO UPDATE SET "
                    "units = excluded.units, updated_at = now()",
                ),
                {
                    "account": self._account, "tier": tier_name, "tenant_id": self._tenant_id,
                    "units": b.units, "kind": b.unit_kind,
                    "backends": list(b.applicable_backends),
                },
            )

    @classmethod
    def from_seed(cls, seed: dict[str, Any] | None = None) -> FreeTierLedger:
        """Build from a seed payload's ``free_tiers`` block (default:
        the package seed)."""
        tiers = (
            pricing_stub.free_tiers() if seed is None
            else dict(seed.get("free_tiers") or {})
        )
        out = cls()
        for tier_name, body in tiers.items():
            applicable = tuple(body.get("applicable_backends", []))
            for key, kind in _TIER_UNIT_KEYS:
                if key in body:
                    out.buckets[tier_name] = _FreeTierBucket(
                        units=float(body[key]),
                        unit_kind=kind,
                        applicable_backends=applicable,
                    )
                    break
        return out

    def remaining(self, tier_name: str) -> float:
        b = self.buckets.get(tier_name)
        return b.units if b else 0.0

    def set_remaining(self, tier_name: str, units: float) -> None:
        b = self.buckets.get(tier_name)
        if b is None:
            self.buckets[tier_name] = _FreeTierBucket(units=units)
        else:
            b.units = units
        self._store(tier_name)

    def consume(self, tier_name: str, units: float) -> None:
        b = self.buckets.get(tier_name)
        if b is None:
            return
        b.units = max(0.0, b.units - units)
        self._store(tier_name, consume=units)

    def lists(self, backend: str) -> bool:
        """True when any tier names ``backend`` (exhausted or not)."""
        return any(
            backend in b.applicable_backends for b in self.buckets.values()
        )

    def tier_for_backend(self, backend: str) -> str | None:
        """First tier that names ``backend`` and still has units left."""
        for tier_name, bucket in self.buckets.items():
            if backend in bucket.applicable_backends and bucket.units > 0:
                return tier_name
        return None

    def covers(self, backend: str, runtime_s: float, shots: int) -> bool:
        """Whether the remaining allowance covers the job.

        Minutes / hours compare against ``runtime_s``; credits use one
        credit per 1000 shots (minimum 1); USD tiers cover while any
        balance remains.
        """
        tier = self.tier_for_backend(backend)
        if tier is None:
            return False
        bucket = self.buckets[tier]
        if bucket.unit_kind == "minutes":
            return bucket.units >= runtime_s / 60.0
        if bucket.unit_kind == "hours":
            return bucket.units >= runtime_s / 3600.0
        if bucket.unit_kind == "credits":
            return bucket.units >= max(1.0, shots / 1000.0)
        if bucket.unit_kind == "usd":
            return bucket.units > 0
        return False


class _LiveFetchError(Exception):
    """Live pricing unavailable (no httpx / missing CA bundle); callers
    fall back to the seed."""


# Per-provider cache TTLs for live-fetched pricing (seconds).
_DEFAULT_TTLS_S: dict[str, int] = {
    "ibm": 3600,
    "braket": 86400,
    "azure": 86400,
    "iqm": 86400,
}

# Provider pricing endpoints. URL hints that recorded cassettes match;
# any non-2xx / network error falls back to the seed.
_DEFAULT_ENDPOINTS: dict[str, str] = {
    "ibm": "https://api.quantum.ibm.com/runtime/jobs/pricing",
    "braket": "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBraket/current/index.json",
    "azure": "https://prices.azure.com/api/retail/prices?$filter=serviceName%20eq%20%27Azure%20Quantum%27",
    "iqm": "https://resonance.meetiqm.com/api/v1/pricing",
}


class LivePricing:
    """Live pricing facade (PROMPT 6B baseline).

    PROMPT 6B ships the cache + fallback path; the actual provider
    HTTP fetchers raise ``NotImplementedError``. Tests use
    ``respx`` to stub them out.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_seconds: int = 86_400,
        *,
        engine: Engine | None = None,
    ) -> None:
        self._engine = engine
        self._cache_dir = cache_dir or _default_cache_dir()
        if engine is None:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl_seconds

    # ── Public API ───────────────────────────────────────────────

    def estimate(self, provider: str, backend: str, shots: int) -> float:
        """Live-or-cache lookup, falling back to the static seed."""
        cached = self._load_cache(provider)
        if cached and self._cache_fresh(cached):
            entry = cached.get("entries", {}).get(backend)
            if entry:
                return pricing_stub.estimate_entry(entry, shots)[0]
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
            entries = _seed_entries(provider)
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
        _ = ssl_pin.client
        msg = (
            f"Live pricing fetcher for {provider!r} is not yet wired. "
            "Subclass PricingEngine and override _fetch_live to use "
            "ssl_pin.client() for the per-provider HTTP path."
        )
        raise NotImplementedError(msg)

    def _cache_path(self, provider: str) -> Path:
        return self._cache_dir / f"{provider}.json"

    def _load_cache(self, provider: str) -> dict[str, Any] | None:
        if self._engine is not None:
            return self._load_cache_db(provider)
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

    def _save_cache(
        self, provider: str, entries: dict[str, Any], *, origin: str = "seed",
    ) -> None:
        if self._engine is not None:
            self._save_cache_db(provider, entries, origin=origin)
            return
        payload = {
            "recorded_at_epoch": time.time(),
            "origin": origin,
            "entries": entries,
        }
        self._cache_path(provider).write_text(json.dumps(payload, indent=2))

    # Postgres cache (P3-01): one row per provider in
    # public.router_pricing_cache; same payload shape as the file cache.

    def _load_cache_db(self, provider: str) -> dict[str, Any] | None:
        from sqlalchemy import text

        assert self._engine is not None
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT extract(epoch from recorded_at) AS epoch, origin, entries "
                    "FROM public.router_pricing_cache WHERE provider = :provider",
                ),
                {"provider": provider},
            ).mappings().first()
        if row is None:
            return None
        return {
            "recorded_at_epoch": float(row["epoch"]),
            "origin": row["origin"],
            "entries": dict(row["entries"] or {}),
        }

    def _save_cache_db(
        self, provider: str, entries: dict[str, Any], *, origin: str,
    ) -> None:
        from sqlalchemy import text

        assert self._engine is not None
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO public.router_pricing_cache (provider, recorded_at, origin, entries) "
                    "VALUES (:provider, now(), :origin, CAST(:entries AS jsonb)) "
                    "ON CONFLICT (provider) DO UPDATE SET recorded_at = excluded.recorded_at, "
                    "origin = excluded.origin, entries = excluded.entries",
                ),
                {"provider": provider, "origin": origin, "entries": json.dumps(entries)},
            )


def _seed_entries(provider: str) -> dict[str, dict[str, Any]]:
    return {
        e.backend: dict(e.raw)
        for e in pricing_stub.list_entries()
        if e.provider == provider
    }


_TENANT_BUDGET_HOOK: Any = None


def set_tenant_budget_hook(hook: Any) -> None:
    """Install a callable ``(tenant_id, amount_usd) -> None`` budget gate.

    PROMPT 10 v2 §A: the qcompass-router's :class:`PricingEngine`
    consults this hook before returning a :class:`Cost`. Backend
    auth wires it to :func:`ucgle_f1.m8_agent.auth.gate_spend` so
    every estimate also enforces the active tenant's monthly
    budget.

    Pass ``None`` to clear (the default — no gating, preserves the
    v1 behaviour for callers without an auth context).
    """
    global _TENANT_BUDGET_HOOK
    _TENANT_BUDGET_HOOK = hook


def _tenant_budget_hook() -> Any:
    return _TENANT_BUDGET_HOOK


class PricingEngine(LivePricing):
    """v2-canonical pricing engine.

    Drop-in extension of :class:`LivePricing` with the v2 signatures
    the spec mandates. The legacy ``LivePricing.estimate(provider,
    backend, shots) -> float`` continues to work for v1 call sites;
    v2 call sites use ``PricingEngine.estimate(provider, backend,
    circuit, shots) -> Cost``.

    PROMPT 10 v2 §A — when the active tenant is set in the calling
    context AND a budget hook is registered via
    :func:`set_tenant_budget_hook`, every estimate consults the
    tenant's remaining budget and raises before returning a Cost
    that would exceed it.

    Router-branch 6B options: ``ca_bundle`` pins the live-fetch trust
    root (default certifi), ``endpoints`` / ``ttl_s`` override the
    per-provider URL and cache TTL, ``client_factory`` injects the
    HTTP client (tests pass stubs; production leaves it None and opts
    in with ``QCOMPASS_PRICING_LIVE=1``), and ``ledger`` overrides the
    seed-derived :class:`FreeTierLedger`. ``engine`` (P3-01) stores the
    pricing cache in Postgres and, unless ``ledger`` is given, loads the
    house account's persisted free-tier ledger.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_seconds: int = 86_400,
        *,
        ca_bundle: Path | None = None,
        endpoints: dict[str, str] | None = None,
        ttl_s: dict[str, int] | None = None,
        client_factory: Callable[[], Any] | None = None,
        ledger: FreeTierLedger | None = None,
        engine: Engine | None = None,
    ) -> None:
        super().__init__(cache_dir=cache_dir, ttl_seconds=ttl_seconds, engine=engine)
        self._ca_bundle = ca_bundle
        self._endpoints = {**_DEFAULT_ENDPOINTS, **(endpoints or {})}
        self._live_ttl = {**_DEFAULT_TTLS_S, **(ttl_s or {})}
        self._client_factory = client_factory
        if ledger is not None:
            self.ledger = ledger
        elif engine is not None:
            self.ledger = FreeTierLedger.persisted(engine)
        else:
            self.ledger = FreeTierLedger.from_seed()

    def estimate(  # type: ignore[override]
        self,
        provider: str,
        backend: str,
        circuit: Any | None = None,
        shots: int = 1024,
        *,
        tenant_id: str | None = None,
    ) -> Cost:  # type: ignore[override]
        """Return a structured :class:`Cost` for the request.

        ``circuit`` is currently unused by the seed-based estimator
        (kept for v2-API compatibility). When PricingEngine is later
        extended to circuit-aware pricing (depth / 2Q-gate count
        scaling), the parameter feeds the heuristic without changing
        callers.

        ``tenant_id`` defaults to the active tenant resolved from
        the auth-side context variable when the hook is wired. The
        budget hook (registered via :func:`set_tenant_budget_hook`)
        is called BEFORE the Cost is returned; raising from the
        hook propagates to the caller unchanged.
        """
        if shots < 1:
            msg = f"shots must be >= 1; got {shots}"
            raise ValueError(msg)

        seed_entry = pricing_stub.lookup(provider, backend)
        cached = self._load_cache(provider)
        if cached and self._cache_fresh(cached, provider):
            entries = cached.get("entries", {})
            entry = entries.get(backend)
            if entry is None and seed_entry is not None:
                entry = entries.get(seed_entry.backend)
            if entry:
                total, breakdown = pricing_stub.estimate_entry(entry, shots)
                origin = cached.get("origin", "seed")
                cost = Cost(
                    provider=provider, backend=backend, shots=shots,
                    total_usd=total, breakdown=breakdown,
                    free_tier=bool(
                        entry.get("free_minutes_per_month")
                        or entry.get("free_credits_per_month")
                        or entry.get("free_tier"),
                    ),
                    source="live" if origin == "live" else "cache",
                    cache_age_s=self._cache_age_s(cached),
                )
                self._maybe_gate_tenant_budget(cost, tenant_id=tenant_id)
                return cost
        # Fall back to the seed.
        if seed_entry is None:
            msg = f"No pricing for {provider}/{backend}"
            raise KeyError(msg)
        total, breakdown = pricing_stub.estimate_entry(seed_entry.raw, shots)
        cost = Cost(
            provider=provider, backend=backend, shots=shots,
            total_usd=total, breakdown=breakdown,
            free_tier=seed_entry.is_free_tier, source="seed",
        )
        self._maybe_gate_tenant_budget(cost, tenant_id=tenant_id)
        return cost

    def _maybe_gate_tenant_budget(
        self, cost: Cost, *, tenant_id: str | None,
    ) -> None:
        hook = _tenant_budget_hook()
        if hook is None:
            return
        # Free-tier cost doesn't draw from the budget.
        if cost.free_tier:
            return
        hook(tenant_id, cost.total_usd)

    def refresh_live(self, providers: Iterable[str]) -> None:
        """Multi-provider refresh. Never raises.

        Live mode (a ``client_factory`` was injected, or
        ``QCOMPASS_PRICING_LIVE=1``): fetch each provider's endpoint
        over the pinned client and cache the merged entries. A client
        that cannot be built, a network error or a non-2xx response
        writes nothing for that provider; estimates keep using the
        seed.

        Offline mode (default): populate each provider's cache from
        the static seed (no network).
        """
        if not self._live_enabled():
            for provider in providers:
                self.refresh(provider)
            return
        try:
            client = self._client()
        except Exception as exc:  # noqa: BLE001 — _LiveFetchError or other
            logger.warning("pricing: live fetch unavailable (%s)", exc)
            return
        try:
            for provider in providers:
                url = self._endpoints.get(provider)
                if url is None:
                    logger.debug("pricing: no endpoint for %s; skipping", provider)
                    continue
                try:
                    resp = client.get(url)
                    if resp.status_code >= 400:
                        logger.info(
                            "pricing: %s returned status=%s; using seed",
                            provider, resp.status_code,
                        )
                        continue
                    payload = resp.json() if resp.content else {}
                except Exception as exc:  # noqa: BLE001
                    logger.info(
                        "pricing: %s fetch failed (%s); using seed", provider, exc,
                    )
                    continue
                self._save_cache(
                    provider, _merge_live(provider, payload), origin="live",
                )
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                with contextlib.suppress(Exception):
                    close()

    # -- live-fetch internals -------------------------------------------

    def _live_enabled(self) -> bool:
        return self._client_factory is not None or os.environ.get(_LIVE_ENV) == "1"

    def _client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory()
        verify = self._verify_target()
        if isinstance(verify, Path) and not verify.is_file():
            msg = f"CA bundle not found: {verify}"
            raise _LiveFetchError(msg)
        try:
            return ssl_pin.client(ca_bundle=verify, timeout=10.0)
        except ImportError as exc:
            raise _LiveFetchError(str(exc)) from exc

    def _verify_target(self) -> Path | str | bool:
        """Trust root for live fetches: ``ca_bundle``, else certifi,
        else the system default bundle."""
        if self._ca_bundle is not None:
            return self._ca_bundle
        try:
            import certifi  # type: ignore[import-not-found]

            return certifi.where()
        except Exception:  # noqa: BLE001
            return ssl.get_default_verify_paths().cafile or True

    def _cache_fresh(self, cached: dict[str, Any], provider: str | None = None) -> bool:
        if cached.get("origin") == "live" and provider is not None:
            ttl = self._live_ttl.get(provider, self._ttl)
            return (time.time() - float(cached.get("recorded_at_epoch", 0.0))) < ttl
        return super()._cache_fresh(cached)

    @staticmethod
    def _cache_age_s(cached: dict[str, Any]) -> int:
        return max(0, int(time.time() - float(cached.get("recorded_at_epoch", 0.0))))


def _merge_live(provider: str, payload: Any) -> dict[str, dict[str, Any]]:
    """Overlay a live payload's scalar rate keys onto the provider's
    seed entries. Live values win; unknown / non-scalar keys are
    ignored; missing keys fall through to the seed."""
    overrides = {
        k: v
        for k, v in (payload or {}).items()
        if isinstance(v, (int, float, str, bool))
    } if isinstance(payload, dict) else {}
    return {
        backend: {**raw, **overrides}
        for backend, raw in _seed_entries(provider).items()
    }


__all__ = [
    "HOUSE_ACCOUNT",
    "Cost",
    "FreeTierLedger",
    "LivePricing",
    "PricingEngine",
    "set_tenant_budget_hook",
]
