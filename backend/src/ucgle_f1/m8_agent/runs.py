"""Run registry for UCGLE-F1 runs on the Postgres job queue (P3-02).

``submit`` validates nothing heavy and computes nothing: it records the run
in ``public.runs`` and enqueues a ``ucgle_f1.run`` job (``public.jobs``). A
worker (``python -m qcompass_worker``) runs the M1→M6 pipeline and writes
progress events to ``public.job_events`` as each module finishes, and the
full ``RunResult`` to ``public.run_results``. ``stream`` replays and tails
those events, so a run survives an API restart and any API replica can
stream it. This replaces the in-process ``RunRegistry._drive``, which ran the
pipeline inside the API and emitted progress before computing.
"""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import TypeAdapter

from ..domain import (
    ResultEvent,
    RunConfig,
    RunEvent,
    RunResult,
    ServiceError,
    ValidationBenchmark,
    ValidationReport,
)
from ..jobs import TERMINAL_RUN_STATUSES, JobQueue, get_queue
from ..m7_infer.pipeline import RunPipeline, build_run_result  # re-exported (scan tool)

_EVENT = TypeAdapter(RunEvent)
_POLL_SECONDS = 0.2


@dataclass(frozen=True)
class RunSlot:
    """A run as the API sees it (status from Postgres)."""

    run_id: str
    status: str
    config: dict[str, Any]
    createdAt: datetime
    tenant_id: str


def _tenant_uuid(tenant: str | None, create: bool) -> str | None:
    """UUID of ``tenant`` (slug or UUID; SEC-H1: passed explicitly by callers).

    ``None`` falls back to the bound tenant, then to the dev tenant only
    under ``QCOMPASS_ENV=dev``; otherwise :class:`principal.TenantNotBound`.
    """
    from .auth import get_auth_store
    from .principal import resolve_tenant_slug

    slug = resolve_tenant_slug(tenant)
    store = get_auth_store()
    if create:
        return store.ensure_tenant(slug)
    found = store.resolve_tenant(slug)
    return found[0] if found else None


class RunRegistry:
    """Submit, inspect, cancel and stream UCGLE-F1 runs (tenant-scoped)."""

    def __init__(self, queue: JobQueue | None = None) -> None:
        self._queue = queue

    @property
    def queue(self) -> JobQueue:
        return self._queue or get_queue()

    def ping(self) -> None:
        """Readiness probe for the run queue (``/readyz``): the jobs table answers."""
        self.queue.ping()

    @staticmethod
    def _new_id() -> str:
        return f"run_{secrets.token_hex(6)}"

    # ── Submit ────────────────────────────────────────────────────────
    async def submit(self, cfg: RunConfig, *, tenant: str | None = None) -> str:
        rid = self._new_id()
        config = cfg.model_dump(mode="json")
        tenant_uuid = await asyncio.to_thread(_tenant_uuid, tenant, True)
        assert tenant_uuid is not None
        await asyncio.to_thread(
            self.queue.enqueue_run,
            run_id=rid, tenant_uuid=tenant_uuid, kind="ucgle_f1.run",
            payload={"config": config},
            label=f"cosmology.ucglef1 · {rid}",
            config={"domain": "cosmology", "kind": "ucgle_f1.run", **config},
            compute_class="gpu_small" if cfg.precision == "high" else "cpu",
        )
        return rid

    def get(self, run_id: str, *, tenant: str | None = None) -> RunSlot | None:
        tenant_uuid = _tenant_uuid(tenant, False)
        if tenant_uuid is None:
            return None
        rec = self.queue.get_run(run_id, tenant_uuid=tenant_uuid)
        if rec is None or rec.config.get("kind") != "ucgle_f1.run":
            return None
        return RunSlot(rec.id, rec.status, rec.config, rec.created_at, rec.tenant_id)

    def result(self, run_id: str, *, tenant: str | None = None) -> RunResult | None:
        slot = self.get(run_id, tenant=tenant)
        if slot is None:
            return None
        payload = self.queue.result(run_id, tenant_uuid=slot.tenant_id)
        return RunResult.model_validate(payload) if payload is not None else None

    async def cancel(self, run_id: str, *, tenant: str | None = None) -> bool:
        if await asyncio.to_thread(lambda: self.get(run_id, tenant=tenant)) is None:
            return False
        return await asyncio.to_thread(self.queue.cancel_run, run_id)

    # ── Stream ────────────────────────────────────────────────────────
    async def stream(self, run_id: str, *, tenant: str | None = None) -> AsyncIterator[RunEvent]:
        """Replay the run's events, then tail them until it ends."""
        slot = await asyncio.to_thread(lambda: self.get(run_id, tenant=tenant))
        if slot is None:
            raise ServiceError("NOT_FOUND", f"run {run_id} not found")
        tenant_uuid = slot.tenant_id
        from .settings import StreamBound

        bound = StreamBound()  # SF1: never poll forever
        after = 0
        while True:
            events = await asyncio.to_thread(
                self.queue.events, run_id, after_id=after, tenant_uuid=tenant_uuid,
            )
            if events:
                bound.saw_event()
            elif (reason := bound.expired()) is not None:
                raise ServiceError("STREAM_ABORTED", f"run {run_id}: {reason}")
            for row in events:
                after = row.id
                if row.type == "result":
                    payload = await asyncio.to_thread(self.queue.result, run_id, tenant_uuid=tenant_uuid)
                    if payload is not None:
                        yield ResultEvent(payload=RunResult.model_validate(payload))
                        return
                    continue
                ev = _EVENT.validate_python({"type": row.type, **row.payload})
                yield ev
                if getattr(ev, "status", None) in TERMINAL_RUN_STATUSES:
                    return
            await asyncio.sleep(_POLL_SECONDS)


def validation_benchmarks_for(pr) -> list[ValidationBenchmark]:  # type: ignore[no-untyped-def]
    # Static V2 band: observed η_B = 6.1e-10.
    observed = pr.eta_B
    target = 6.1e-10
    rel = abs(observed - target) / target if target else float("nan")
    status = "match" if rel < 0.1 else ("degraded" if rel < 1.0 else "miss")
    return [ValidationBenchmark(
        id="V2",
        label="Kawai-Kim 1702.07689",
        arxivId="1702.07689",
        target=target,
        observed=float(observed),
        relativeError=float(rel),
        status=status,
    )]


_registry_singleton: RunRegistry | None = None


def get_registry() -> RunRegistry:
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = RunRegistry()
    return _registry_singleton


_validation_benchmarks_for = validation_benchmarks_for  # pre-P3-02 name
_ = (RunPipeline, build_run_result)
_ = ValidationReport  # re-exported for tests
