"""Cost-aware routing policy (PROMPT 6A baseline + PROMPT 6B layers).

Decision flow:

  1. ``budget_usd == 0``:
     - if ``require_real_hardware`` is True → raise
       :class:`BudgetExceeded` (real hardware costs money).
     - else route to ``local_aer`` if its SDK is importable, else
       ``local_lightning``, else raise (no zero-cost backend).
  2. ``budget_usd > 0``:
     - filter by ``preferred_providers`` (when non-empty).
     - free-tier candidates (IBM Open Plan → IQM Starter → AWS
       SV1) are considered first; the cheapest free option that
       meets ``min_fidelity`` wins outright.
     - if no free-tier candidate matches, rank paid candidates by
       ``stub_cost * (2 - fidelity_estimate)``.
     - the chosen backend's calibration is checked against
       ``CalibrationCache``; >3σ drift raises
       :class:`CalibrationDrift`.
  3. transforms (``transforms`` field on :class:`RouterRequest`)
     are applied via :func:`qcompass_router.transforms.apply_transforms`
     and the resulting records are attached to the decision.
"""

from __future__ import annotations

from typing import Any, Iterable

from . import pricing_stub
from .budget import BudgetExceeded
from .calibration import CalibrationCache, CalibrationDrift
from .decision import RouterRequest, RoutingDecision, TransformRecord
from .providers import ProviderAdapter, list_providers
from .providers.base import BackendInfo


_FREE_TIER_ORDER = ("ibm", "iqm", "braket")


class Router:
    """The qcompass-router decision engine."""

    def __init__(
        self,
        providers: list[ProviderAdapter] | None = None,
        *,
        calibration: CalibrationCache | None = None,
    ) -> None:
        self._providers: list[ProviderAdapter] = (
            list(providers) if providers is not None else list_providers()
        )
        self._calibration = calibration

    @property
    def providers(self) -> list[ProviderAdapter]:
        return list(self._providers)

    def decide(
        self,
        req: RouterRequest,
        *,
        circuit: Any | None = None,
        transforms: list[str] | None = None,
        transform_parameters: dict[str, dict[str, Any]] | None = None,
    ) -> RoutingDecision:
        """Pick a backend for ``req``; optionally apply transforms.

        ``transforms`` is a list of transform names (e.g.
        ``["aqc_tensor", "obp"]``) applied in order; the resulting
        :class:`TransformRecord` list lands in
        ``RoutingDecision.transforms_applied`` so the caller can
        propagate it into ``ProvenanceRecord.error_mitigation_config``.
        """
        if req.budget_usd <= 0.0:
            decision = self._route_free(req)
        else:
            decision = self._route_paid(req)

        if self._calibration is not None:
            self._calibration.check_drift(decision.provider, decision.backend)

        if transforms:
            from .transforms import apply_transforms

            _, records = apply_transforms(
                circuit, transforms, parameters=transform_parameters,
            )
            decision = decision.model_copy(
                update={"transforms_applied": records},
            )
        return decision

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

        # Free-tier preference: surface free-tier candidates first
        # in the canonical PROMPT 6B order. The cheapest free
        # candidate that meets the fidelity floor wins outright.
        free_candidates = [c for c in candidates if c[6]]
        if free_candidates:
            free_sorted = sorted(
                free_candidates,
                key=lambda item: (
                    _free_tier_rank(item[0]),
                    item[2],            # cost
                    -item[4],           # higher fidelity first
                ),
            )
            provider, backend, cost, queue, fidelity, reason, _ = free_sorted[0]
            return RoutingDecision(
                provider=provider,
                backend=backend,
                cost_estimate_usd=cost,
                queue_time_s_estimate=queue,
                fidelity_estimate=fidelity,
                transforms_applied=[],
                reason=f"free-tier preference: {reason}",
            )

        scored = sorted(candidates, key=_score_key(req))
        provider, backend, cost, queue, fidelity, reason, _ = scored[0]
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
    ) -> Iterable[tuple[str, str, float, float, float, str, bool]]:
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
                    backend.free_tier,
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
    def key(
        item: tuple[str, str, float, float, float, str, bool],
    ) -> tuple[float, float, float]:
        _provider, _backend, cost, queue, fidelity, _reason, _free = item
        return (cost * (2.0 - fidelity), queue, -fidelity)
    return key


def _free_tier_rank(provider: str) -> int:
    """Free-tier ordering: IBM Open → IQM Starter → AWS sims."""
    try:
        return _FREE_TIER_ORDER.index(provider)
    except ValueError:
        return len(_FREE_TIER_ORDER)


__all__ = ["Router"]
