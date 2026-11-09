"""Job handlers for the Gate 1 round-2 worker tests (test_security_gate1_worker.py).

They are module-level functions so a worker can hand them to a job's child
process (which imports them by name), and they use only the handler API
that existed before the fix (``ctx.job``, ``ctx.run_id``, ``ctx.emit``,
``ctx.queue.set_run_status`` / ``save_result``), so the same tests also run
against the pre-fix worker, where handlers ran on a thread. They coordinate
with the test through files in the directory named by the job payload's
``gates`` key, which works across threads and processes alike.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# The attributes of JobQueue a handler must not reach through ctx.queue.
PASS_THROUGH = ("complete", "heartbeat", "cancel_run", "enqueue_run", "_emit", "engine")


def _gates(ctx: Any) -> Path:
    return Path(ctx.job.payload["gates"])


def _now() -> str:
    return datetime.now(UTC).isoformat()


def mark(ctx: Any, name: str, text: str = "") -> None:
    (_gates(ctx) / name).write_text(text)


def wait_gate(ctx: Any, name: str, timeout: float = 60.0) -> None:
    path = _gates(ctx) / name
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() > deadline:
            raise TimeoutError(f"gate {name} never opened")
        time.sleep(0.02)


def gil_hog(ctx: Any) -> dict[str, Any]:
    """One long C call that holds the GIL (the custom-potential bypass's big pow)."""
    ctx.queue.set_run_status(ctx.run_id, "running")
    mark(ctx, "started")
    _ = 9 ** (2 * 9**7)
    mark(ctx, "finished")
    return {}


def by_payload(ctx: Any) -> dict[str, Any]:
    """Run the handler of this module named by the job payload's ``handler``."""
    handler = globals()[ctx.job.payload["handler"]]
    return handler(ctx)  # type: ignore[no-any-return]


def ignore_cancel_and_sleep(ctx: Any) -> dict[str, Any]:
    """Never checks for cancellation; sleeps, then tries to finish."""
    ctx.queue.set_run_status(ctx.run_id, "running")
    mark(ctx, "started")
    time.sleep(float(ctx.job.payload.get("sleep", 20)))
    ctx.queue.save_result(ctx.run_id, {"late": True})
    ctx.queue.set_run_status(ctx.run_id, "completed")
    mark(ctx, "finished")
    return {}


def keep_ticking(ctx: Any) -> dict[str, Any]:
    """Runs until stopped (or 30 s), rewriting a file every 20 ms so the test can see it is alive."""
    ctx.queue.set_run_status(ctx.run_id, "running")
    tick = _gates(ctx) / "tick"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        tick.write_text(repr(time.monotonic()))
        time.sleep(0.02)
    return {}


def quick(ctx: Any) -> dict[str, Any]:
    ctx.queue.set_run_status(ctx.run_id, "running")
    mark(ctx, f"ran-{ctx.job.id}", repr(time.time()))
    ctx.queue.set_run_status(ctx.run_id, "completed")
    ctx.emit("status", {"type": "status", "status": "completed", "at": _now()})
    return {"ok": True}


def attempt_gated(ctx: Any) -> dict[str, Any]:
    """Attempt N waits for the file ``go-N``, then writes its result and completes."""
    n = ctx.job.attempts
    ctx.queue.set_run_status(ctx.run_id, "running")
    mark(ctx, f"started-{n}")
    wait_gate(ctx, f"go-{n}")
    try:
        ctx.queue.save_result(ctx.run_id, {"from": f"attempt-{n}"})
        ctx.queue.set_run_status(ctx.run_id, "completed")
        outcome = "wrote"
    except Exception as exc:  # noqa: BLE001 - the outcome is what the test checks
        outcome = type(exc).__name__
    mark(ctx, f"outcome-{n}", outcome)
    return {"attempt": n}


def probe_pass_through(ctx: Any) -> dict[str, Any]:
    """Which JobQueue internals a handler can reach, and whether it can cancel another run."""
    exposed = []
    for name in PASS_THROUGH:
        try:
            getattr(ctx.queue, name)
        except AttributeError:
            continue
        exposed.append(name)
    try:
        ctx.queue.cancel_run(ctx.job.payload["victim"])
    except Exception:  # noqa: BLE001
        pass
    mark(ctx, "exposed", ",".join(exposed))
    return {}


def provenance_after_gate(ctx: Any) -> dict[str, Any]:
    """Waits for ``go``, then records provenance (upload + row) as the built-in handlers do."""
    from ucgle_f1 import worker

    ctx.queue.set_run_status(ctx.run_id, "running")
    mark(ctx, "started")
    wait_gate(ctx, "go")
    try:
        worker._record_provenance(ctx, {"classical_reference_hash": "late"})
        outcome = "recorded"
    except Exception as exc:  # noqa: BLE001
        outcome = type(exc).__name__
    mark(ctx, "outcome", outcome)
    return {}


def quiet_then_complete(ctx: Any) -> dict[str, Any]:
    """A healthy run that emits nothing for a while (sim.run of a long domain run)."""
    ctx.queue.set_run_status(ctx.run_id, "running")
    ctx.emit("status", {"type": "status", "status": "running", "at": _now()})
    time.sleep(float(ctx.job.payload.get("sleep", 4)))
    ctx.queue.save_result(ctx.run_id, {"status_detail": "completed"})
    ctx.queue.set_run_status(ctx.run_id, "completed")
    ctx.emit("status", {"type": "status", "status": "completed", "at": _now()})
    return {}


def sleep_then_complete_status(ctx: Any) -> dict[str, Any]:
    """Sleeps, then sets the run completed and emits its status (an in-flight finish)."""
    time.sleep(float(ctx.job.payload.get("sleep", 0.3)))
    ctx.queue.set_run_status(ctx.run_id, "completed")
    ctx.emit("status", {"type": "status", "status": "completed", "at": _now()})
    return {}


def cpu_limit(ctx: Any) -> dict[str, Any]:
    import resource

    soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
    return {"soft": soft, "hard": hard}


def emit_after_gate(ctx: Any) -> dict[str, Any]:
    """Waits for ``go``, then appends one log event (a worker write racing a cancel)."""
    ctx.queue.set_run_status(ctx.run_id, "running")
    mark(ctx, "started")
    wait_gate(ctx, "go")
    try:
        ctx.emit("log", {"type": "log", "module": "M7", "level": "info", "text": "late", "at": _now()})
        outcome = "emitted"
    except Exception as exc:  # noqa: BLE001
        outcome = type(exc).__name__
    mark(ctx, "outcome", outcome)
    return {}
