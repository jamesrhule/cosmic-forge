"""The QCompass worker loop (P3-02). Entrypoint: ``python -m qcompass_worker``.

Loop: ``claim_next_job`` with a lease → run the handler for the job's kind
in a child process while a heartbeat thread renews the lease →
``complete_job``. Every loop also runs the janitor (``reap_expired_jobs``),
which requeues jobs whose worker died and dead-letters a job after
``max_attempts`` with a ``system_incidents`` row.

Each job runs in its own child process (``multiprocessing`` "spawn"): the
worker can kill it at its wall-clock limit or when its lease is lost, even
inside one long C call that holds the child's GIL (SEC-L3). The child has
no write path of its own: every run write, event and provenance upload it
makes is a request to this process, which applies it under the attempt's
lease (job, worker id, attempt) and stops answering once the attempt is
abandoned. The heartbeat thread and ``/healthz`` stay in this process.

Handlers publish progress to ``public.job_events`` as work actually
finishes (M1…M6 for UCGLE-F1 runs, prepare/run for domain runs); nothing is
emitted ahead of the computation. Each lease renewal also appends a
``heartbeat`` event, so a stream of a long, quiet run never looks idle.
The API streams those rows over SSE and WebSocket.
"""

from __future__ import annotations

import dataclasses
import functools
import logging
import math
import multiprocessing
import os
import socket
import sys
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from multiprocessing.connection import Connection
from multiprocessing.connection import wait as wait_for
from typing import Any

from .jobs import COMPUTE_CLASSES, JOB_KINDS, TERMINAL_RUN_STATUSES, Job, JobQueue

log = logging.getLogger(__name__)

_MODULES = ("M1", "M2", "M3", "M4", "M5", "M6")


DEFAULT_JOB_TIMEOUT_SECONDS = 3600.0
# The largest wall-clock limit a worker accepts: what a thread or process
# wait can represent on this platform.
MAX_JOB_TIMEOUT_SECONDS = float(threading.TIMEOUT_MAX)
_JOB_TIMEOUT_ENV = "QCOMPASS_JOB_TIMEOUT_SECONDS"


def _valid_timeout(value: object, source: str) -> float:
    """``value`` as a job time limit, or ValueError naming ``source`` (SEC-L3)."""
    ok = (
        isinstance(value, int | float) and not isinstance(value, bool)
        and math.isfinite(value) and 0 < value <= MAX_JOB_TIMEOUT_SECONDS
    )
    if not ok:
        msg = (f"{source} must be a finite number of seconds in (0, {MAX_JOB_TIMEOUT_SECONDS:g}], "
               f"got {value!r}; there is no way to disable the job time limit")
        raise ValueError(msg)
    return float(value)  # type: ignore[arg-type]


def job_timeout_seconds_default() -> float:
    """Per-job wall-clock limit (SEC-L3): ``QCOMPASS_JOB_TIMEOUT_SECONDS``, default 3600.

    The API's request timeout on Cloud Run is the same hour. A value that is
    not a finite number of seconds in (0, ``MAX_JOB_TIMEOUT_SECONDS``] raises
    ValueError, so a misconfigured worker refuses to start; there is no
    "no limit".
    """
    raw = os.environ.get(_JOB_TIMEOUT_ENV, "").strip()
    if not raw:
        return DEFAULT_JOB_TIMEOUT_SECONDS
    value: object
    try:
        value = float(raw)
    except ValueError:
        value = raw
    return _valid_timeout(value, f"{_JOB_TIMEOUT_ENV}={raw!r}")


class JobCancelled(Exception):
    """The job was cancelled (or its lease lost, or it timed out) while it ran."""


