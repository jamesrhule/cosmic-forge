"""Cost-aware routing policy (PROMPT 6A baseline).

Decision flow:

  1. ``budget_usd == 0``:
     - if ``require_real_hardware`` is True → raise
       :class:`BudgetExceeded` (real hardware costs money).
     - else route to ``local_aer`` if its SDK is importable, else
       ``local_lightning``, else raise (no zero-cost backend).
  2. ``budget_usd > 0``:
     - filter by ``preferred_providers`` (when non-empty).
     - rank candidates by ``stub_cost * (2 - fidelity_estimate)``.
     - return cheapest meeting ``min_fidelity``.

PROMPT 6B layers in:
  - Free-tier preference (IBM Open Plan → IQM Starter → AWS sims)
    ahead of paid tiers.
  - Calibration drift gate (refuses on > 3σ drift).
  - Transform stack with TransformRecord propagation.
  - Live pricing fetchers with SSL pinning.
"""

from __future__ import annotations

from typing import Iterable

from . import pricing_stub
from .budget import BudgetExceeded
from .decision import RouterRequest, RoutingDecision
from .providers import ProviderAdapter, list_providers
from .providers.base import BackendInfo


class Router:
    """The qcompass-router decision engine."""

    def __init__(
        self,
        providers: list[ProviderAdapter] | None = None,
    ) -> None:
        self._providers: list[ProviderAdapter] = (
            list(providers) if providers is not None else list_providers()
        )

    @property
    def providers(self) -> list[ProviderAdapter]:
        return list(self._providers)

    def decide(self, req: RouterRequest) -> RoutingDecision:
        if req.budget_usd <= 0.0:
            return self._route_free(req)
        return self._route_paid(req)

    # ── budget == 0 ──────────────────────────────────────────────

    def _route_free(self, req: RouterRequest) -> RoutingDecision:
        if req.require_real_hardware:
            msg = (
                "budget_usd=0 cannot satisfy require_real_hardware=True; "
                "increase the budget or drop the hardware requirement."
            )
            raise BudgetExceeded(msg)

        for adapter_name in ("local_aer", "local_lightning"):
            for adapter in self._providers:
                if adapter.name != adapter_name:
                    continue
                if not adapter.is_available():
                    continue
                backends = adapter.list_backends()
                if not backends:
                    continue
                pick = backends[0]
                return RoutingDecision(
                    provider=pick.provider,
                    backend=pick.name,
                    cost_estimate_usd=0.0,
                    queue_time_s_estimate=pick.queue_time_s_estimate,
                    fidelity_estimate=pick.fidelity_estimate,
                    transforms_applied=[],
                    reason=f"budget=0 → {adapter_name} (free / local).",
                )

        msg = (
            "No zero-cost backend is available. Install qcompass-router[ibm] "
            "(qiskit-aer) or qcompass-router[lightning] (pennylane-lightning)."
        )
        raise BudgetExceeded(msg, code="NO_LOCAL_BACKEND")

    # ── budget > 0 ──────────────────────────────────────────────

    def _route_paid(self, req: RouterRequest) -> RoutingDecision:
        candidates = list(self._enumerate_candidates(req))
        if not candidates:
            msg = (
                "No backend matched the request. Adjust min_fidelity or "
                "preferred_providers."
            )
            raise BudgetExceeded(msg, code="NO_CANDIDATE_BACKEND")

        scored = sorted(candidates, key=_score_key(req))
        provider, backend, cost, queue, fidelity, reason = scored[0]
        return RoutingDecision(
            provider=provider,
            backend=backend,
            cost_estimate_usd=cost,
            queue_time_s_estimate=queue,
            fidelity_estimate=fidelity,
            transforms_applied=[],
            reason=reason,
        )

    # ── helpers ─────────────────────────────────────────────────

    def _enumerate_candidates(
        self, req: RouterRequest,
    ) -> Iterable[tuple[str, str, float, float, float, str]]:
        preferred = set(req.preferred_providers)
        for adapter in self._providers:
            # Local adapters are still candidates when budget>0; they
            # cost nothing and so always win on cost. The user can
            # exclude them via preferred_providers if they explicitly
            # want hardware.
            if not adapter.is_available():
                continue
            if preferred and adapter.name not in preferred:
                continue
            for backend in adapter.list_backends():
                cost = self._cost_for(adapter, backend, req.shots)
                if cost > req.budget_usd:
                    continue
                if backend.fidelity_estimate < req.min_fidelity:
                    continue
                if req.require_real_hardware and (
                    adapter.kind == "local" or backend.simulator
                ):
                    continue
                if backend.queue_time_s_estimate > req.max_wallclock_s:
                    continue
                reason = (
                    f"{adapter.name}/{backend.name} cost ${cost:.4f}, "
                    f"fidelity {backend.fidelity_estimate:.3f}, queue "
                    f"{int(backend.queue_time_s_estimate)} s."
                )
                yield (
                    adapter.name,
                    backend.name,
                    cost,
                    backend.queue_time_s_estimate,
                    backend.fidelity_estimate,
                    reason,
                )

    @staticmethod
    def _cost_for(
        adapter: ProviderAdapter, backend: BackendInfo, shots: int,
    ) -> float:
        try:
            return pricing_stub.estimate(adapter.name, backend.name, shots)
        except KeyError:
            # Adapter exposes a backend not in the pricing seed; treat
            # as zero-cost so the router can still consider it.
            return 0.0


def _score_key(req: RouterRequest):  # type: ignore[no-untyped-def]
    """Cheaper × higher-fidelity wins.

    Score = cost * (2 - fidelity_estimate). At equal cost the
    higher-fidelity backend ranks first because (2 - fidelity) is
    smaller. At equal fidelity the cheaper backend wins.
    """
    def key(item: tuple[str, str, float, float, float, str]) -> tuple[float, float, float]:
        _provider, _backend, cost, queue, fidelity, _reason = item
        return (cost * (2.0 - fidelity), queue, -fidelity)
    return key


__all__ = ["Router"]
