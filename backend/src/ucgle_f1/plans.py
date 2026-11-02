"""Plan limits enforced at enqueue time (P3-05).

``PLAN_LIMITS`` is main's table (``src/lib/billing.ts``), which the pricing
page shows; ``backend/tests/test_plan_limits.py`` fails if the two drift.
The tenant's tier is ``public.tenants.subscription_tier``, which only the
service changes (trigger ``tenants_write_guard``, migration 20261102100000).

Machine-readable errors (``ServiceError`` codes, HTTP status via
``api_errors``):

- ``PLAN_RUNS_PER_MONTH_EXCEEDED`` (429): runs the API created this calendar
  month (UTC) already equal ``maxRunsPerMonth``.
- ``PLAN_CONCURRENT_JOBS_EXCEEDED`` (429): queued + running jobs already
  equal ``maxConcurrentJobs``.
- ``PLAN_GPU_REQUIRED`` (402): a ``gpu_small``/``gpu_large`` job on a tier
  without ``gpuAccess``.
- ``PLAN_TIMELINE_BYTES_EXCEEDED`` (402): a timeline larger than
  ``maxTimelineBytes``.

Per-tenant QPU spend budgets are enforced in the router through the tenant
budget hook (``m8_agent.auth.install_budget_hook``), code ``BUDGET_EXCEEDED`` (402).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Connection, text

from .domain import ServiceError

INF = math.inf


@dataclass(frozen=True)
class PlanLimits:
    maxRunsPerMonth: float
    maxConcurrentJobs: float
    maxTimelineBytes: int
    gpuAccess: bool
    prioritySupport: bool


PLAN_LIMITS: dict[str, PlanLimits] = {
    "free": PlanLimits(25, 1, 10 * 1024 * 1024, False, False),
    "pro": PlanLimits(500, 4, 50 * 1024 * 1024, True, False),
    "team": PlanLimits(5_000, 16, 250 * 1024 * 1024, True, True),
    "enterprise": PlanLimits(INF, INF, 1024 * 1024 * 1024, True, True),
}

GPU_CLASSES = frozenset({"gpu_small", "gpu_large"})


class PlanLimitExceeded(ServiceError):
    def __init__(self, code: str, message: str, *, tier: str, limit: float, used: float) -> None:
        super().__init__(code, message)  # type: ignore[arg-type]  # one of the PLAN_* codes
        self.tier = tier
        self.limit = limit
        self.used = used


def limits_for(tier: str | None) -> tuple[str, PlanLimits]:
    tier = tier if tier in PLAN_LIMITS else "free"
    return tier, PLAN_LIMITS[tier]  # type: ignore[index]


def check_timeline_bytes(tier: str | None, size: int) -> None:
    name, lim = limits_for(tier)
    if size > lim.maxTimelineBytes:
        raise PlanLimitExceeded(
            "PLAN_TIMELINE_BYTES_EXCEEDED",
            f"timeline of {size} bytes exceeds the {name} plan's {lim.maxTimelineBytes} bytes",
            tier=name, limit=lim.maxTimelineBytes, used=size,
        )


def enforce_at_enqueue(
    conn: Connection, tenant_uuid: str, compute_class: str, *, timeline_bytes: int | None = None,
) -> None:
    """Check every plan limit inside the enqueue transaction.

    The tenant row is locked (``for update``) so concurrent submits for one
    tenant are serialised and can't both slip under a limit.
    """
    row = conn.execute(
        text("select subscription_tier::text from public.tenants where id = cast(:t as uuid) for update"),
        {"t": tenant_uuid},
    ).first()
    name, lim = limits_for(row[0] if row else None)
    if compute_class in GPU_CLASSES and not lim.gpuAccess:
        raise PlanLimitExceeded(
            "PLAN_GPU_REQUIRED", f"the {name} plan has no GPU access ({compute_class})",
            tier=name, limit=0, used=1,
        )
    if timeline_bytes is not None:
        check_timeline_bytes(name, timeline_bytes)
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Only runs the API created count (origin 'api', 20261102120000): clients
    # can write rows into public.runs through PostgREST, with any
    # created_at, but the runs_origin_guard trigger marks every such row
    # 'client', also after its author's account is deleted, and the API's
    # own rows are beyond client policies (round 2, c2: a member could
    # otherwise lock the tenant out with rows dated 2099).
    runs = conn.execute(
        text(
            "select count(*) from public.runs where tenant_id = cast(:t as uuid) "
            "and origin = 'api' and created_at >= :m"
        ),
        {"t": tenant_uuid, "m": month_start},
    ).scalar_one()
    if runs >= lim.maxRunsPerMonth:
        raise PlanLimitExceeded(
            "PLAN_RUNS_PER_MONTH_EXCEEDED",
            f"the {name} plan allows {int(lim.maxRunsPerMonth)} runs per month; {runs} used",
            tier=name, limit=lim.maxRunsPerMonth, used=runs,
        )
    active = conn.execute(
        text(
            "select count(*) from public.jobs where tenant_id = cast(:t as uuid) "
            "and status in ('queued', 'running')"
        ),
        {"t": tenant_uuid},
    ).scalar_one()
    if active >= lim.maxConcurrentJobs:
        raise PlanLimitExceeded(
            "PLAN_CONCURRENT_JOBS_EXCEEDED",
            f"the {name} plan allows {int(lim.maxConcurrentJobs)} concurrent jobs; {active} active",
            tier=name, limit=lim.maxConcurrentJobs, used=active,
        )


__all__ = [
    "GPU_CLASSES", "PLAN_LIMITS", "PlanLimitExceeded", "PlanLimits",
    "check_timeline_bytes", "enforce_at_enqueue", "limits_for",
]