class _GuardedQueue:
    """The queue as a handler sees it, in the job's child process.

    Only these calls exist; each is a request to the worker process, which
    applies it under the attempt's lease (job, worker id, attempt) or
    refuses it. A refused write raises :class:`JobCancelled`. Nothing else
    of :class:`JobQueue` is reachable from a handler (``complete``,
    ``heartbeat``, ``cancel_run``, ``enqueue_run``, ``_emit``, ``engine``…).
    """

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def _call(self, name: str, *args: Any) -> Any:
        self._conn.send(("call", name, args))
        status, value = self._conn.recv()
        if status != "ok":
            raise JobCancelled(value)
        return value

    def set_run_status(self, run_id: str, status: str) -> None:
        self._call("set_run_status", run_id, status)

    def save_result(self, run_id: str, payload: dict[str, Any]) -> None:
        self._call("save_result", run_id, payload)

    def record_provenance(self, run_id: str, record: dict[str, Any]) -> None:
        """The provenance object in run-artifacts and its row (P3-03)."""
        self._call("record_provenance", run_id, record)

    def emit(self, job: Job, run_id: str, tenant_uuid: str, type_: str, payload: dict[str, Any]) -> None:
        self._call("emit", run_id, type_, payload)

    def job_status(self, job_id: str) -> str | None:
        return self._call("job_status", job_id)  # type: ignore[no-any-return]


class JobContext:
    """What a handler sees: the job, the guarded queue, and cooperative cancellation."""

    def __init__(self, job: Job, queue: _GuardedQueue) -> None:
        self.job = job
        self.queue = queue

    @property
    def run_id(self) -> str:
        if self.job.run_id is None:
            raise ValueError(f"job {self.job.id} ({self.job.kind}) has no run")
        return self.job.run_id

    def emit(self, type_: str, payload: dict[str, Any]) -> None:
        self.queue.emit(self.job, self.run_id, self.job.tenant_id, type_, payload)

    def check_cancelled(self) -> None:
        if self.queue.job_status(self.job.id) == "cancelled":
            raise JobCancelled(self.job.id)


Handler = Callable[[JobContext], dict[str, Any] | None]


# ── handlers ───────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _record_provenance(ctx: JobContext, record: dict[str, Any]) -> None:
    """Row in public.run_provenance plus an object in run-artifacts (P3-03).

    The worker process uploads the object and writes the row under the
    attempt's lease, checked immediately before the Storage put.
    """
    ctx.queue.record_provenance(ctx.run_id, record)


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


def _not_built_yet(ticket: str, ctx: JobContext) -> dict[str, Any]:
    raise NotImplementedError(
        f"job kind {ctx.job.kind!r} is accepted by the queue; its handler lands in {ticket}",
    )


def _owned_elsewhere(ticket: str) -> Handler:
    # A partial of a module-level function: job processes receive handlers by reference.
    return functools.partial(_not_built_yet, ticket)


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


# ── the job's child process ────────────────────────────────────────

_SPAWN = multiprocessing.get_context("spawn")
# How long a child that finished gets to exit, and how long terminate and
# kill each wait, before the next step.
_CHILD_EXIT_GRACE = 5.0
_CHILD_KILL_WAIT = 2.0
# After the worker refuses a child's write, how long the child gets to
# report its own outcome (a handler sees JobCancelled and returns at once).
_REFUSED_GRACE = 2.0
# CPU seconds a child may use beyond its share of the wall-clock limit
# before RLIMIT_CPU stops it (defence in depth: the wall-clock kill is the
# limit; this one also holds if the worker process itself is gone).
_CPU_SLACK_SECONDS = 30


@dataclasses.dataclass(frozen=True)
class _ChildSpec:
    job: Job
    handler: Handler  # pickled by reference: a module-level function
    parent_pid: int
    cpu_seconds: int
    budget_hook: bool
    log_level: int


def _cpu_count() -> int:
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        return max(1, os.cpu_count() or 1)


def _budget_hook_installed() -> bool:
    try:
        from qcompass_router.pricing import _tenant_budget_hook  # type: ignore[import-not-found]
    except ImportError:
        return False
    return _tenant_budget_hook() is not None


