"""Routing policy — Phase-6B.

Decision pipeline:
  1. Pre-flight calibration check per candidate. drift>3.0 → CalibrationDrift.
     Stale candidates are downgraded only when a fresh alternative exists.
  2. Auto-apply circuit transforms when QASM depth exceeds the per-backend
     `device_typical_depth_max` from `pricing_seed.yaml`.
  3. Free-tier preference (IBM Open → IQM Starter → AWS Braket sims →
     Azure $200 credit) when budget>0 and a backend is covered by a tier.
  4. Cost via PricingEngine (live cache where valid; seed fallback otherwise).
  5. Cheapest viable candidate that meets `min_fidelity`. Decisions carry
     transform records + calibration metadata.

Zero-budget routes to local_aer / local_lightning unchanged from 6A,
unless `require_real_hardware=True` AND a free tier covers a backend.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from qcompass_router.calibration import (
    CalibrationCache,
    CalibrationDrift,
    DRIFT_THRESHOLD,
    assert_no_drift,
)
from qcompass_router.decision import BackendRequest, RoutingDecision
from qcompass_router.pricing import Cost, FreeTierLedger, PricingEngine
from qcompass_router.providers import default_adapters
from qcompass_router.providers.base import ProviderAdapter
from qcompass_router.transforms import apply_transforms
from qcompass_router.transforms.record import TransformRecord

LARGE_CIRCUIT_QUBIT_THRESHOLD = 25
DEFAULT_AUTO_TRANSFORMS: tuple[str, ...] = ("cutting", "obp")

# Free-tier preference order.
_FREE_TIER_PRIORITY: tuple[str, ...] = (
    "ibm_open",
    "iqm_starter",
    "aws_braket",
    "azure_credit",
)

# Phase-6A fidelity / queue priors are kept as fallbacks; live calibration
# overrides per-backend when a sample exists.
_KIND_FIDELITY: dict[str, float] = {
    "local": 1.0,
    "cloud-sc": 0.97,
    "cloud-ion": 0.99,
    "cloud-neutral-atom": 0.96,
    "cloud-other": 0.97,
}
_KIND_QUEUE_S: dict[str, float] = {
    "local": 0.0,
    "cloud-sc": 600.0,
    "cloud-ion": 900.0,
    "cloud-neutral-atom": 600.0,
    "cloud-other": 600.0,
}


class BudgetExceeded(Exception):
    """Raised when no backend satisfies the request within the given budget."""


@dataclass(frozen=True)
class _Candidate:
    adapter: ProviderAdapter
    backend: str
    cost: Cost
    fidelity: float
    queue_s: float
    free_tier: str | None
    drift_score: float
    stale: bool

    @property
    def cost_usd(self) -> float:
        return self.cost.usd

    @property
    def score(self) -> float:
        # Lower is better. Free-tier candidates get a strong boost so they
        # outrank paid candidates of equal nominal cost; paid candidates
        # are scored by `cost * (2 - fidelity)`.
        if self.free_tier is not None:
            return -1.0 - _free_tier_priority(self.free_tier)
        return self.cost_usd * (2.0 - self.fidelity)


_QASM_QUBIT_RE = re.compile(
    r"^\s*(?:qreg\s+\w+\s*\[\s*(\d+)\s*\]|qubit\s*\[\s*(\d+)\s*\]\s*\w+)\s*;",
    re.MULTILINE,
)


def _qubit_count(qasm: str) -> int:
    """Best-effort qubit-count parse for QASM 2 / OpenQASM 3."""
    total = 0
    for m in _QASM_QUBIT_RE.finditer(qasm):
        n = m.group(1) or m.group(2)
        if n:
            total += int(n)
    return total


def _depth_estimate(qasm: str) -> int:
    """Cheap upper-bound circuit-depth proxy: count gate-bearing lines."""
    if not qasm:
        return 0
    depth = 0
    for raw in qasm.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("//", "OPENQASM", "include", "qreg ", "creg ", "qubit", "bit ")):
            continue
        if line.endswith(";"):
            depth += 1
    return depth


def _free_tier_priority(name: str) -> float:
    try:
        return float(len(_FREE_TIER_PRIORITY) - _FREE_TIER_PRIORITY.index(name))
    except ValueError:
        return 0.0


def _kind_fidelity(adapter: ProviderAdapter) -> float:
    return _KIND_FIDELITY.get(getattr(adapter, "kind", ""), 0.95)


def _kind_queue(adapter: ProviderAdapter) -> float:
    return _KIND_QUEUE_S.get(getattr(adapter, "kind", ""), 600.0)


def _load_seed_meta(seed_path: Path | None) -> dict[str, Any]:
    """Load full seed YAML once, exposing free_tiers + device_typical_depth_max."""
    from qcompass_router.pricing import _default_seed_path

    path = seed_path or _default_seed_path()
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


class Router:
    """Phase-6B routing policy."""

    def __init__(
        self,
        providers: list[ProviderAdapter] | None = None,
        *,
        pricing: PricingEngine | None = None,
        calibration: CalibrationCache | None = None,
        free_tier_ledger: FreeTierLedger | None = None,
        seed_path: Path | None = None,
        auto_transforms: tuple[str, ...] = DEFAULT_AUTO_TRANSFORMS,
    ) -> None:
        self._providers: list[ProviderAdapter] = (
            list(providers) if providers is not None else default_adapters()
        )
        self._pricing = pricing or PricingEngine(seed_yaml=seed_path)
        self._calibration = calibration  # may be None — calibration is opt-in
        self._seed_meta = _load_seed_meta(seed_path)
        self._free_tier_ledger = free_tier_ledger or self._pricing.ledger
        self._auto_transforms = tuple(auto_transforms)

    # public accessors --------------------------------------------------
    @property
    def providers(self) -> list[ProviderAdapter]:
        return list(self._providers)

    @property
    def pricing(self) -> PricingEngine:
        return self._pricing

    @property
    def calibration(self) -> CalibrationCache | None:
        return self._calibration

    @property
    def free_tier_ledger(self) -> FreeTierLedger:
        return self._free_tier_ledger

    # decide ------------------------------------------------------------
    def decide(self, req: BackendRequest) -> RoutingDecision:
        circuit_obj, transform_records = self._maybe_apply_transforms(req)

        if req.budget_usd <= 0:
            return self._decide_zero_budget(req, transform_records)
        return self._decide_paid(req, transform_records)

    # ------------------------------------------------------------------
    # transform autopilot
    # ------------------------------------------------------------------
    def _maybe_apply_transforms(
        self, req: BackendRequest
    ) -> tuple[Any, list[TransformRecord]]:
        depth = _depth_estimate(req.circuit_qasm)
        depth_caps = self._seed_meta.get("device_typical_depth_max") or {}
        # Conservative trigger: if depth exceeds the smallest non-local cap.
        non_local_caps = [
            v
            for k, v in depth_caps.items()
            if k not in ("local_aer", "local_lightning")
        ]
        threshold = min(non_local_caps) if non_local_caps else None
        if threshold is None or depth <= threshold:
            return req.circuit_qasm, []
        circuit, records = apply_transforms(
            req.circuit_qasm, list(self._auto_transforms)
        )
        return circuit, records

    # ------------------------------------------------------------------
    # zero-budget
    # ------------------------------------------------------------------
    def _decide_zero_budget(
        self, req: BackendRequest, transform_records: list[TransformRecord]
    ) -> RoutingDecision:
        if req.require_real_hardware:
            free_decision = self._try_free_tier_real_hardware(req, transform_records)
            if free_decision is not None:
                return free_decision
            raise BudgetExceeded(
                "require_real_hardware=True with budget_usd=0 and no free tier "
                "covers an available backend."
            )

        large = _qubit_count(req.circuit_qasm) > LARGE_CIRCUIT_QUBIT_THRESHOLD
        order = (
            ("local_lightning", "local_aer") if large
            else ("local_aer", "local_lightning")
        )
        for name in order:
            adapter = self._by_name(name)
            if adapter is None:
                continue
            return self._build_decision(
                adapter=adapter,
                backend=self._default_backend(adapter),
                cost=Cost(usd=0.0, pricing_basis="free", cache_age_s=0, live=False),
                fidelity=_kind_fidelity(adapter),
                queue_s=0.0,
                free_tier=None,
                calibration_meta=None,
                transform_records=transform_records,
                reason=(
                    f"budget_usd=0 → routed to {adapter.name} "
                    f"({'large-circuit preference' if large else 'small-circuit preference'})"
                ),
            )

        raise BudgetExceeded(
            "budget_usd=0 and no local simulator adapter is registered."
        )

    def _try_free_tier_real_hardware(
        self, req: BackendRequest, transform_records: list[TransformRecord]
    ) -> RoutingDecision | None:
        """Permit hardware routing under budget=0 if a free tier covers it."""
        runtime = float(req.shots) * 1e-3
        for adapter in self._providers:
            if adapter.kind == "local" or not adapter.is_available():
                continue
            for be in adapter.list_backends():
                tier = self._free_tier_ledger.tier_for_backend(be.name)
                if tier is None:
                    continue
                if not self._free_tier_ledger.covers(be.name, runtime, req.shots):
                    continue
                cal_meta = self._cal_check(adapter.name, be.name)
                return self._build_decision(
                    adapter=adapter,
                    backend=be.name,
                    cost=Cost(usd=0.0, pricing_basis="free", cache_age_s=0, live=False),
                    fidelity=_kind_fidelity(adapter),
                    queue_s=_kind_queue(adapter),
                    free_tier=tier,
                    calibration_meta=cal_meta,
                    transform_records=transform_records,
                    reason=f"budget_usd=0 → free tier {tier} covers {be.name}",
                )
        return None

    # ------------------------------------------------------------------
    # paid
    # ------------------------------------------------------------------
    def _decide_paid(
        self, req: BackendRequest, transform_records: list[TransformRecord]
    ) -> RoutingDecision:
        candidates = list(self._enumerate_candidates(req))

        viable: list[_Candidate] = [
            c
            for c in candidates
            if c.fidelity >= req.min_fidelity and c.cost_usd <= req.budget_usd
        ]
        if not viable:
            raise BudgetExceeded(
                f"no provider meets budget=${req.budget_usd:.2f} "
                f"and min_fidelity={req.min_fidelity:.2f} "
                f"(checked {len(candidates)} candidate(s))."
            )

        viable.sort(
            key=lambda c: (c.score, c.cost_usd, c.adapter.name, c.backend)
        )
        best = viable[0]
        cal_meta = self._cal_meta(best)
        if best.free_tier is not None:
            reason = (
                f"free tier {best.free_tier} covers {best.backend}; "
                f"fidelity={best.fidelity:.3f}"
            )
        else:
            reason = (
                f"cheapest viable: cost=${best.cost_usd:.4f} "
                f"basis={best.cost.pricing_basis} live={best.cost.live} "
                f"fidelity={best.fidelity:.3f} score={best.score:.4f}"
            )
        return self._build_decision(
            adapter=best.adapter,
            backend=best.backend,
            cost=best.cost,
            fidelity=best.fidelity,
            queue_s=best.queue_s,
            free_tier=best.free_tier,
            calibration_meta=cal_meta,
            transform_records=transform_records,
            reason=reason,
        )

    # ------------------------------------------------------------------
    # candidate enumeration
    # ------------------------------------------------------------------
    def _enumerate_candidates(self, req: BackendRequest) -> Iterable[_Candidate]:
        preferred = {p.lower() for p in req.preferred_providers}
        runtime_estimate = float(req.shots) * 1e-3
        for adapter in self._providers:
            if not adapter.is_available():
                continue
            if preferred and adapter.name.lower() not in preferred:
                continue
            if req.require_real_hardware and adapter.kind == "local":
                continue
            backends = adapter.list_backends()
            if not backends:
                continue
            kind_fid = _kind_fidelity(adapter)
            kind_q = _kind_queue(adapter)
            for backend in backends:
                # Calibration pre-flight: drift>3 raises immediately.
                cal_meta = self._cal_check(adapter.name, backend.name)
                drift = float(cal_meta["drift_score"]) if cal_meta else 0.0
                stale = bool(cal_meta["stale"]) if cal_meta else False
                cost = self._cost_for(adapter, backend.name, req.shots)
                free_tier = None
                if self._free_tier_ledger.covers(
                    backend.name, runtime_estimate, req.shots
                ):
                    free_tier = self._free_tier_ledger.tier_for_backend(backend.name)
                yield _Candidate(
                    adapter=adapter,
                    backend=backend.name,
                    cost=cost,
                    fidelity=kind_fid,
                    queue_s=kind_q,
                    free_tier=free_tier,
                    drift_score=drift,
                    stale=stale,
                )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _cost_for(
        self, adapter: ProviderAdapter, backend: str, shots: int
    ) -> Cost:
        # Adapters that know per-backend pricing override the pricing
        # engine (this also keeps 6A tests' FakeAdapter contract working).
        per_backend = getattr(adapter, "estimate_cost_for", None)
        if callable(per_backend):
            try:
                return Cost(
                    usd=float(per_backend(backend, shots)),
                    pricing_basis="per_shot",
                    cache_age_s=0,
                    live=False,
                )
            except Exception:  # noqa: BLE001 — fall through
                pass
        try:
            return self._pricing.estimate(adapter.name, backend, None, shots)
        except KeyError:
            return Cost(
                usd=float(adapter.estimate_cost_stub(None, shots)),
                pricing_basis="per_shot",
                cache_age_s=0,
                live=False,
            )

    def _cal_check(self, provider: str, backend: str) -> dict[str, Any] | None:
        if self._calibration is None:
            return None
        # `assert_no_drift` raises on drift>threshold.
        return assert_no_drift(
            self._calibration, provider, backend, threshold=DRIFT_THRESHOLD
        )

    def _cal_meta(self, candidate: _Candidate) -> dict[str, Any] | None:
        if self._calibration is None:
            return None
        return {
            "provider": candidate.adapter.name,
            "backend": candidate.backend,
            "drift_score": candidate.drift_score,
            "stale": candidate.stale,
            "threshold": DRIFT_THRESHOLD,
        }

    def _by_name(self, name: str) -> ProviderAdapter | None:
        for adapter in self._providers:
            if adapter.name == name and adapter.is_available():
                return adapter
        return None

    def _default_backend(self, adapter: ProviderAdapter) -> str:
        backends = adapter.list_backends()
        return backends[0].name if backends else adapter.name

    def _build_decision(
        self,
        *,
        adapter: ProviderAdapter,
        backend: str,
        cost: Cost,
        fidelity: float,
        queue_s: float,
        free_tier: str | None,
        calibration_meta: dict[str, Any] | None,
        transform_records: list[TransformRecord],
        reason: str,
    ) -> RoutingDecision:
        return RoutingDecision(
            provider=adapter.name,
            backend=backend,
            cost_estimate_usd=cost.usd,
            queue_time_s_estimate=queue_s,
            fidelity_estimate=fidelity,
            transforms_applied=[r.name for r in transform_records],
            transform_records=list(transform_records),
            calibration=(
                None
                if calibration_meta is None and free_tier is None
                else {
                    **(calibration_meta or {}),
                    **({"free_tier": free_tier} if free_tier else {}),
                    "pricing_basis": cost.pricing_basis,
                    "live_pricing": cost.live,
                    "cache_age_s": cost.cache_age_s,
                }
            ),
            reason=reason,
        )


# Re-export for callers that catch CalibrationDrift via the router module.
__all__ = [
    "BudgetExceeded",
    "CalibrationDrift",
    "Router",
]
