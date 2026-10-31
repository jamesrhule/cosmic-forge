"""The QCompass worker loop (P3-02). Entrypoint: ``python -m qcompass_worker``.

Loop: ``claim_next_job`` with a lease → run the handler for the job's kind
while a heartbeat thread renews the lease → ``complete_job``. Every loop
also runs the janitor (``reap_expired_jobs``), which requeues jobs whose
worker died and dead-letters a job after ``max_attempts`` with a
``system_incidents`` row.

Handlers publish progress to ``public.job_events`` as work actually
finishes (M1…M6 for UCGLE-F1 runs, prepare/run for domain runs); nothing is
emitted ahead of the computation. The API streams those rows over SSE and
WebSocket.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import socket
import threading
import time
import traceback
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from .jobs import COMPUTE_CLASSES, JOB_KINDS, Job, JobQueue

log = logging.getLogger(__name__)

_MODULES = ("M1", "M2", "M3", "M4", "M5", "M6")


class JobCancelled(Exception):
    """The job was cancelled (or its lease lost) while it ran."""


class JobContext:
    """What a handler sees: the job, the queue, and cooperative cancellation."""

    def __init__(self, job: Job, queue: JobQueue, lost: threading.Event) -> None:
        self.job = job
        self.queue = queue
        self._lost = lost

    @property
    def run_id(self) -> str:
        if self.job.run_id is None:
            raise ValueError(f"job {self.job.id} ({self.job.kind}) has no run")
        return self.job.run_id

    def emit(self, type_: str, payload: dict[str, Any]) -> None:
        self.queue.emit(self.job, self.run_id, self.job.tenant_id, type_, payload)

    def check_cancelled(self) -> None:
        if self._lost.is_set() or self.queue.job_status(self.job.id) == "cancelled":
            raise JobCancelled(self.job.id)


Handler = Callable[[JobContext], dict[str, Any] | None]


# ── handlers ───────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _record_provenance(ctx: JobContext, record: dict[str, Any]) -> None:
    """Row in public.run_provenance plus an object in run-artifacts (P3-03)."""
    import json

    from .artifacts import ArtifactStore

    upload = ArtifactStore().put(
        ctx.run_id, "provenance.json",
        json.dumps(record, sort_keys=True, default=str).encode(),
    )
    ctx.queue.save_provenance(
        ctx.run_id, ctx.job.tenant_id, record,
        artifact_path=upload.path, artifact_status=upload.status,
    )


def handle_ucgle_f1_run(ctx: JobContext) -> dict[str, Any]:
    """UCGLE-F1 M1→M6 run; events use the backend's RunEvent shapes."""
    from .domain import LogEvent, MetricEvent, ProgressEvent, RunConfig, StatusEvent
    from .m7_infer.audit import run_audit
    from .m7_infer.pipeline import RunPipeline, build_run_result
    from .m8_agent.runs import validation_benchmarks_for

    def emit(ev: Any) -> None:
        ctx.emit(ev.type, ev.model_dump(mode="json"))

    cfg = RunConfig.model_validate(ctx.job.payload["config"])
    ctx.queue.set_run_status(ctx.run_id, "running")
    emit(StatusEvent(status="running", at=datetime.now(UTC)))
    emit(LogEvent(module="M1", level="info", text="starting pipeline", at=datetime.now(UTC)))

    def on_module(module: str, seconds: float) -> None:
        emit(ProgressEvent(
            module=module,  # type: ignore[arg-type]
            fraction=(_MODULES.index(module) + 1) / len(_MODULES),
            detail=f"{module} finished in {seconds:.3f}s",
        ))
        ctx.check_cancelled()

    pr = RunPipeline(seed=0).run(cfg, on_module=on_module)
    result = build_run_result(
        run_id=ctx.run_id, cfg=cfg, pr=pr, audit_runner=run_audit,
        validation_benchmarks=validation_benchmarks_for(pr),
    )
    ctx.check_cancelled()
    dumped = result.model_dump(mode="json")
    ctx.queue.save_result(ctx.run_id, dumped)
    _record_provenance(ctx, {
        "classical_reference_hash": "",
        "run_provenance": dumped.get("provenance"),
        "config": dumped.get("config"),
    })
    ctx.queue.set_run_status(ctx.run_id, "completed")
    emit(MetricEvent(name="eta_B", value=result.eta_B.value))
    emit(MetricEvent(name="F_GB", value=result.F_GB))
    # The result body lives in run_results; the stream hydrates it.
    ctx.emit("result", {"type": "result"})
    emit(StatusEvent(status="completed", at=datetime.now(UTC)))
    return {"run_id": ctx.run_id, "eta_B": result.eta_B.value}