def _confine_child(parent_pid: int, cpu_seconds: int) -> None:
    """Die with the worker (Linux), and cap the child's CPU time (RLIMIT_CPU)."""
    if sys.platform.startswith("linux"):
        try:
            import ctypes
            import signal

            libc = ctypes.CDLL(None, use_errno=True)
            libc.prctl(1, int(signal.SIGKILL))  # PR_SET_PDEATHSIG
        except (OSError, AttributeError):  # pragma: no cover - libc without prctl
            pass
    if os.getppid() != parent_pid:
        os._exit(1)  # the worker is already gone
    try:
        import resource
    except ImportError:  # pragma: no cover - not POSIX
        return
    try:
        _, hard = resource.getrlimit(resource.RLIMIT_CPU)
        new_hard = cpu_seconds + 5
        if hard != resource.RLIM_INFINITY:
            new_hard = min(new_hard, hard)
        resource.setrlimit(resource.RLIMIT_CPU, (min(cpu_seconds, new_hard), new_hard))
    except (ValueError, OSError):  # pragma: no cover - a stricter limit is already set
        log.warning("could not set RLIMIT_CPU for job process", exc_info=True)


def _child_main(conn: Connection, spec: _ChildSpec) -> None:
    """Entry point of a job's child process: run the handler, report the outcome."""
    logging.basicConfig(level=spec.log_level)
    _confine_child(spec.parent_pid, spec.cpu_seconds)
    from .m8_agent.auth import install_budget_hook, set_active_tenant

    if spec.budget_hook:
        install_budget_hook()
    set_active_tenant(spec.job.tenant_id)
    ctx = JobContext(spec.job, _GuardedQueue(conn))
    outcome: tuple[str, Any]
    try:
        outcome = ("done", _jsonable(spec.handler(ctx) or {}))
    except JobCancelled as exc:
        outcome = ("cancelled", str(exc))
    except BaseException as exc:  # noqa: BLE001 - reported to the worker as the job's failure
        outcome = ("error", f"{exc.__class__.__name__}: {exc}")
    try:
        conn.send(outcome)
    except (OSError, ValueError):  # the worker stopped listening (abandoned)
        pass
    finally:
        conn.close()


