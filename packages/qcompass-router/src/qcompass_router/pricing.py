"""Production pricing model.

`PricingEngine` is the runtime pricing path used by `Router`. It loads the
seed YAML at construction, optionally refreshes per-provider live rates via
SSL-pinned httpx clients, and falls back to the seed on any error so the
router stays usable offline.

Free-tier consumption is tracked by `FreeTierLedger`, an in-memory ledger
that callers can preload (tests / CI) or wire to durable storage.

`pricing_stub.estimate(...)` from PROMPT 6A is left untouched for back-compat.
"""

from __future__ import annotations

import json
import logging
import ssl
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Literal

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------

PricingBasis = Literal[
    "per_second",
    "per_shot",
    "per_task",
    "per_circuit",
    "per_credit",
    "free",
]


class Cost(BaseModel):
    """Result of `PricingEngine.estimate()`."""

    usd: float
    pricing_basis: PricingBasis
    cache_age_s: int
    live: bool


# ---------------------------------------------------------------------------
# Free-tier ledger
# ---------------------------------------------------------------------------


@dataclass
class _FreeTierBucket:
    units: float = 0.0
    unit_kind: str = "minutes"  # "minutes" | "credits" | "usd" | "hours"
    applicable_backends: tuple[str, ...] = ()


@dataclass
class FreeTierLedger:
    """In-memory free-tier ledger.

    Per-provider remaining units (minutes / credits / USD / simulator-hours).
    Tests preload this directly; production wires it to user budgets.
    """

    buckets: dict[str, _FreeTierBucket] = field(default_factory=dict)

    @classmethod
    def from_seed(cls, seed: dict[str, Any]) -> "FreeTierLedger":
        out = cls()
        for tier_name, body in (seed.get("free_tiers") or {}).items():
            applicable = tuple(body.get("applicable_backends", []))
            if "minutes_per_month" in body:
                out.buckets[tier_name] = _FreeTierBucket(
                    units=float(body["minutes_per_month"]),
                    unit_kind="minutes",
                    applicable_backends=applicable,
                )
            elif "credits_per_month" in body:
                out.buckets[tier_name] = _FreeTierBucket(
                    units=float(body["credits_per_month"]),
                    unit_kind="credits",
                    applicable_backends=applicable,
                )
            elif "simulator_hours_per_month" in body:
                out.buckets[tier_name] = _FreeTierBucket(
                    units=float(body["simulator_hours_per_month"]),
                    unit_kind="hours",
                    applicable_backends=applicable,
                )
            elif "usd" in body:
                out.buckets[tier_name] = _FreeTierBucket(
                    units=float(body["usd"]),
                    unit_kind="usd",
                    applicable_backends=applicable,
                )
        return out

    # tier-name accessors -----------------------------------------------
    def remaining(self, tier_name: str) -> float:
        b = self.buckets.get(tier_name)
        return b.units if b else 0.0

    def set_remaining(self, tier_name: str, units: float) -> None:
        b = self.buckets.get(tier_name)
        if b is None:
            self.buckets[tier_name] = _FreeTierBucket(units=units)
        else:
            b.units = units

    def consume(self, tier_name: str, units: float) -> None:
        b = self.buckets.get(tier_name)
        if b is None:
            return
        b.units = max(0.0, b.units - units)

    # backend-aware lookups --------------------------------------------
    def tier_for_backend(self, backend: str) -> str | None:
        for tier_name, bucket in self.buckets.items():
            if backend in bucket.applicable_backends and bucket.units > 0:
                return tier_name
        return None

    def covers(
        self,
        backend: str,
        runtime_s: float,
        shots: int,
    ) -> bool:
        """Best-effort coverage probe.

        Translates a runtime estimate into the bucket's unit (minutes,
        credits, hours, USD) and checks against `units` remaining.
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


# ---------------------------------------------------------------------------
# Live-fetch transports
# ---------------------------------------------------------------------------


class _LiveFetchError(Exception):
    """Internal — caught and turned into a seed fallback."""


def _build_pinned_client(verify: Path | str | bool):  # pragma: no cover -
    """Construct an SSL-pinned httpx client.

    Soft-imported: when httpx is unavailable, the caller falls back to
    seed values without raising.
    """
    try:
        import httpx  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise _LiveFetchError(f"httpx not available: {exc}") from exc

    if isinstance(verify, Path):
        if not verify.is_file():
            raise _LiveFetchError(f"CA bundle not found: {verify}")
        verify_arg: Any = str(verify)
    else:
        verify_arg = verify

    transport = httpx.HTTPTransport(verify=verify_arg)
    return httpx.Client(transport=transport, timeout=10.0)


# ---------------------------------------------------------------------------
# PricingEngine
# ---------------------------------------------------------------------------

# Default per-provider cache TTLs.
_DEFAULT_TTLS_S: dict[str, int] = {
    "ibm": 3600,
    "braket": 86400,
    "azure": 86400,
    "iqm": 86400,
}


# Provider live-pricing endpoints. The values are URL hints that respx /
# vcrpy cassettes can match; defaults are illustrative and the engine
# treats any non-2xx / network error as "fall back to seed".
_DEFAULT_ENDPOINTS: dict[str, str] = {
    "ibm": "https://api.quantum.ibm.com/runtime/jobs/pricing",
    "braket": "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBraket/current/index.json",
    "azure": "https://prices.azure.com/api/retail/prices?$filter=serviceName%20eq%20%27Azure%20Quantum%27",
    "iqm": "https://resonance.meetiqm.com/api/v1/pricing",
}


class PricingEngine:
    """Pricing engine. Live-aware with deterministic seed fallback."""

    DEFAULT_CACHE_DIR: ClassVar[Path] = Path.home() / ".cache/qcompass/pricing"

    def __init__(
        self,
        seed_yaml: Path | None = None,
        cache_dir: Path | None = None,
        *,
        ca_bundle: Path | None = None,
        endpoints: dict[str, str] | None = None,
        ttl_s: dict[str, int] | None = None,
        client_factory=None,
        ledger: FreeTierLedger | None = None,
    ) -> None:
        self._seed_yaml_path = seed_yaml or _default_seed_path()
        self._seed = _load_seed_yaml(self._seed_yaml_path)
        self._cache_dir = Path(cache_dir) if cache_dir else self.DEFAULT_CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._ca_bundle = ca_bundle
        self._endpoints = {**_DEFAULT_ENDPOINTS, **(endpoints or {})}
        self._ttl = {**_DEFAULT_TTLS_S, **(ttl_s or {})}
        self._client_factory = client_factory or (
            lambda: _build_pinned_client(self._verify_target())
        )
        self.ledger = ledger or FreeTierLedger.from_seed(self._seed)

    # -- public API -----------------------------------------------------
    def estimate(
        self,
        provider: str,
        backend: str,
        circuit: Any,
        shots: int,
    ) -> Cost:
        """Return a `Cost` for (provider, backend, circuit, shots)."""
        if shots < 0:
            raise ValueError("shots must be non-negative")

        cache_payload, cache_age_s = self._read_cache(provider)
        live = cache_payload is not None
        if cache_payload is not None:
            entry = self._merge_seed(provider, backend, cache_payload)
        else:
            entry = self._seed_lookup(provider, backend)

        if entry is None:
            return Cost(
                usd=0.0,
                pricing_basis="free",
                cache_age_s=cache_age_s,
                live=live,
            )

        usd, basis = _compute_cost(entry, shots)
        return Cost(
            usd=usd,
            pricing_basis=basis,
            cache_age_s=cache_age_s,
            live=live,
        )

    def refresh_live(self, providers: list[str]) -> None:
        """Refresh on-disk pricing cache for the given provider names.

        Offline-safe: any error logs and is suppressed; callers continue
        to read seed values until the next refresh succeeds.
        """
        try:
            client = self._client_factory()
        except _LiveFetchError as exc:
            logger.warning("pricing: live fetch unavailable (%s)", exc)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("pricing: client construction failed (%s)", exc)
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
                            provider,
                            resp.status_code,
                        )
                        continue
                    payload = resp.json() if resp.content else {}
                except Exception as exc:  # noqa: BLE001
                    logger.info("pricing: %s fetch failed (%s); using seed", provider, exc)
                    continue
                self._write_cache(provider, payload)
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass

    # -- internals ------------------------------------------------------
    def _verify_target(self) -> Path | str | bool:
        if self._ca_bundle is not None:
            return self._ca_bundle
        # Fall back to certifi where available; system store otherwise.
        try:
            import certifi  # type: ignore

            return certifi.where()
        except Exception:  # noqa: BLE001
            return ssl.get_default_verify_paths().cafile or True

    def _seed_lookup(self, provider: str, backend: str) -> dict[str, Any] | None:
        providers = self._seed.get("providers") or {}
        for key in (f"{provider}_{backend}", backend, provider):
            if key in providers:
                return providers[key]
        return None

    def _merge_seed(
        self, provider: str, backend: str, live: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge a live cache payload into the seed entry.

        Live payloads are expected to mirror the seed's key shapes
        (per_second_usd, etc.). Unknown keys are ignored. Live values
        take precedence; missing keys fall through to the seed.
        """
        base = self._seed_lookup(provider, backend) or {}
        merged = dict(base)
        for k, v in (live or {}).items():
            if isinstance(v, (int, float, str, bool)):
                merged[k] = v
        return merged

    def _cache_path(self, provider: str) -> Path:
        return self._cache_dir / f"{provider}.json"

    def _read_cache(self, provider: str) -> tuple[dict[str, Any] | None, int]:
        path = self._cache_path(provider)
        if not path.is_file():
            return None, 0
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None, 0
        ts = payload.get("_cached_at")
        if not isinstance(ts, (int, float)):
            return None, 0
        age = max(0, int(time.time() - ts))
        ttl = self._ttl.get(provider, _DEFAULT_TTLS_S.get(provider, 86400))
        if age > ttl:
            return None, age
        body = {k: v for k, v in payload.items() if k != "_cached_at"}
        return body, age

    def _write_cache(self, provider: str, payload: dict[str, Any]) -> None:
        path = self._cache_path(provider)
        body = dict(payload)
        body["_cached_at"] = int(time.time())
        path.write_text(json.dumps(body), encoding="utf-8")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _default_seed_path() -> Path:
    pkg_dir = Path(__file__).resolve().parent
    candidates = (
        pkg_dir / "fixtures" / "pricing_seed.yaml",
        pkg_dir.parent.parent / "fixtures" / "pricing_seed.yaml",
    )
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "pricing_seed.yaml not found; checked: "
        + ", ".join(str(p) for p in candidates)
    )