def _jsonable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return repr(obj)


def _classical_hash(result: Any) -> str:
    direct = getattr(result, "classical_hash", None)
    if direct:
        return str(direct)
    prov = getattr(result, "provenance", None)
    return str(getattr(prov, "classical_reference_hash", "") or "")


def resolve_simulation(domain: str) -> Any:
    """The plugin class for a short domain name (``cosmology``) or plugin name.

    Plugins register under their own names: ``cosmology.ucglef1`` for the
    UCGLE-F1 adapter, the short name for the rest. Jobs carry the short name
    (``qcompass_routes``), so fall back to the plugin whose name starts with it.
    """
    from qcompass_core.registry import get_simulation, list_domains

    try:
        return get_simulation(domain)
    except Exception:
        for name in list_domains():
            if name.split(".", 1)[0] == domain:
                return get_simulation(name)
        raise


def handle_qcompass_run(ctx: JobContext) -> dict[str, Any]:
    """A domain run through the qcompass plugin registry (prepare → run)."""
    from qcompass_core import Manifest

    domain = str(ctx.job.payload["domain"])
    manifest = ctx.job.payload["manifest"]
    ctx.queue.set_run_status(ctx.run_id, "running")
    ctx.emit("status", {"status": "running", "at": _now()})
    try:
        sim_cls = resolve_simulation(domain)
    except Exception as exc:  # noqa: BLE001 - plugin missing in this image
        raise RuntimeError(f"domain plugin {domain!r} is not installed in this worker: {exc}") from exc
    t0 = time.perf_counter()
    qmanifest = Manifest.model_validate(manifest)
    sim = sim_cls()
    instance = sim.prepare(qmanifest)
    ctx.emit("progress", {"stage": "prepare", "fraction": 0.5, "seconds": time.perf_counter() - t0})
    ctx.check_cancelled()
    t1 = time.perf_counter()
    result = sim.run(instance, backend=None)
    ctx.emit("progress", {"stage": "run", "fraction": 1.0, "seconds": time.perf_counter() - t1})
    ctx.check_cancelled()
    classical_hash = _classical_hash(result)
    prov = getattr(result, "provenance", None)
    record = _jsonable(prov) if prov is not None else {}
    if not isinstance(record, dict):
        record = {"value": record}
    record.setdefault("classical_reference_hash", classical_hash)
    _record_provenance(ctx, record)
    ctx.queue.save_result(ctx.run_id, {
        "manifest": manifest,
        "status_detail": "completed",
        "result": _jsonable(result),
        "classical_reference_hash": classical_hash,
    })
    ctx.queue.set_run_status(ctx.run_id, "completed")
    ctx.emit("status", {"status": "completed", "at": _now()})
    return {"run_id": ctx.run_id, "classical_reference_hash": classical_hash}


def _owned_elsewhere(ticket: str) -> Handler:
    def _handler(ctx: JobContext) -> dict[str, Any]:
        raise NotImplementedError(
            f"job kind {ctx.job.kind!r} is accepted by the queue; its handler lands in {ticket}",
        )
    return _handler


HANDLERS: dict[str, Handler] = {
    "ucgle_f1.run": handle_ucgle_f1_run,
    "qcompass.run": handle_qcompass_run,
    # Kinds the queue accepts now; their compute is owned by later tickets.
    "scan": _owned_elsewhere("P4-07"),
    "viz.bake": _owned_elsewhere("P4-04"),
    "qpu.submit": _owned_elsewhere("P2-01"),
    "qpu.poll": _owned_elsewhere("P2-01"),
    "patch.dryrun": _owned_elsewhere("P3-08/P5-05"),
}
assert set(HANDLERS) == set(JOB_KINDS)


# ── loop ───────────────────────────────────────────────────────────────