@dataclasses.dataclass
class _Attempt:
    """One attempt at a job (its lease is job, worker id, attempt), as the worker sees it."""

    job: Job
    lost: threading.Event
    refused_at: float | None = None  # when the database refused one of its writes
    run_ended: bool = False  # it set its run terminal: no more liveness events


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
        job_timeout_seconds: float | None = None,
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
        # SEC-L3: finite, positive and representable, or the worker doesn't start.
        self.job_timeout_seconds = (
            job_timeout_seconds_default() if job_timeout_seconds is None
            else _valid_timeout(job_timeout_seconds, "job_timeout_seconds")
        )
        # Job processes that survived terminate and kill. While one lives the
        # worker claims nothing and /healthz fails, so the container is
        # replaced. Guarded by _lock: /healthz reads it from its own thread.
        self.abandoned: list[Any] = []
        self._lock = threading.Lock()
        self.stop = threading.Event()
        # Liveness for /healthz (P3-07): the loop's last turn, and whether a
        # job is running (a long job legitimately blocks the loop).
        self.last_loop = time.monotonic()
        self.busy = False

    def _live_abandoned(self) -> bool:
        with self._lock:
            return any(p.is_alive() for p in self.abandoned)

    def healthy(self) -> bool:
        """The loop is turning, or a job is in progress; never true after stop.

        Also false while a job process abandoned after its timeout or a lost
        lease is still alive (terminate and kill failed): the container is
        replaced. Read-only, so a probe never races the loop.
        """
        if self.stop.is_set():
            return False
        if self._live_abandoned():
            return False
        stale_after = max(30.0, 10 * self.poll_seconds)
        return self.busy or (time.monotonic() - self.last_loop) < stale_after

    def run_once(self) -> bool:
        """Reap, then claim and run one job. False when nothing was claimed.

        Claims nothing while an abandoned job process is still alive.
        """
        self.queue.reap()
        with self._lock:
            self.abandoned[:] = [p for p in self.abandoned if p.is_alive()]
            wedged = bool(self.abandoned)
        if wedged:
            log.error("not claiming: %d abandoned job process(es) still alive", len(self.abandoned))
            return False
        job = self.queue.claim(self.worker_id, self.classes, self.lease_seconds)
        if job is None:
            return False
        self._execute(job)
        return True

    def run_forever(self) -> None:
        log.info("worker %s serving %s", self.worker_id, ",".join(self.classes))
        while not self.stop.is_set():
            self.last_loop = time.monotonic()
            try:
                busy = self.run_once()
            except Exception:  # noqa: BLE001 - keep serving; the janitor recovers leases
                log.exception("worker loop error")
                busy = False
            if not busy:
                self.stop.wait(self.poll_seconds)

    def _execute(self, job: Job) -> None:
        self.busy = True
        try:
            self._execute_job(job)
        finally:
            self.busy = False
            self.last_loop = time.monotonic()

    def _complete(self, job: Job, *, result: dict[str, Any] | None = None, error: str | None = None) -> bool:
        return self.queue.complete(job.id, worker_id=self.worker_id, attempt=job.attempts, result=result, error=error)

    def _fail(self, job: Job, message: str) -> None:
        """Record a failed job on its run and complete it, while this attempt holds the lease (SF2)."""
        lease = {"worker_id": self.worker_id, "attempt": job.attempts}
        if job.run_id is not None:
            try:
                if self.queue.emit(job, job.run_id, job.tenant_id, "log", {
                    "type": "log", "module": "M7", "level": "error", "text": message, "at": _now(),
                }, **lease) and self.queue.set_run_status(job.run_id, "failed", job_id=job.id, **lease):
                    self.queue.emit(job, job.run_id, job.tenant_id, "status",
                                    {"type": "status", "status": "failed", "at": _now()}, **lease)
            except Exception:  # noqa: BLE001
                log.exception("could not record failure for run %s", job.run_id)
        if not self._complete(job, error=message[:2000]):
            log.warning("job %s: lease no longer held; failure not recorded on the job", job.id)

    def _foreign_run(self, job: Job) -> str | None:
        """Why ``job`` may not touch its run (SEC-H2), or None when it may.

        A job runs only against a run that exists and belongs to the job's
        own tenant; anything else is a forged or corrupt job.
        """
        if job.run_id is None:
            return None
        owner = self.queue.run_tenant(job.run_id)
        if owner is None:
            return f"JOB_RUN_MISSING: job {job.id} names run {job.run_id!r}, which does not exist"
        if owner != job.tenant_id:
            return f"JOB_TENANT_MISMATCH: job {job.id} is not owned by the tenant of run {job.run_id!r}"
        return None

    def _execute_job(self, job: Job) -> None:
        refused = self._foreign_run(job)
        if refused is not None:
            # Fail the job only; the run (another tenant's, or none) is untouched.
            log.warning("job %s refused: %s", job.id, refused)
            self._complete(job, error=refused)
            return
        handler = self.handlers.get(job.kind)
        if handler is None:
            self._fail(job, f"NotImplementedError: no handler for job kind {job.kind!r}")
            return

        attempt = _Attempt(job, threading.Event())
        done = threading.Event()
        hb = threading.Thread(target=self._beat, args=(attempt, done), name=f"heartbeat-{job.id[:8]}", daemon=True)
        # Tenant context for the job (budget hook, P3-05; tenant-scoped stores).
        from .m8_agent.auth import reset_active_tenant, set_active_tenant

        tenant_token = set_active_tenant(job.tenant_id)
        hb.start()
        try:
            outcome, detail = self._run_child(attempt, handler)
        finally:
            done.set()
            hb.join(timeout=5)
            reset_active_tenant(tenant_token)

        if outcome == "done":
            if not self._complete(job, result=detail):
                log.warning("job %s finished after losing its lease; completion ignored", job.id)
            return
        if outcome == "error":
            log.warning("job %s failed: %s", job.id, detail)
        else:
            log.error("job %s abandoned: %s", job.id, detail)
        # Under a lost lease every write below is refused (another attempt or
        # a cancel owns the job now); otherwise the job and run fail.
        self._fail(job, detail)

    def _beat(self, attempt: _Attempt, done: threading.Event) -> None:
        """Renew the attempt's lease; a refusal marks it lost at once."""
        job = attempt.job
        while not done.wait(self.heartbeat_seconds):
            try:
                if not self.queue.heartbeat(job.id, self.worker_id, self.lease_seconds, attempt=job.attempts):
                    attempt.lost.set()
                    return
                if job.run_id is not None and not attempt.run_ended:
                    # Liveness for the run's streams (SF1): a long, quiet job
                    # is not an idle stream.
                    self.queue.emit(job, job.run_id, job.tenant_id, "heartbeat",
                                    {"type": "heartbeat", "at": _now()},
                                    worker_id=self.worker_id, attempt=job.attempts)
            except Exception:  # noqa: BLE001 - transient DB error; retry next beat
                log.warning("heartbeat failed for job %s", job.id, exc_info=True)

    def _run_child(self, attempt: _Attempt, handler: Handler) -> tuple[str, Any]:
        """Run ``handler`` in a child process until it reports, or until the
        attempt is abandoned: wall-clock limit, lost lease, the child dying,
        or any error while waiting. The child is stopped either way.

        Returns ("done", result) or ("error" | "abandoned", message).
        """
        job = attempt.job
        spec = _ChildSpec(
            job=job, handler=handler, parent_pid=os.getpid(),
            cpu_seconds=math.ceil(self.job_timeout_seconds * _cpu_count()) + _CPU_SLACK_SECONDS,
            budget_hook=_budget_hook_installed(), log_level=logging.getLogger().getEffectiveLevel(),
        )
        ours, theirs = _SPAWN.Pipe()
        proc = _SPAWN.Process(target=_child_main, args=(theirs, spec), name=f"job-{job.id[:8]}", daemon=True)
        finished = False
        try:
            try:
                proc.start()
            except Exception as exc:  # noqa: BLE001 - e.g. a handler that can't be pickled
                return "error", f"JOB_START_FAILED: could not start the job's process: {exc.__class__.__name__}: {exc}"
            finally:
                theirs.close()
            outcome = self._wait_child(attempt, proc, ours)
            finished = outcome[0] in ("done", "error")
            return outcome
        except Exception as exc:  # noqa: BLE001 - any error while waiting abandons the attempt
            attempt.lost.set()
            return "abandoned", f"JOB_ABANDONED: job {job.id} lost its worker's wait: {exc.__class__.__name__}: {exc}"
        finally:
            ours.close()
            self._stop_child(proc, graceful=finished)

    def _wait_child(self, attempt: _Attempt, proc: Any, conn: Connection) -> tuple[str, Any]:
        job = attempt.job
        deadline = time.monotonic() + self.job_timeout_seconds
        lost_lease = (
            f"JOB_LEASE_LOST: job {job.id} ({job.kind}) attempt {job.attempts} lost its lease "
            "(cancelled, reclaimed after it expired, or its run already ended); its process was stopped"
        )
        while True:
            if attempt.lost.is_set() and (
                attempt.refused_at is None or time.monotonic() - attempt.refused_at > _REFUSED_GRACE
            ):
                return "abandoned", lost_lease
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                attempt.lost.set()  # nothing the child asks for is applied from here on
                return "abandoned", (
                    f"JOB_TIMEOUT: job {job.id} ({job.kind}) exceeded the "
                    f"{self.job_timeout_seconds:g}s wall-clock limit; its process was stopped"
                )
            ready = wait_for([conn, proc.sentinel], timeout=min(remaining, 0.1))
            if conn in ready or conn.poll():
                try:
                    message = conn.recv()
                except EOFError:
                    message = None
                if message is None:
                    proc.join(_CHILD_EXIT_GRACE)
                    return "abandoned", f"JOB_CRASHED: job {job.id}'s process ended (exit code {proc.exitcode})"
                if message[0] == "call":
                    conn.send(self._serve(attempt, message[1], message[2]))
                    continue
                kind, detail = message
                if kind == "cancelled" or attempt.refused_at is not None:
                    attempt.lost.set()
                    return "abandoned", f"{lost_lease}: {detail}"
                return kind, detail
            if proc.sentinel in ready:
                proc.join(_CHILD_EXIT_GRACE)
                return "abandoned", f"JOB_CRASHED: job {job.id}'s process ended (exit code {proc.exitcode})"

    def _serve(self, attempt: _Attempt, name: str, args: tuple[Any, ...]) -> tuple[str, Any]:
        """Apply one request of the attempt's child under its lease, or refuse it."""
        job = attempt.job
        if attempt.lost.is_set():
            return "refused", f"{name} after job {job.id} was abandoned"
        lease = {"job_id": job.id, "worker_id": self.worker_id, "attempt": job.attempts}
        run_id = job.run_id
        try:
            if name == "job_status":
                return "ok", self.queue.job_status(job.id)
            if run_id is None or not args or args[0] != run_id:
                return "refused", f"{name}: job {job.id} may only write its own run"
            if name == "set_run_status":
                ok = self.queue.set_run_status(run_id, str(args[1]), **lease)
                attempt.run_ended = attempt.run_ended or (ok and str(args[1]) in TERMINAL_RUN_STATUSES)
            elif name == "save_result":
                ok = self.queue.save_result(run_id, args[1], **lease)
            elif name == "emit":
                ok = self.queue.emit(job, run_id, job.tenant_id, str(args[1]), args[2],
                                     worker_id=self.worker_id, attempt=job.attempts)
            elif name == "record_provenance":
                ok = self._record_provenance(attempt, args[1])
            else:
                return "refused", f"handlers may not call {name}"
        except Exception as exc:  # noqa: BLE001 - reported to the handler
            log.warning("job %s: %s failed", job.id, name, exc_info=True)
            return "error", f"{name} failed: {exc.__class__.__name__}: {exc}"
        if not ok:
            attempt.refused_at = time.monotonic()
            attempt.lost.set()  # nothing else this attempt asks for is applied
            return "refused", f"{name} refused: job {job.id} lost its lease or its run already ended"
        return "ok", None

    def _record_provenance(self, attempt: _Attempt, record: dict[str, Any]) -> bool:
        """Upload provenance.json and write its row, both under the attempt's lease (P3-03).

        The lease is checked (and renewed) immediately before the Storage
        put, so an attempt that was cancelled, timed out or reclaimed
        uploads nothing; the row is lease-checked again when written.
        """
        import json

        from .artifacts import ArtifactStore

        job = attempt.job
        assert job.run_id is not None
        if attempt.lost.is_set() or not self.queue.heartbeat(
            job.id, self.worker_id, self.lease_seconds, attempt=job.attempts,
        ):
            return False
        upload = ArtifactStore().put(
            job.run_id, "provenance.json", json.dumps(record, sort_keys=True, default=str).encode(),
        )
        return self.queue.save_provenance(
            job.run_id, job.tenant_id, record,
            artifact_path=upload.path, artifact_status=upload.status,
            job_id=job.id, worker_id=self.worker_id, attempt=job.attempts,
        )

    def _stop_child(self, proc: Any, *, graceful: bool) -> None:
        """Let a finished child exit; otherwise terminate, then kill it."""
        if proc._popen is None:  # never started
            return
        if graceful:
            proc.join(_CHILD_EXIT_GRACE)
        if proc.is_alive():
            proc.terminate()
            proc.join(_CHILD_KILL_WAIT)
        if proc.is_alive():
            proc.kill()
            proc.join(_CHILD_KILL_WAIT)
        if proc.is_alive():
            log.error("job process %s survived kill; not claiming until it exits", proc.pid)
            with self._lock:
                self.abandoned.append(proc)
            return
        proc.close()


