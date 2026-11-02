"""Cost-aware routing policy (PROMPT 6A baseline + PROMPT 6B layers).

One router for both lineages (P0-02 unification of the agent branch
and the router branch). Decision flow:

  0. transforms: explicit ``transforms=[...]`` are applied as asked;
     otherwise, when the circuit's depth exceeds the smallest non-local
     ``device_typical_depth_max`` in the pricing seed, the default
     auto-transform stack (``cutting`` + ``obp``) is applied. The
     records land in ``RoutingDecision.transforms_applied``.
  1. ``budget_usd == 0``:
     - ``require_real_hardware`` → route to a real backend only when a
       free tier in the :class:`FreeTierLedger` covers the job; else
       raise :class:`BudgetExceeded` (code ``BUDGET_EXCEEDED``).
     - else route to ``local_aer``, falling back to ``local_lightning``
       (circuits above :data:`LARGE_CIRCUIT_QUBIT_THRESHOLD` qubits
       prefer ``local_lightning``); none available → ``NO_LOCAL_BACKEND``.
  2. ``budget_usd > 0``:
     - filter by availability, ``preferred_providers``, budget,
       ``min_fidelity``, ``require_real_hardware``, ``max_wallclock_s``.
     - free-tier candidates (ledger coverage, else the seed's free-tier
       flag) win outright in the order IBM Open → IQM Starter → AWS
       Braket → Azure credit, then cost, then fidelity.
     - otherwise rank by ``cost * (2 - fidelity_estimate)``.
     - with a calibration cache, stale candidates rank after fresh
       ones (only when a fresh alternative exists).
  3. calibration gate on the chosen backend: the v1 day-table
     ``check_drift`` and :func:`assert_no_drift` (two-qubit-error drift
     above :data:`DRIFT_THRESHOLD` raises :class:`CalibrationDrift`).

Backends whose descriptors omit fidelity / queue / kind (PROMPT 6A
adapters) get the adapter kind's priors. Adapter price overrides
(``estimate_cost_for``) win over the pricing engine / seed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from . import pricing_stub
from .budget import BudgetExceeded
from .calibration import (
    DRIFT_THRESHOLD,
    CalibrationCache,
    CalibrationDrift,
    assert_no_drift,
)
from .decision import RouterRequest, RoutingDecision, TransformRecord
from .pricing import Cost, FreeTierLedger, PricingEngine
from .providers import ProviderAdapter, list_providers
from .providers.base import BackendInfo
from .transforms import apply_transforms, circuit_depth

# PROMPT 6 v2 §"free-tier preference": IBM Open Plan > IQM Starter
# > AWS Braket simulators > Azure $200 credit > cheapest paid.
_FREE_TIER_ORDER = ("ibm", "iqm", "braket", "azure")

# Above this qubit count budget=0 prefers Lightning over Aer (6A).
LARGE_CIRCUIT_QUBIT_THRESHOLD = 25

# Applied when the circuit is deeper than the device caps (6B).
DEFAULT_AUTO_TRANSFORMS: tuple[str, ...] = ("cutting", "obp")

_LOCAL_PROVIDERS = ("local_aer", "local_lightning")

# Runtime heuristic used for free-tier coverage: 1 ms per shot.
_SECONDS_PER_SHOT = 1e-3

_QASM_QUBIT_RE = re.compile(
    r"^\s*(?:qreg\s+\w+\s*\[\s*(\d+)\s*\]|qubit\s*\[\s*(\d+)\s*\]\s*\w+)\s*;",
    re.MULTILINE,
)


def _qubit_count(qasm: str) -> int:
    """Best-effort qubit-count parse for QASM 2 / OpenQASM 3."""
    total = 0
    for m in _QASM_QUBIT_RE.finditer(qasm or ""):
        n = m.group(1) or m.group(2)
        if n:
            total += int(n)
    return total


@dataclass(frozen=True)
class _Candidate:
    adapter: ProviderAdapter
    info: BackendInfo  # priors resolved: fidelity / queue are floats
    cost: Cost
    free_tier: str | None
    stale: bool

    @property
    def fidelity(self) -> float:
        return float(self.info.fidelity_estimate or 0.0)

    @property
    def queue_s(self) -> float:
        return float(self.info.queue_time_s_estimate or 0.0)


class Router:
    """The qcompass-router decision engine."""

    def __init__(
        self,
        providers: list[ProviderAdapter] | None = None,
        *,
        calibration: CalibrationCache | None = None,
        pricing: PricingEngine | None = None,
        free_tier_ledger: FreeTierLedger | None = None,
        seed_path: Path | None = None,
        auto_transforms: tuple[str, ...] = DEFAULT_AUTO_TRANSFORMS,
    ) -> None:
        self._providers: list[ProviderAdapter] = (
            list(providers) if providers is not None else list_providers()
        )
        package_seed = Path(str(resources.files("qcompass_router.fixtures").joinpath("pricing_seed.yaml")))
        if seed_path is not None and Path(seed_path).resolve() != package_seed.resolve():
            msg = (
                "Router(seed_path=...) only accepts the package pricing seed; "
                "the package seed is the single source of prices (LEDGER P0-02 S2)."
            )
            raise ValueError(msg)
        self._calibration = calibration
        if free_tier_ledger is not None:
            self._ledger = free_tier_ledger
        elif pricing is not None:
            self._ledger = pricing.ledger
        else:
            self._ledger = FreeTierLedger.from_seed()
        # 6B default: a PricingEngine, so routing reads a fresh live/cached
        # price when one exists and falls back to the package seed otherwise.
        # It never fetches live on its own (that needs QCOMPASS_PRICING_LIVE
        # or an injected client_factory, R8).
        self._pricing = pricing if pricing is not None else PricingEngine(ledger=self._ledger)
        self._auto_transforms = tuple(auto_transforms)

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
        return self._ledger

    def decide(
        self,
        req: RouterRequest,
        *,
        circuit: Any | None = None,
        transforms: list[str] | None = None,
        transform_parameters: dict[str, dict[str, Any]] | None = None,
    ) -> RoutingDecision:
        """Pick a backend for ``req``; apply explicit or automatic transforms.

        ``transforms`` is a list of transform names (e.g.
        ``["aqc_tensor", "obp"]``) applied in order to ``circuit`` (or
        to ``req.circuit_qasm`` when no circuit object is given). The
        resulting :class:`TransformRecord` list lands in
        ``RoutingDecision.transforms_applied`` so the caller can
        propagate it into ``ProvenanceRecord.error_mitigation_config``.
        """
        target = circuit if circuit is not None else req.circuit_qasm
        records = self._transform_records(target, transforms, transform_parameters)

        if req.budget_usd <= 0.0:
            decision = self._route_free(req)
        else:
            decision = self._route_paid(req)

        if self._calibration is not None:
            self._calibration.check_drift(decision.provider, decision.backend)

        if records:
            decision = decision.model_copy(update={"transforms_applied": records})
        return decision

    # ── transforms ───────────────────────────────────────────────

    def _transform_records(
        self,
        target: Any,
        transforms: list[str] | None,
        parameters: dict[str, dict[str, Any]] | None,
    ) -> list[TransformRecord]:
        if transforms:
            return apply_transforms(target, transforms, parameters=parameters)[1]
        threshold = _auto_transform_depth_threshold()
        if threshold is None or not self._auto_transforms:
            return []
        if circuit_depth(target) <= threshold:
            return []
        return apply_transforms(target, list(self._auto_transforms))[1]

    # ── budget == 0 ──────────────────────────────────────────────

    def _route_free(self, req: RouterRequest) -> RoutingDecision:
        if req.require_real_hardware:
            decision = self._free_tier_hardware(req)
            if decision is not None:
                return decision
            msg = (
                "budget_usd=0 cannot satisfy require_real_hardware=True "
                "(no free tier covers an available hardware backend); "
                "increase the budget or drop the hardware requirement."
            )
            raise BudgetExceeded(msg)

        large = _qubit_count(req.circuit_qasm) > LARGE_CIRCUIT_QUBIT_THRESHOLD
        order = tuple(reversed(_LOCAL_PROVIDERS)) if large else _LOCAL_PROVIDERS
        for adapter_name in order:
            for adapter in self._providers:
                if adapter.name != adapter_name or not adapter.is_available():
                    continue
                infos = adapter.list_backend_infos()
                if not infos:
                    continue
                pick = infos[0].with_priors(adapter.kind)
                preference = "large-circuit" if large else "small-circuit"
                return RoutingDecision(
                    provider=adapter.name,
                    backend=pick.name,
                    cost_estimate_usd=0.0,
                    queue_time_s_estimate=float(pick.queue_time_s_estimate or 0.0),
                    fidelity_estimate=float(pick.fidelity_estimate or 0.0),
                    transforms_applied=[],
                    reason=(
                        f"budget=0 → {adapter_name} (free / local, "
                        f"{preference} preference)."
                    ),
                )

        msg = (
            "No zero-cost backend is available. Install qcompass-router[ibm] "
            "(qiskit-aer) or qcompass-router[lightning] (pennylane-lightning)."
        )
        raise BudgetExceeded(msg, code="NO_LOCAL_BACKEND")

    def _free_tier_hardware(self, req: RouterRequest) -> RoutingDecision | None:
        """budget=0 + real hardware: allowed only on a covering free tier."""
        runtime_s = req.shots * _SECONDS_PER_SHOT
        for adapter in self._providers:
            if adapter.kind == "local" or not adapter.is_available():
                continue
            for raw in adapter.list_backend_infos():
                info = raw.with_priors(adapter.kind)
                if info.simulator:
                    continue
                if not self._ledger.covers(info.name, runtime_s, req.shots):
                    continue
                tier = self._ledger.tier_for_backend(info.name)
                candidate = _Candidate(
                    adapter=adapter,
                    info=info,
                    cost=Cost(
                        provider=adapter.name, backend=info.name,
                        shots=req.shots, total_usd=0.0, source="seed",
                    ),
                    free_tier=tier,
                    stale=self._is_stale(adapter.name, info.name),
                )
                return self._build_decision(
                    candidate, reason=f"budget=0 → free tier {tier} covers {info.name}.",
                )
        return None

    # ── budget > 0 ──────────────────────────────────────────────

    def _route_paid(self, req: RouterRequest) -> RoutingDecision:
        candidates = list(self._enumerate_candidates(req))
        if not candidates:
            msg = (
                "No backend matched the request. Adjust min_fidelity, "
                "budget_usd or preferred_providers."
            )
            raise BudgetExceeded(msg, code="NO_CANDIDATE_BACKEND")

        any_fresh = any(not c.stale for c in candidates)
        free = [c for c in candidates if c.free_tier is not None]
        if free:
            best = min(
                free,
                key=lambda c: (
                    c.stale and any_fresh,
                    _free_tier_rank(c.adapter.name),
                    c.cost.total_usd,
                    -c.fidelity,
                ),
            )
            reason = (
                f"free-tier preference: {best.free_tier} covers "
                f"{best.adapter.name}/{best.info.name}, fidelity "
                f"{best.fidelity:.3f}."
            )
        else:
            best = min(
                candidates,
                key=lambda c: (
                    c.stale and any_fresh,
                    c.cost.total_usd * (2.0 - c.fidelity),
                    c.queue_s,
                    -c.fidelity,
                ),
            )
            reason = (
                f"{best.adapter.name}/{best.info.name} cost "
                f"${best.cost.total_usd:.4f} ({best.cost.pricing_basis}, "
                f"{best.cost.source}), fidelity {best.fidelity:.3f}, "
                f"queue {int(best.queue_s)} s."
            )
        if best.stale and not any_fresh and self._calibration is not None:
            reason += " (calibration stale for every candidate)"
        return self._build_decision(best, reason=reason)

    # ── helpers ─────────────────────────────────────────────────

    def _enumerate_candidates(self, req: RouterRequest) -> Iterable[_Candidate]:
        preferred = {p.lower() for p in req.preferred_providers}
        runtime_s = req.shots * _SECONDS_PER_SHOT
        for adapter in self._providers:
            # Local adapters are still candidates when budget>0; they
            # cost nothing and so always win on cost. The user can
            # exclude them via preferred_providers if they explicitly
            # want hardware.
            if not adapter.is_available():
                continue
            if preferred and adapter.name.lower() not in preferred:
                continue
            for raw in adapter.list_backend_infos():
                info = raw.with_priors(adapter.kind)
                if req.require_real_hardware and (
                    adapter.kind == "local" or info.simulator
                ):
                    continue
                cost = self._cost_for(adapter, info.name, req.shots)
                if cost.total_usd > req.budget_usd:
                    continue
                if float(info.fidelity_estimate or 0.0) < req.min_fidelity:
                    continue
                if float(info.queue_time_s_estimate or 0.0) > req.max_wallclock_s:
                    continue
                yield _Candidate(
                    adapter=adapter,
                    info=info,
                    cost=cost,
                    free_tier=self._free_tier(adapter, info, runtime_s, req.shots),
                    stale=self._is_stale(adapter.name, info.name),
                )

    def _free_tier(
        self, adapter: ProviderAdapter, info: BackendInfo, runtime_s: float, shots: int,
    ) -> str | None:
        """Ledger tier covering the job; the seed's free-tier flag only
        decides for backends no ledger tier lists."""
        if self._ledger.lists(info.name):
            if self._ledger.covers(info.name, runtime_s, shots):
                return self._ledger.tier_for_backend(info.name)
            return None
        return f"{adapter.name}_free_tier" if info.free_tier else None

    def _is_stale(self, provider: str, backend: str) -> bool:
        if self._calibration is None:
            return False
        return self._calibration.is_stale(provider, backend)

    def _cost_for(self, adapter: ProviderAdapter, backend: str, shots: int) -> Cost:
        """Adapter override → pricing engine → seed → adapter stub."""
        try:
            override = adapter.estimate_cost_for(backend, shots)
        except Exception:  # noqa: BLE001 — fall through to the seed (6A)
            override = None
        if override is not None:
            return Cost(
                provider=adapter.name, backend=backend, shots=shots,
                total_usd=float(override),
                breakdown={"adapter": float(override)} if override else {},
                source="adapter",
            )
        if self._pricing is not None:
            try:
                return self._pricing.estimate(adapter.name, backend, None, shots)
            except KeyError:
                pass
        entry = pricing_stub.lookup(adapter.name, backend)
        if entry is not None:
            total, breakdown = pricing_stub.estimate_entry(entry.raw, shots)
            return Cost(
                provider=adapter.name, backend=backend, shots=shots,
                total_usd=total, breakdown=breakdown,
                free_tier=entry.is_free_tier, source="seed",
            )
        # Backend absent from the seed: the adapter's own stub, else free.
        try:
            stub = float(adapter.estimate_cost_stub(None, shots))
        except Exception:  # noqa: BLE001
            stub = 0.0
        return Cost(
            provider=adapter.name, backend=backend, shots=shots,
            total_usd=stub, source="unpriced",
        )

    def _build_decision(self, candidate: _Candidate, *, reason: str) -> RoutingDecision:
        calibration: dict[str, Any] | None = None
        if self._calibration is not None:
            calibration = assert_no_drift(
                self._calibration,
                candidate.adapter.name,
                candidate.info.name,
                threshold=DRIFT_THRESHOLD,
            )
        if calibration is not None or candidate.free_tier is not None:
            calibration = {
                **(calibration or {}),
                **({"free_tier": candidate.free_tier} if candidate.free_tier else {}),
                "pricing_basis": candidate.cost.pricing_basis,
                "live_pricing": candidate.cost.live,
                "cache_age_s": candidate.cost.cache_age_s,
            }
        return RoutingDecision(
            provider=candidate.adapter.name,
            backend=candidate.info.name,
            cost_estimate_usd=candidate.cost.total_usd,
            queue_time_s_estimate=candidate.queue_s,
            fidelity_estimate=candidate.fidelity,
            transforms_applied=[],
            calibration=calibration,
            reason=reason,
        )


def _auto_transform_depth_threshold() -> int | None:
    """Smallest non-local device depth cap in the seed (conservative)."""
    caps = [
        v for k, v in pricing_stub.device_typical_depth_max().items()
        if k not in _LOCAL_PROVIDERS
    ]
    return min(caps) if caps else None


def _free_tier_rank(provider: str) -> int:
    """Free-tier ordering: IBM Open → IQM Starter → AWS sims → Azure."""
    try:
        return _FREE_TIER_ORDER.index(provider)
    except ValueError:
        return len(_FREE_TIER_ORDER)


__all__ = [
    "DEFAULT_AUTO_TRANSFORMS",
    "LARGE_CIRCUIT_QUBIT_THRESHOLD",
    "BudgetExceeded",
    "CalibrationDrift",
    "Router",
]
