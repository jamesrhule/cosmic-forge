"""In-process run registry.

Keeps submitted runs in memory, drives them through the M1–M7
pipeline on a background executor, and streams lifecycle events.
"""

from __future__ import annotations

import asyncio
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import AsyncIterator

from ..domain import (
    LogEvent,
    MetricEvent,
    ProgressEvent,
    ResultEvent,
    RunConfig,
    RunEvent,
    RunResult,
    RunStatus,
    StatusEvent,
    ValidationBenchmark,
    ValidationReport,
)
from ..m7_infer.audit import run_audit
from ..m7_infer.pipeline import RunPipeline, build_run_result


@dataclass
class _RunSlot:
    run_id: str
    config: RunConfig
    status: RunStatus = "queued"
    result: RunResult | None = None
    events: list[RunEvent] = field(default_factory=list)
    event_sem: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(0))
    cancelled: bool = False
    createdAt: datetime = field(default_factory=lambda: datetime.now(UTC))


class RunRegistry:
    """Append-only run store with cooperative cancellation."""

    def __init__(self) -> None:
        self._runs: dict[str, _RunSlot] = {}
        self._listeners: dict[str, list[asyncio.Queue[RunEvent]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def _new_id(self) -> str:
        return f"run_{secrets.token_hex(6)}"

    # ── Submit ────────────────────────────────────────────────────────
    async def submit(self, cfg: RunConfig) -> str:
        rid = self._new_id()
        slot = _RunSlot(run_id=rid, config=cfg)
        async with self._lock:
            self._runs[rid] = slot
        asyncio.create_task(self._drive(rid))
        return rid

    def get(self, run_id: str) -> _RunSlot | None:
        return self._runs.get(run_id)

    def result(self, run_id: str) -> RunResult | None:
        s = self._runs.get(run_id)
        return s.result if s else None

    async def cancel(self, run_id: str) -> bool:
        s = self._runs.get(run_id)
        if not s:
            return False
        s.cancelled = True
        await self._emit(run_id, StatusEvent(status="canceled", at=datetime.now(UTC)))
        return True

    # ── Stream ────────────────────────────────────────────────────────
    async def stream(self, run_id: str) -> AsyncIterator[RunEvent]:
        q: asyncio.Queue[RunEvent] = asyncio.Queue()
        self._listeners[run_id].append(q)
        # Replay history first so late subscribers don't miss events.
        for ev in list(self._runs[run_id].events):
            await q.put(ev)
        try:
            while True:
                ev = await q.get()
                yield ev
                if getattr(ev, "type", None) == "result":
                    return
                if getattr(ev, "status", None) in {"completed", "failed", "canceled"}:
                    return
        finally:
            self._listeners[run_id].remove(q)

    async def _emit(self, run_id: str, ev: RunEvent) -> None:
        s = self._runs[run_id]
        s.events.append(ev)
        for q in list(self._listeners[run_id]):
            await q.put(ev)

    # ── Driver ────────────────────────────────────────────────────────
    async def _drive(self, run_id: str) -> None:
        s = self._runs[run_id]
        loop = asyncio.get_running_loop()
        try:
            await self._emit(run_id, StatusEvent(status="running", at=datetime.now(UTC)))
            await self._emit(run_id, LogEvent(
                module="M1", level="info", text="starting pipeline",
                at=datetime.now(UTC)))

            for mod, frac in [
                ("M1", 0.15), ("M2", 0.3), ("M3", 0.6),
                ("M4", 0.75), ("M5", 0.9), ("M6", 1.0),
            ]:
                if s.cancelled:
                    return
                await self._emit(run_id, ProgressEvent(module=mod, fraction=frac))

            pr = await loop.run_in_executor(
                None, lambda: RunPipeline(seed=0).run(s.config)
            )
            if s.cancelled:
                return

            result = build_run_result(
                run_id=run_id,
                cfg=s.config,
                pr=pr,
                audit_runner=run_audit,
                validation_benchmarks=_validation_benchmarks_for(pr),
            )
            s.result = result
            s.status = "completed"
            await self._emit(run_id, MetricEvent(name="eta_B", value=result.eta_B.value))
            await self._emit(run_id, MetricEvent(name="F_GB", value=result.F_GB))
            await self._emit(run_id, ResultEvent(payload=result))
            await self._emit(run_id, StatusEvent(status="completed", at=datetime.now(UTC)))
        except Exception as exc:  # noqa: BLE001
            s.status = "failed"
            await self._emit(run_id, LogEvent(
                module="M7", level="error", text=str(exc),
                at=datetime.now(UTC)))
            await self._emit(run_id, StatusEvent(status="failed", at=datetime.now(UTC)))


def _validation_benchmarks_for(pr) -> list[ValidationBenchmark]:  # type: ignore[no-untyped-def]
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


_ = ValidationReport  # re-exported for tests
_ = time