def serve_health(worker: Worker, port: int, host: str = "0.0.0.0") -> Any:  # noqa: S104 - container port
    """Serve ``GET /healthz`` for ``worker`` on a daemon thread (P3-07).

    Containers and Cloud Run probe it: 200 ``{"status": "ok"}`` while the
    loop turns (or a job runs), 503 otherwise. It never touches the
    database; readiness of the queue is the API's ``/readyz``.
    """
    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class _Health(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - http.server API
            if self.path.split("?", 1)[0] != "/healthz":
                self.send_error(404)
                return
            ok = worker.healthy()
            body = json.dumps({
                "status": "ok" if ok else "unhealthy",
                "worker_id": worker.worker_id,
                "classes": list(worker.classes),
                "busy": worker.busy,
            }).encode()
            self.send_response(200 if ok else 503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_: Any) -> None:  # probes every few seconds: stay quiet
            return

    server = ThreadingHTTPServer((host, port), _Health)
    threading.Thread(target=server.serve_forever, name="worker-health", daemon=True).start()
    return server


def main(argv: list[str] | None = None) -> int:
    import argparse
    import signal

    parser = argparse.ArgumentParser(prog="qcompass_worker", description=__doc__.splitlines()[0])
    parser.add_argument("--classes", default="cpu", help="comma-separated compute classes")
    parser.add_argument("--lease-seconds", type=int, default=60)
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    parser.add_argument("--once", action="store_true", help="drain the queue, then exit")
    parser.add_argument(
        "--job-timeout-seconds", type=float, default=None,
        help="wall-clock limit per job (default: $QCOMPASS_JOB_TIMEOUT_SECONDS or 3600)",
    )
    parser.add_argument(
        "--health-port", type=int,
        default=int(os.environ["PORT"]) if os.environ.get("PORT", "").isdigit() else None,
        help="serve GET /healthz on this port (default: $PORT when set, e.g. in containers)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=os.environ.get("QCOMPASS_LOG_LEVEL", "INFO"))
    classes = tuple(c.strip() for c in args.classes.split(",") if c.strip())
    # P3-05: QPU jobs routed in this process are gated by tenant budgets too.
    from .m8_agent.auth import install_budget_hook

    install_budget_hook()
    try:
        worker = Worker(
            JobQueue(), classes, lease_seconds=args.lease_seconds, poll_seconds=args.poll_seconds,
            job_timeout_seconds=args.job_timeout_seconds,
        )
    except ValueError as exc:  # SEC-L3: an invalid time limit; refuse to start
        parser.error(str(exc))
    if args.once:
        while worker.run_once():
            pass
        return 0
    signal.signal(signal.SIGTERM, lambda *_: worker.stop.set())
    signal.signal(signal.SIGINT, lambda *_: worker.stop.set())
    health = serve_health(worker, args.health_port) if args.health_port else None
    try:
        worker.run_forever()
    finally:
        if health is not None:
            health.shutdown()
            health.server_close()
    return 0


__all__ = [
    "DEFAULT_JOB_TIMEOUT_SECONDS",
    "MAX_JOB_TIMEOUT_SECONDS",
    "HANDLERS",
    "JobCancelled",
    "JobContext",
    "Worker",
    "job_timeout_seconds_default",
    "main",
    "resolve_simulation",
    "serve_health",
]
