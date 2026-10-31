"""Static pricing seed loader.

Reads ``qcompass_router/fixtures/pricing_seed.yaml`` lazily and
exposes ``estimate(provider, backend, shots)`` returning a dollar
cost. :class:`qcompass_router.pricing.PricingEngine` layers the live
cache + SSL-pinned refresh on top and reuses :func:`estimate_entry`
(the package's one pricing formula).

The seed is the single source of truth for pricing, free tiers
(``free_tiers:``), device depth caps (``device_typical_depth_max:``)
and account credits (``account_credits:``).

Schema invariants (enforced when parsing):
- Each entry under ``providers:`` has ``provider``, ``backend``,
  ``fidelity_estimate``, ``queue_time_s_estimate``.
- At least one of ``per_second_usd``, ``per_shot_usd``,
  ``per_task_usd``, ``per_credit_usd``, ``hqc_per_circuit``,
  ``per_run_usd``, ``min_program_usd`` is present.
- ``free_*_per_month`` is optional and surfaces via
  :func:`is_free_tier`.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml


@dataclass(frozen=True)
class PricingEntry:
    """Parsed pricing-seed entry for a single backend."""

    key: str
    provider: str
    backend: str
    fidelity_estimate: float
    queue_time_s_estimate: float
    raw: dict[str, Any]

    @property
    def is_free_tier(self) -> bool:
        # PROMPT 6 v2 adds the explicit boolean `free_tier` key for
        # one-shot credits like Azure's $200 starter (no monthly
        # allowance to count). v1's free_minutes / free_credits keys
        # still mark free-tier for IBM Open Plan + IQM Starter.
        if self.raw.get("free_tier") is True:
            return True
        return any(
            k in self.raw
            for k in ("free_minutes_per_month", "free_credits_per_month")
        )

    @property
    def per_shot_usd(self) -> float:
        return float(self.raw.get("per_shot_usd", 0.0))

    @property
    def per_task_usd(self) -> float:
        return float(self.raw.get("per_task_usd", 0.0))

    @property
    def per_second_usd(self) -> float:
        return float(self.raw.get("per_second_usd", 0.0))

    @property
    def per_credit_usd(self) -> float:
        return float(self.raw.get("per_credit_usd", 0.0))

    @property
    def per_run_usd(self) -> float:
        return float(self.raw.get("per_run_usd", 0.0))

    @property
    def min_program_usd(self) -> float:
        return float(self.raw.get("min_program_usd", 0.0))


_PAYLOAD: dict[str, Any] | None = None
_PRICING: dict[str, PricingEntry] | None = None
_ACCOUNT_CREDITS: dict[str, dict[str, Any]] | None = None


def seed_payload() -> dict[str, Any]:
    """Return the whole parsed seed YAML (cached until :func:`reload`)."""
    global _PAYLOAD
    if _PAYLOAD is None:
        text = (
            resources.files("qcompass_router.fixtures")
            .joinpath("pricing_seed.yaml")
            .read_text()
        )
        _PAYLOAD = yaml.safe_load(text) or {}
    return _PAYLOAD


def _load_seed() -> dict[str, PricingEntry]:
    out: dict[str, PricingEntry] = {}
    for key, body in (seed_payload().get("providers") or {}).items():
        if not isinstance(body, dict):
            msg = f"pricing_seed.yaml entry {key!r} must be a mapping"
            raise ValueError(msg)  # noqa: TRY004 - ValueError is the seed loader's documented contract
        for required in ("provider", "backend", "fidelity_estimate",
                         "queue_time_s_estimate"):
            if required not in body:
                msg = (
                    f"pricing_seed.yaml entry {key!r} missing required "
                    f"field {required!r}"
                )
                raise ValueError(msg)
        out[key] = PricingEntry(
            key=key,
            provider=str(body["provider"]),
            backend=str(body["backend"]),
            fidelity_estimate=float(body["fidelity_estimate"]),
            queue_time_s_estimate=float(body["queue_time_s_estimate"]),
            raw=body,
        )
    return out


def _pricing() -> dict[str, PricingEntry]:
    global _PRICING
    if _PRICING is None:
        _PRICING = _load_seed()
    return _PRICING


def account_credits() -> dict[str, dict[str, Any]]:
    """Return the v2 ``account_credits`` block from the seed.

    PROMPT 6 v2 ranks Azure ahead of paid backends while
    ``account_credits['azure']['credit_remaining_usd'] > 0``.
    """
    global _ACCOUNT_CREDITS
    if _ACCOUNT_CREDITS is None:
        _ACCOUNT_CREDITS = dict(seed_payload().get("account_credits") or {})
    return dict(_ACCOUNT_CREDITS)


def free_tiers() -> dict[str, dict[str, Any]]:
    """Return the ``free_tiers`` block (seeds :class:`FreeTierLedger`)."""
    return dict(seed_payload().get("free_tiers") or {})


def device_typical_depth_max() -> dict[str, int]:
    """Return the per-device typical max depth (auto-transform trigger)."""
    return {
        str(k): int(v)
        for k, v in (seed_payload().get("device_typical_depth_max") or {}).items()
    }


def reload() -> None:
    """Drop the cached seed (useful for tests)."""
    global _PRICING, _ACCOUNT_CREDITS, _PAYLOAD
    _PRICING = None
    _ACCOUNT_CREDITS = None
    _PAYLOAD = None


def list_entries() -> list[PricingEntry]:
    return list(_pricing().values())


def lookup(provider: str, backend: str) -> PricingEntry | None:
    """Find the seed entry for ``(provider, backend)``.

    Resolution order (first hit wins):

    1. an entry whose ``provider`` and ``backend`` both match;
    2. the seed key ``"<provider>_<backend>"`` (PROMPT 6A keys such as
       ``braket_ionq_aria``);
    3. the seed key ``"<backend>"`` when that entry belongs to
       ``provider``;
    4. only when ``backend`` is empty (the caller did not pin one):
       the seed key ``"<provider>"``, else the provider's first entry.

    Unknown pairs return None. Step 3 checks the provider so a backend
    name never borrows another provider's price.
    """
    entries = _pricing()
    for entry in entries.values():
        if entry.provider == provider and entry.backend == backend:
            return entry
    if backend:
        keyed = entries.get(f"{provider}_{backend}")
        if keyed is not None:
            return keyed
        by_backend = entries.get(backend)
        if by_backend is not None and by_backend.provider == provider:
            return by_backend
        return None
    by_provider = entries.get(provider)
    if by_provider is not None:
        return by_provider
    for entry in entries.values():
        if entry.provider == provider:
            return entry
    return None


def estimate_entry(
    raw: dict[str, Any], shots: int,
) -> tuple[float, dict[str, float]]:
    """Dollar estimate + per-axis breakdown for one seed / cache entry.

    - ``per_shot_usd`` x shots, ``per_task_usd``, ``per_run_usd``;
    - ``per_second_usd`` x shots/1024 (1 s per 1024 shots placeholder);
    - ``per_credit_usd`` x shots/1024 (1 credit per 1024 shots);
    - ``per_1q_shot_usd`` (else ``per_2q_shot_usd``) x shots — Azure
      gate-shot pricing without gate counting;
    - ``hqc_per_circuit`` x ``hqc_overage_usd`` — Quantinuum HQCs;
    - ``min_program_usd`` floors the total.
    """
    breakdown: dict[str, float] = {}

    def _rate(key: str) -> float:
        return float(raw.get(key) or 0.0)

    def _add(axis: str, value: float) -> None:
        if value:
            breakdown[axis] = value

    _add("per_shot", _rate("per_shot_usd") * shots)
    _add("per_task", _rate("per_task_usd"))
    _add("per_run", _rate("per_run_usd"))
    _add("per_second", _rate("per_second_usd") * (shots / 1024.0))
    _add("per_credit", _rate("per_credit_usd") * (shots / 1024.0))
    gate_shot = _rate("per_1q_shot_usd") or _rate("per_2q_shot_usd")
    _add("per_gate_shot", gate_shot * shots)
    _add("per_circuit", _rate("hqc_per_circuit") * _rate("hqc_overage_usd"))
    cost = sum(breakdown.values())
    floor = _rate("min_program_usd")
    if floor and cost < floor:
        breakdown["min_program_floor"] = floor - cost
        cost = floor
    return cost, breakdown


def estimate(provider: str, backend: str, shots: int) -> float:
    """Return a single dollar estimate for ``shots`` on the pair.

    Raises ``ValueError`` for ``shots < 1`` and ``KeyError`` when the
    seed has no entry for the pair (see :func:`lookup`).
    """
    if shots < 1:
        msg = f"shots must be >= 1; got {shots}"
        raise ValueError(msg)
    entry = lookup(provider, backend)
    if entry is None:
        msg = f"No pricing for {provider}/{backend}"
        raise KeyError(msg)
    return estimate_entry(entry.raw, shots)[0]


def is_free_tier(provider: str, backend: str) -> bool:
    entry = lookup(provider, backend)
    return bool(entry and entry.is_free_tier)