class Worker:
    def __init__(
        self,
        queue: JobQueue,
        classes: tuple[str, ...] = ("cpu",),
        *,
        worker_id: str | None = None,
        lease_seconds: int = 60,
        heartbeat_seconds: float | None = None,
        poll_seconds: float = 0.5,
        handlers: dict[str, Handler] | None = None,
    ) -> None:
        unknown = set(classes) - set(COMPUTE_CLASSES)
        if unknown:
            raise ValueError(f"unknown compute classes: {sorted(unknown)}")
        self.queue = queue
        self.classes = classes
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
        self.lease_seconds = lease_seconds
        self.heartbeat_seconds = heartbeat_seconds or max(lease_seconds / 3, 0.2)
        self.poll_seconds = poll_seconds
        self.handlers = handlers or HANDLERS
        self.stop = threading.Event()

    def run_once(self) -> bool:
        """Reap, then claim and run one job. False when the queue was empty."""
        self.queue.reap()
        job = self.queue.claim(self.worker_id, self.classes, self.lease_seconds)
        if job is None:
            return False
        self._execute(job)
        return True

    def run_forever(self) -> None:
        log.info("worker %s serving %s", self.worker_id, ",".join(self.classes))
        while not self.stop.is_set():
            try:
                busy = self.run_once()
            except Exception:  # noqa: BLE001 - keep serving; the janitor recovers leases
                log.exception("worker loop error")
                busy = False
            if not busy:
                self.stop.wait(self.poll_seconds)

    def _execute(self, job: Job) -> None:
        lost = threading.Event()
        done = threading.Event()

        def beat() -> None:
            while not done.wait(self.heartbeat_seconds):
                try:
                    if not self.queue.heartbeat(job.id, self.worker_id, self.lease_seconds):
                        lost.set()
                        return
                except Exception:  # noqa: BLE001 - transient DB error; retry next beat
                    log.warning("heartbeat failed for job %s", job.id, exc_info=True)

        # Tenant context for the job (budget hook, P3-05; tenant-scoped stores).
        from .m8_agent.auth import reset_active_tenant, set_active_tenant

        tenant_token = set_active_tenant(job.tenant_id)
        hb = threading.Thread(target=beat, name=f"heartbeat-{job.id[:8]}", daemon=True)
        hb.start()
        ctx = JobContext(job, self.queue, lost)
        try:
            handler = self.handlers.get(job.kind)
            if handler is None:
                raise NotImplementedError(f"no handler for job kind {job.kind!r}")
            result = handler(ctx)
        except JobCancelled:
            log.info("job %s cancelled or lease lost", job.id)
            return
        except Exception as exc:  # noqa: BLE001 - recorded on the job and the run
            message = f"{exc.__class__.__name__}: {exc}"
            log.warning("job %s failed: %s", job.id, message)
            if job.run_id is not None:
                try:
                    ctx.emit("log", {"type": "log", "module": "M7", "level": "error",
                                     "text": message, "at": _now()})
                    ctx.queue.set_run_status(job.run_id, "failed")
                    ctx.emit("status", {"type": "status", "status": "failed", "at": _now()})
                except Exception:  # noqa: BLE001
                    log.exception("could not record failure for run %s", job.run_id)
            self.queue.complete(job.id, error=message[:2000] or traceback.format_exc()[-2000:])
            return
        finally:
            done.set()
            hb.join(timeout=5)
            reset_active_tenant(tenant_token)
        self.queue.complete(job.id, result=result or {})


def main(argv: list[str] | None = None) -> int:
    import argparse
    import signal

    parser = argparse.ArgumentParser(prog="qcompass_worker", description=__doc__.splitlines()[0])
    parser.add_argument("--classes", default="cpu", help="comma-separated compute classes")
    parser.add_argument("--lease-seconds", type=int, default=60)
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    parser.add_argument("--once", action="store_true", help="drain the queue, then exit")
    args = parser.parse_args(argv)
    logging.basicConfig(level=os.environ.get("QCOMPASS_LOG_LEVEL", "INFO"))
    classes = tuple(c.strip() for c in args.classes.split(",") if c.strip())
    # P3-05: QPU jobs routed in this process are gated by tenant budgets too.
    from .m8_agent.auth import install_budget_hook

    install_budget_hook()
    worker = Worker(JobQueue(), classes, lease_seconds=args.lease_seconds, poll_seconds=args.poll_seconds)
    if args.once:
        while worker.run_once():
            pass
        return 0
    signal.signal(signal.SIGTERM, lambda *_: worker.stop.set())
    signal.signal(signal.SIGINT, lambda *_: worker.stop.set())
    worker.run_forever()
    return 0


__all__ = ["HANDLERS", "JobCancelled", "JobContext", "Worker", "main"]
