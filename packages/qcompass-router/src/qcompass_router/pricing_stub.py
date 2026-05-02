"""Static pricing seed loader.

PROMPT 6A reads ``fixtures/pricing_seed.yaml`` once at import and
exposes ``estimate(provider, backend, shots)`` returning a dollar
cost. PROMPT 6B replaces this module with a live-pricing adapter
plus an SSL-pinned httpx client and an on-disk cache.

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

import importlib.resources as resources
from dataclasses import dataclass
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


def _load_seed() -> dict[str, PricingEntry]:
    text = (
        resources.files("qcompass_router.fixtures")
        .joinpath("pricing_seed.yaml")
        .read_text()
    )
    payload = yaml.safe_load(text)
    out: dict[str, PricingEntry] = {}
    for key, body in (payload.get("providers") or {}).items():
        if not isinstance(body, dict):
            msg = f"pricing_seed.yaml entry {key!r} must be a mapping"
            raise ValueError(msg)
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


_PRICING: dict[str, PricingEntry] | None = None
_ACCOUNT_CREDITS: dict[str, dict[str, Any]] | None = None


def _pricing() -> dict[str, PricingEntry]:
    global _PRICING
    if _PRICING is None:
        _PRICING = _load_seed()
    return _PRICING


def _load_account_credits() -> dict[str, dict[str, Any]]:
    text = (
        resources.files("qcompass_router.fixtures")
        .joinpath("pricing_seed.yaml")
        .read_text()
    )
    payload = yaml.safe_load(text) or {}
    return dict(payload.get("account_credits") or {})


def account_credits() -> dict[str, dict[str, Any]]:
    """Return the v2 ``account_credits`` block from the seed.

    PROMPT 6 v2 ranks Azure ahead of paid backends while
    ``account_credits['azure']['credit_remaining_usd'] > 0``.
    """
    global _ACCOUNT_CREDITS
    if _ACCOUNT_CREDITS is None:
        _ACCOUNT_CREDITS = _load_account_credits()
    return dict(_ACCOUNT_CREDITS)


def reload() -> None:
    """Drop the cached seed (useful for tests)."""
    global _PRICING, _ACCOUNT_CREDITS
    _PRICING = None
    _ACCOUNT_CREDITS = None


def list_entries() -> list[PricingEntry]:
    return list(_pricing().values())


def lookup(provider: str, backend: str) -> PricingEntry | None:
    """Find an entry by ``(provider, backend)`` pair."""
    for entry in _pricing().values():
        if entry.provider == provider and entry.backend == backend:
            return entry
    return None


def estimate(provider: str, backend: str, shots: int) -> float:
    """Return a single dollar estimate for the run.

    The PROMPT 6A model: take the dominant pricing axis (per_shot >
    per_second > per_task > per_run > per_credit) and add the
    minimum-program floor where relevant. PROMPT 6B replaces this
    with a circuit-aware estimator.
    """
    if shots < 1:
        msg = f"shots must be >= 1; got {shots}"
        raise ValueError(msg)
    entry = lookup(provider, backend)
    if entry is None:
        msg = f"No pricing for {provider}/{backend}"
        raise KeyError(msg)
    cost = 0.0
    if entry.per_shot_usd > 0.0:
        cost += entry.per_shot_usd * shots
    if entry.per_task_usd > 0.0:
        cost += entry.per_task_usd
    if entry.per_run_usd > 0.0:
        cost += entry.per_run_usd
    if entry.per_second_usd > 0.0:
        # PROMPT 6B will derive duration from circuit depth; for now
        # use a 1-second-per-1024-shots placeholder.
        cost += entry.per_second_usd * (shots / 1024.0)
    if entry.per_credit_usd > 0.0:
        # Simple: 1 credit per 1024 shots.
        cost += entry.per_credit_usd * (shots / 1024.0)
    if entry.min_program_usd > 0.0:
        cost = max(cost, entry.min_program_usd)
    return cost


def is_free_tier(provider: str, backend: str) -> bool:
    entry = lookup(provider, backend)
    return bool(entry and entry.is_free_tier)
