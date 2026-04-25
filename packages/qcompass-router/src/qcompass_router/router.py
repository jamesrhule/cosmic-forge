"""Routing policy. Phase-6A baseline.

Decision rules (this phase):
  1. budget_usd == 0:
       * require_real_hardware → BudgetExceeded
       * else → local_aer (preferred) or local_lightning for large circuits
  2. budget_usd > 0:
       * filter providers by `is_available()` + `preferred_providers`
       * score each candidate by `cost_stub * (2 - fidelity_estimate)`
       * return the cheapest candidate that meets `min_fidelity`
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from qcompass_router.decision import BackendRequest, RoutingDecision
from qcompass_router.providers import default_adapters
from qcompass_router.providers.base import ProviderAdapter

# Above this qubit count we prefer Lightning (GPU/Kokkos) over Aer.
LARGE_CIRCUIT_QUBIT_THRESHOLD = 25

# Phase-6A fidelity priors, by provider kind. Phase-6B replaces these
# with calibration-derived numbers.
_KIND_FIDELITY: dict[str, float] = {
    "local": 1.0,
    "cloud-sc": 0.97,
    "cloud-ion": 0.99,
    "cloud-neutral-atom": 0.96,
    "cloud-other": 0.97,
}

# Phase-6A queue priors (seconds). Phase-6B uses live queue lengths.
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
    cost: float
    fidelity: float
    queue_s: float

    @property
    def score(self) -> float:
        # Lower is better. Higher fidelity → smaller multiplier.
        return self.cost * (2.0 - self.fidelity)


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


def _kind_fidelity(adapter: ProviderAdapter) -> float:
    return _KIND_FIDELITY.get(getattr(adapter, "kind", ""), 0.95)


def _kind_queue(adapter: ProviderAdapter) -> float:
    return _KIND_QUEUE_S.get(getattr(adapter, "kind", ""), 600.0)


class Router:
    """Phase-6A routing policy."""

    def __init__(self, providers: list[ProviderAdapter] | None = None) -> None:
        self._providers: list[ProviderAdapter] = (
            list(providers) if providers is not None else default_adapters()
        )

    @property
    def providers(self) -> list[ProviderAdapter]:
        return list(self._providers)

    # ------------------------------------------------------------------
    # decide
    # ------------------------------------------------------------------
    def decide(self, req: BackendRequest) -> RoutingDecision:
        if req.budget_usd <= 0:
            return self._decide_zero_budget(req)
        return self._decide_paid(req)

    # ------------------------------------------------------------------
    # zero-budget
    # ------------------------------------------------------------------
    def _decide_zero_budget(self, req: BackendRequest) -> RoutingDecision:
        if req.require_real_hardware:
            raise BudgetExceeded(
                "require_real_hardware=True with budget_usd=0; "
                "real hardware always costs money in Phase-6A."
            )

        large = _qubit_count(req.circuit_qasm) > LARGE_CIRCUIT_QUBIT_THRESHOLD
        order = ("local_lightning", "local_aer") if large else ("local_aer", "local_lightning")
        for name in order:
            adapter = self._by_name(name)
            if adapter is None:
                continue
            return RoutingDecision(
                provider=adapter.name,
                backend=self._default_backend(adapter),
                cost_estimate_usd=0.0,
                queue_time_s_estimate=0.0,
                fidelity_estimate=_kind_fidelity(adapter),
                transforms_applied=[],
                reason=(
                    f"budget_usd=0 → routed to {adapter.name} "
                    f"({'large-circuit preference' if large else 'small-circuit preference'})"
                ),
            )

        raise BudgetExceeded(
            "budget_usd=0 and no local simulator adapter is registered."
        )

    # ------------------------------------------------------------------
    # paid
    # ------------------------------------------------------------------
    def _decide_paid(self, req: BackendRequest) -> RoutingDecision:
        candidates = list(self._enumerate_candidates(req))

        # Filter to those meeting min_fidelity AND budget.
        viable: list[_Candidate] = [
            c
            for c in candidates
            if c.fidelity >= req.min_fidelity and c.cost <= req.budget_usd
        ]
        if not viable:
            raise BudgetExceeded(
                f"no provider meets budget=${req.budget_usd:.2f} "
                f"and min_fidelity={req.min_fidelity:.2f} "
                f"(checked {len(candidates)} candidate(s))."
            )

        viable.sort(key=lambda c: (c.score, c.cost, c.adapter.name, c.backend))
        best = viable[0]
        return RoutingDecision(
            provider=best.adapter.name,
            backend=best.backend,
            cost_estimate_usd=best.cost,
            queue_time_s_estimate=best.queue_s,
            fidelity_estimate=best.fidelity,
            transforms_applied=[],
            reason=(
                f"cheapest viable: cost=${best.cost:.4f} "
                f"fidelity={best.fidelity:.3f} score={best.score:.4f}"
            ),
        )

    # ------------------------------------------------------------------
    # candidate enumeration
    # ------------------------------------------------------------------
    def _enumerate_candidates(
        self, req: BackendRequest
    ) -> Iterable[_Candidate]:
        preferred = {p.lower() for p in req.preferred_providers}
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
                cost = self._cost_for(adapter, backend.name, req.shots)
                yield _Candidate(
                    adapter=adapter,
                    backend=backend.name,
                    cost=cost,
                    fidelity=kind_fid,
                    queue_s=kind_q,
                )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _cost_for(
        self, adapter: ProviderAdapter, backend: str, shots: int
    ) -> float:
        # Adapters that know per-backend pricing expose `estimate_cost_for`;
        # otherwise fall back to the generic stub.
        per_backend = getattr(adapter, "estimate_cost_for", None)
        if callable(per_backend):
            try:
                return float(per_backend(backend, shots))
            except Exception:  # noqa: BLE001 — fall through to stub
                pass
        return float(adapter.estimate_cost_stub(None, shots))

    def _by_name(self, name: str) -> ProviderAdapter | None:
        for adapter in self._providers:
            if adapter.name == name and adapter.is_available():
                return adapter
        return None

    def _default_backend(self, adapter: ProviderAdapter) -> str:
        backends = adapter.list_backends()
        return backends[0].name if backends else adapter.name