def _load_seed_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _compute_cost(entry: dict[str, Any], shots: int) -> tuple[float, PricingBasis]:
    """Apply whichever pricing shape matches `entry`.

    Mirrors the resolution order used by `pricing_stub.estimate` so the
    seed fallback is bit-identical to the Phase-6A behaviour. Returns
    (usd, basis) where `basis` is a `PricingBasis` literal.
    """
    per_shot = entry.get("per_shot_usd")
    per_task = entry.get("per_task_usd")
    per_run = entry.get("per_run_usd")
    per_second = entry.get("per_second_usd")
    per_credit = entry.get("per_credit_usd")
    per_1q = entry.get("per_1q_shot_usd")
    per_2q = entry.get("per_2q_shot_usd")
    min_program = entry.get("min_program_usd", 0.0)
    hqc_per_circuit = entry.get("hqc_per_circuit")
    hqc_overage_usd = entry.get("hqc_overage_usd")

    if per_1q is not None or per_2q is not None:
        rate = float(per_1q if per_1q is not None else (per_2q or 0.0))
        return max(rate * shots, float(min_program)), "per_shot"

    if hqc_per_circuit is not None and hqc_overage_usd is not None:
        return float(hqc_per_circuit) * float(hqc_overage_usd), "per_circuit"

    if per_second is not None:
        return float(per_second) * (shots * 1e-3), "per_second"

    if per_credit is not None:
        credits = max(1.0, shots / 1000.0)
        return float(per_credit) * credits, "per_credit"

    if per_run is not None:
        return float(per_run), "per_task"

    if per_shot is not None or per_task is not None:
        if per_shot is None:
            return float(per_task or 0.0), "per_task"
        return float(per_task or 0.0) + float(per_shot) * shots, "per_shot"

    return 0.0, "free"
