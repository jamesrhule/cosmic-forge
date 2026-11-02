"""Gate 1 security review, round 2, worker lane (cluster c3): one regression test per finding.

Each test drives only APIs that existed at 9c6bf4c (the worker, its handler
API, JobQueue's pre-fix signatures, HTTP and SQL), fails there for the
finding's own reason, and passes with the fix. Handlers live in
``gate1_worker_handlers`` so a job's child process can import them. IDs
match ``docs/build/lanes/W1-sec-worker.md`` and
``docs/build/evidence/W1-security-round2-worker.md``.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import gate1_worker_handlers as handlers
import psycopg
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from ucgle_f1.db.migrate import apply_migrations, rollback
from ucgle_f1.jobs import JobQueue
from ucgle_f1.m8_agent.auth import get_auth_store
from ucgle_f1.m8_agent.server import build_app
from ucgle_f1.worker import Worker


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("BLOCKED-ON-JAMES:DATABASE_URL (no test Postgres)")
    return url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture
def acme(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """Tenant acme in a production configuration, with an API client and a gate directory."""
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    monkeypatch.delenv("QCOMPASS_ENV", raising=False)
    monkeypatch.delenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", raising=False)
    store = get_auth_store()
    tok = store.issue("acme", scopes=["read", "run"])
    gates = tmp_path / "gates"
    gates.mkdir()
    return {
        "uuid": store.ensure_tenant("acme"),
        "headers": {"Authorization": f"Bearer {tok.token_id}", "X-QCompass-Tenant": "acme"},
        "gates": gates,
    }


def _enqueue(
    q: JobQueue, acme: dict[str, Any], run_id: str, *, max_attempts: int = 3,
    kind: str = "qcompass.run", **payload: Any,
) -> str:
    config = ({"domain": "chemistry", "kind": kind, "manifest": {}} if kind == "qcompass.run"
              else {"domain": "cosmology", "kind": kind})
    return q.enqueue_run(
        run_id=run_id, tenant_uuid=acme["uuid"], kind=kind,
        payload={"domain": "chemistry", "manifest": {}, "gates": str(acme["gates"]), **payload},
        label=run_id, config=config, max_attempts=max_attempts, enforce_limits=False,
    )


def _job_row(run_id: str) -> tuple[str, str | None]:
    with psycopg.connect(_url()) as conn:
        row = conn.execute("select status::text, error from public.jobs where run_id = %s", (run_id,)).fetchone()
    return row[0], row[1]


def _events(run_id: str) -> list[tuple[str, dict[str, Any]]]:
    with psycopg.connect(_url()) as conn:
        rows = conn.execute(
            "select type, payload from public.job_events where run_id = %s order by id", (run_id,),
        ).fetchall()
    return [(r[0], r[1]) for r in rows]


def _wait_file(path: Path, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists():
        assert time.monotonic() < deadline, f"{path.name} never appeared"
        time.sleep(0.02)


def _in_thread(fn: Any) -> tuple[threading.Thread, dict[str, Any]]:
    out: dict[str, Any] = {}

    def run() -> None:
        try:
            out["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - re-raised by the test
            out["error"] = exc

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t, out


def _bounded(fn: Any, timeout: float) -> Any:
    t, out = _in_thread(fn)
    t.join(timeout)
    assert not t.is_alive(), f"did not finish within {timeout:g}s"
    if "error" in out:
        raise out["error"]
    return out["value"]


# ── c3-expr-caps: custom-potential caps can't be bypassed ─────────────


@pytest.mark.parametrize("source", [
    "phi^(9^9^9)",                                   # '^' became '**' (convert_xor)
    "phi**(Rational(9)**Rational(9)**Rational(9))",  # constants wrapped in an allowed call
    "phi**(sqrt(81)**sqrt(81)**sqrt(81))",
    "(((((Rational(9)**64)**64)**64)**64)**64)",     # a nested tower of allowed powers
    "Rational(9)**(phi - phi + 9**9)",               # an exponent that only looks symbolic
    "exp(9**9*log(9))",                              # sympy rewrites exp(k*log(x)) as x**k
])
def test_c3_expr_caps_bypasses_are_rejected_quickly(source: str) -> None:
    code = (
        "import sys\n"
        "from ucgle_f1.m2_scalar.potentials import _custom_expr\n"
        "try:\n"
        "    _custom_expr(sys.argv[1])\n"
        "except ValueError as exc:\n"
        "    print('rejected:', exc)\n"
        "else:\n"
        "    print('accepted')\n"
    )
    try:
        out = subprocess.run(
            [sys.executable, "-c", code, source], capture_output=True, text=True, timeout=20, check=True,
        ).stdout
    except subprocess.TimeoutExpired:
        pytest.fail(f"parsing {source!r} did not finish: sympy evaluated an unbounded constant")
    assert out.startswith("rejected: custom potential:"), out


def test_c3_expr_caps_real_potentials_compile_as_before() -> None:
    """Accepted potentials are the expressions sympify built before the fix, symbol for symbol."""
    import sympy as sp

    from ucgle_f1.m2_scalar.potentials import _custom_expr

    phi = sp.Symbol("phi", real=True)
    names = {n: sp.Symbol(n, real=True) for n in ("m", "a", "b", "L", "f_a", "M", "V0", "mu")}
    for source in ("m**2*phi**2/2", "a * phi**2 + b * cos(phi)", "L**4*(1 - cos(phi/f_a))",
                   "phi**64", "(phi**2)**30", "Rational(3, 4)*M**2*(1 - exp(-sqrt(Rational(2, 3))*phi))**2",
                   "1e-10*phi**4 + 1.3e-5", "V0*(1 - (phi/mu)**4)", "tanh(phi/sqrt(6))**2",
                   "pi*phi**2 + log(cosh(phi))", "exp(-2*log(phi))", "phi**(1/2) - 2.5e-3*phi"):
        symbols = {"phi": phi, **names}
        expected = sp.sympify(source, locals={**symbols, "Rational": sp.Rational, "sqrt": sp.sqrt,
                                              "exp": sp.exp, "cos": sp.cos, "tanh": sp.tanh,
                                              "log": sp.log, "cosh": sp.cosh, "pi": sp.pi})
        got = _custom_expr(source, symbols)
        assert got == expected and sp.srepr(got) == sp.srepr(expected), source


# ── c3-gil-timeout: a GIL-holding handler is stopped at its limit ─────


def test_c3_gil_holding_handler_is_stopped_at_its_time_limit(acme: dict[str, Any]) -> None:
    q = JobQueue()
    _enqueue(q, acme, "run_gil")
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.gil_hog}, lease_seconds=2,
                    heartbeat_seconds=0.2, job_timeout_seconds=1.0, poll_seconds=0.05)
    gaps: list[float] = []
    stop = threading.Event()

    def ticker() -> None:  # anything else in the worker process: heartbeat, /healthz
        last = time.monotonic()
        while not stop.is_set():
            time.sleep(0.05)
            now = time.monotonic()
            gaps.append(now - last)
            last = now

    tick = threading.Thread(target=ticker, daemon=True)
    tick.start()
    try:
        assert worker.run_once() is True
    finally:
        stop.set()
        tick.join()
    status, error = _job_row("run_gil")
    assert status == "failed" and error is not None and error.startswith("JOB_TIMEOUT"), (status, error)
    assert q.get_run("run_gil").status == "failed"  # type: ignore[union-attr]
    assert max(gaps) < 1.0, f"the worker process stalled {max(gaps):.1f}s while the handler held a GIL"
    assert not (acme["gates"] / "finished").exists(), "the handler was stopped, not waited for"


def test_c3_gil_job_process_has_a_cpu_limit(acme: dict[str, Any]) -> None:
    """Defence in depth: RLIMIT_CPU bounds a job process even if the worker is gone."""
    q = JobQueue()
    _enqueue(q, acme, "run_rlimit")
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.cpu_limit}, job_timeout_seconds=7.0)
    assert worker.run_once() is True
    with psycopg.connect(_url()) as conn:
        result = conn.execute("select result from public.jobs where run_id = 'run_rlimit'").fetchone()[0]
    cores = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)
    assert 0 < result["soft"] <= math.ceil(7.0 * cores) + 30
    assert result["soft"] <= result["hard"] <= result["soft"] + 5


# ── c3-timeout-parse: invalid time limits refuse to start ─────────────


@pytest.mark.parametrize("raw", ["inf", "nan", "1e10"])
def test_c3_timeout_parse_env_values_that_break_the_wait_are_refused(
    raw: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QCOMPASS_JOB_TIMEOUT_SECONDS", raw)
    with pytest.raises(ValueError, match="QCOMPASS_JOB_TIMEOUT_SECONDS"):
        Worker(JobQueue(), ("cpu",))


@pytest.mark.parametrize("value", [-1.0, 0.0, math.inf, math.nan, 1e10])
def test_c3_timeout_parse_constructor_values_are_refused(value: float) -> None:
    with pytest.raises(ValueError, match="job_timeout_seconds"):
        Worker(JobQueue(), ("cpu",), job_timeout_seconds=value)


def test_c3_timeout_parse_cli_refuses_to_start(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ucgle_f1.m8_agent import auth
    from ucgle_f1.worker import main

    # main() installs the router's budget hook process-wide; not in the test process.
    monkeypatch.setattr(auth, "install_budget_hook", lambda: False)
    with pytest.raises(SystemExit) as refused:
        main(["--once", "--job-timeout-seconds", "-1"])
    assert refused.value.code == 2
    assert "job_timeout_seconds" in capsys.readouterr().err


def test_c3_timeout_parse_an_error_while_waiting_fails_the_job(
    acme: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-fix guard: any exception while the worker waits abandons the attempt and fails the job."""
    import ucgle_f1.worker as worker_mod

    def broken_wait(*_: Any, **__: Any) -> Any:
        raise OverflowError("timestamp out of range for platform time_t")

    q = JobQueue()
    _enqueue(q, acme, "run_wait_error", sleep=20)
    monkeypatch.setattr(worker_mod, "wait_for", broken_wait)
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.ignore_cancel_and_sleep})
    assert _bounded(worker.run_once, 30) is True
    status, error = _job_row("run_wait_error")
    assert status == "failed" and error is not None and error.startswith("JOB_ABANDONED"), (status, error)
    assert q.get_run("run_wait_error").status == "failed"  # type: ignore[union-attr]


# ── c3-lock-order: cancel vs dead-letter ──────────────────────────────


def test_c3_lock_order_cancel_racing_a_dead_letter_does_not_deadlock(acme: dict[str, Any]) -> None:
    url = _url()
    q = JobQueue()
    _enqueue(q, acme, "run_dl", max_attempts=1)
    assert q.claim("dying", ["cpu"], lease_seconds=1) is not None
    time.sleep(1.2)  # the worker died; its last attempt's lease expired
    # Hold the janitor between its job-row lock and its run update.
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(
            "create or replace function public._c3_slow_incident() returns trigger language plpgsql "
            "as $$ begin perform pg_sleep(1.5); return new; end $$"
        )
        conn.execute(
            "create trigger _c3_slow_incident before insert on public.system_incidents "
            "for each row execute function public._c3_slow_incident()"
        )
    out: dict[str, Any] = {}
    try:
        def reap() -> None:
            try:
                out["reap"] = q.reap()
            except Exception as exc:  # noqa: BLE001
                out["reap"] = type(getattr(exc, "orig", exc)).__name__

        t = threading.Thread(target=reap)
        t.start()
        time.sleep(0.4)
        try:
            out["cancel"] = q.cancel_run("run_dl")
        except Exception as exc:  # noqa: BLE001
            out["cancel"] = type(getattr(exc, "orig", exc)).__name__
        t.join(30)
    finally:
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("drop trigger if exists _c3_slow_incident on public.system_incidents")
            conn.execute("drop function if exists public._c3_slow_incident()")
    assert out == {"reap": 1, "cancel": False}, f"cancel and the janitor deadlocked: {out}"
    assert q.get_run("run_dl").status == "failed"  # type: ignore[union-attr]
    assert _events("run_dl")[-1][1]["status"] == "failed"


# ── c3-attempt-lease: an earlier attempt never writes ─────────────────


def test_c3_attempt_lease_a_stale_attempt_with_the_same_worker_id_cannot_write(acme: dict[str, Any]) -> None:
    q = JobQueue()
    job_id = _enqueue(q, acme, "run_attempts")
    gates = acme["gates"]
    common = {"worker_id": "fixed-worker-id", "job_timeout_seconds": 60, "poll_seconds": 0.05,
              "handlers": {"qcompass.run": handlers.attempt_gated}}
    # Attempt 1 never renews its 1 s lease (a worker stuck, or partitioned from the DB).
    first = Worker(q, ("cpu",), lease_seconds=1, heartbeat_seconds=3600, **common)
    t1, _ = _in_thread(first.run_once)
    _wait_file(gates / "started-1")
    time.sleep(1.2)
    assert q.reap() == 1, "the janitor requeues attempt 1's job"
    # The same worker id (a restarted worker that reuses it) claims attempt 2.
    second = Worker(q, ("cpu",), lease_seconds=30, **common)
    t2, _ = _in_thread(second.run_once)
    _wait_file(gates / "started-2")
    (gates / "go-1").write_text("")  # attempt 1 wakes up and tries to finish
    t1.join(30)
    assert not t1.is_alive()
    assert q.result("run_attempts") is None, "attempt 1 stored a result while attempt 2 holds the job"
    assert q.get_run("run_attempts").status == "running"  # type: ignore[union-attr]
    assert q.job_status(job_id) == "running", "attempt 1 completed the job attempt 2 is running"
    (gates / "go-2").write_text("")
    t2.join(30)
    assert not t2.is_alive()
    assert q.result("run_attempts") == {"from": "attempt-2"}
    assert q.get_run("run_attempts").status == "completed"  # type: ignore[union-attr]
    assert q.job_status(job_id) == "succeeded"


def test_c3_attempt_lease_a_terminal_run_never_changes_status(acme: dict[str, Any]) -> None:
    q = JobQueue()
    _enqueue(q, acme, "run_sticky")
    _enqueue(q, acme, "run_canceled")
    assert q.set_run_status("run_sticky", "running") is True
    assert q.set_run_status("run_sticky", "failed") is True
    for later in ("completed", "running", "canceled", "queued"):
        assert q.set_run_status("run_sticky", later) is False, f"failed -> {later}"
    assert q.save_result("run_sticky", {"late": True}) is False, "a terminal run's result never changes"
    assert q.get_run("run_sticky").status == "failed"  # type: ignore[union-attr]
    assert q.result("run_sticky") is None
    assert q.cancel_run("run_canceled") is True
    assert q.set_run_status("run_canceled", "completed") is False
    # The same rule holds for every writer, in SQL.
    with psycopg.connect(_url()) as conn, pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("update public.runs set status = 'running' where id = 'run_sticky'")
    assert q.get_run("run_sticky").status == "failed"  # type: ignore[union-attr]


class _SlowQueue(JobQueue):
    """Delays stand in for DB latency: a slow 'completed' write, a slow failed completion."""

    def __init__(self) -> None:
        super().__init__()
        self.writes: list[tuple[str, bool]] = []

    def set_run_status(self, run_id: str, status: str, **kw: Any) -> bool:
        if status == "completed":
            time.sleep(0.7)
        ok = super().set_run_status(run_id, status, **kw)
        self.writes.append((status, ok))
        return ok

    def complete(self, job_id: str, **kw: Any) -> bool:
        if kw.get("error"):
            time.sleep(0.5)
        return super().complete(job_id, **kw)


def test_c3_attempt_lease_an_in_flight_write_never_lands_after_the_failure(acme: dict[str, Any]) -> None:
    q = _SlowQueue()
    _enqueue(q, acme, "run_inflight", sleep=0.3)
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.sleep_then_complete_status},
                    job_timeout_seconds=0.5, poll_seconds=0.05)
    assert worker.run_once() is True
    time.sleep(1.5)  # anything still in flight lands now
    terminal = [status for status, ok in q.writes if ok and status in ("completed", "failed")]
    assert len(terminal) == 1, f"a terminal run was overwritten: {q.writes}"
    final = q.get_run("run_inflight").status  # type: ignore[union-attr]
    assert final == terminal[0]
    status_events = [p.get("status") for t, p in _events("run_inflight") if t == "status"]
    assert set(status_events) - {"queued", "running"} <= {final}, (final, status_events)


def test_c3_attempt_lease_no_worker_event_lands_after_a_cancel(acme: dict[str, Any]) -> None:
    """The lease check and the write it guards are one locked step (SF2 residual 2)."""
    url = _url()
    q = JobQueue()
    _enqueue(q, acme, "run_order")
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.emit_after_gate},
                    heartbeat_seconds=60, job_timeout_seconds=60)
    t, _ = _in_thread(worker.run_once)
    _wait_file(acme["gates"] / "started")
    # Hold the next job_events insert statement for 1.5 s, before it takes its
    # id (a sequence, not a row, picks the first statement: nothing else waits).
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("create sequence public._c3_slow_once")
        conn.execute(
            "create function public._c3_slow_once() returns trigger language plpgsql as $$ begin "
            "if nextval('public._c3_slow_once') = 1 then perform pg_sleep(1.5); end if; "
            "return null; end $$"
        )
        conn.execute(
            "create trigger _c3_slow_once before insert on public.job_events "
            "for each statement execute function public._c3_slow_once()"
        )
    try:
        (acme["gates"] / "go").write_text("")
        time.sleep(0.4)  # the worker's event insert is waiting in the trigger
        assert q.cancel_run("run_order") is True
        t.join(30)
    finally:
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("drop trigger if exists _c3_slow_once on public.job_events")
            conn.execute("drop function if exists public._c3_slow_once()")
            conn.execute("drop sequence if exists public._c3_slow_once")
    events = _events("run_order")
    assert events[-1] == ("status", {**events[-1][1], "status": "canceled"}), (
        f"a worker event landed after the run was canceled: {[e[0] for e in events]}"
    )


# ── c3-guarded-queue: handlers can't reach queue internals ────────────


def test_c3_guarded_queue_handlers_cannot_reach_queue_internals(acme: dict[str, Any]) -> None:
    q = JobQueue()
    _enqueue(q, acme, "run_victim")
    with psycopg.connect(_url(), autocommit=True) as conn:
        # Not claimable by this worker's class: only the probe runs.
        conn.execute("update public.jobs set compute_class = 'edge' where run_id = 'run_victim'")
    _enqueue(q, acme, "run_probe", victim="run_victim")
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.probe_pass_through}, job_timeout_seconds=60)
    assert worker.run_once() is True
    assert (acme["gates"] / "exposed").read_text() == "", "handlers reach JobQueue internals"
    assert q.get_run("run_victim").status == "queued", "a handler canceled another run"  # type: ignore[union-attr]


# ── c3-stream-bounds: long runs stream to the end; bounds always hold ─


def _sse(client: TestClient, run_id: str, headers: dict[str, str], domain: str = "chemistry") -> str:
    with client.stream("GET", f"/api/qcompass/domains/{domain}/runs/{run_id}/stream", headers=headers) as r:
        return "".join(r.iter_text())


def _ws(client: TestClient, run_id: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    got: list[dict[str, Any]] = []
    with client.websocket_connect(f"/ws/qcompass/domains/chemistry/runs/{run_id}/events", headers=headers) as w:
        try:
            while True:
                got.append(w.receive_json())
        except WebSocketDisconnect:
            return got


def _legacy(run_id: str) -> list[Any]:
    from ucgle_f1.m8_agent.runs import RunRegistry

    async def collect() -> list[Any]:
        return [ev async for ev in RunRegistry().stream(run_id, tenant="acme")]

    return asyncio.run(collect())


def test_c3_stream_idle_a_long_quiet_run_is_not_aborted(
    acme: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QCOMPASS_STREAM_IDLE_SECONDS", "1.5")
    client = TestClient(build_app())
    q = JobQueue()
    _enqueue(q, acme, "run_quiet", sleep=4)
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.quiet_then_complete},
                    heartbeat_seconds=0.3, job_timeout_seconds=60)
    t, _ = _in_thread(worker.run_once)
    text = _bounded(lambda: _sse(client, "run_quiet", acme["headers"]), 40)
    t.join(30)
    assert "STREAM_ABORTED" not in text, "a healthy run's stream was aborted as idle"
    assert '"status": "completed"' in text and text.rstrip().endswith("data: {}")
    assert "event: heartbeat" not in text, "liveness rows are not sent to clients"


def test_c3_stream_max_bound_holds_while_events_keep_arriving(
    acme: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QCOMPASS_STREAM_IDLE_SECONDS", "30")
    monkeypatch.setenv("QCOMPASS_STREAM_MAX_SECONDS", "1")
    client = TestClient(build_app())
    q = JobQueue()
    _enqueue(q, acme, "run_chatty")
    _enqueue(q, acme, "run_chatty_legacy", kind="ucgle_f1.run")
    stop = threading.Event()

    def chatter() -> None:
        while not stop.wait(0.1):
            for run_id in ("run_chatty", "run_chatty_legacy"):
                q.emit(None, run_id, acme["uuid"], "log", {
                    "type": "log", "module": "M1", "level": "info", "text": "tick", "at": "2026-11-02T00:00:00Z",
                })

    feeder = threading.Thread(target=chatter, daemon=True)
    feeder.start()
    try:
        text = _bounded(lambda: _sse(client, "run_chatty", acme["headers"]), 8)
        assert "STREAM_ABORTED" in text and "QCOMPASS_STREAM_MAX_SECONDS" in text
        msgs = _bounded(lambda: _ws(client, "run_chatty", acme["headers"]), 8)
        assert msgs[-1]["event"] == "error" and msgs[-1]["data"]["code"] == "STREAM_ABORTED"
        from ucgle_f1.domain import ServiceError

        with pytest.raises(ServiceError) as aborted:
            _bounded(lambda: _legacy("run_chatty_legacy"), 8)
        assert aborted.value.code == "STREAM_ABORTED"
    finally:
        stop.set()
        feeder.join()


def test_c3_stream_a_run_that_ended_without_a_terminal_event_ends_its_streams(acme: dict[str, Any]) -> None:
    client = TestClient(build_app())
    q = JobQueue()
    _enqueue(q, acme, "run_silent_end")
    _enqueue(q, acme, "run_silent_legacy", kind="ucgle_f1.run")
    for run_id in ("run_silent_end", "run_silent_legacy"):
        # The worker set the status, then died before writing the status event.
        assert q.set_run_status(run_id, "running") is True
        assert q.set_run_status(run_id, "failed") is True
    text = _bounded(lambda: _sse(client, "run_silent_end", acme["headers"]), 15)
    assert '"status": "failed"' in text and text.rstrip().endswith("data: {}")
    assert "STREAM_ABORTED" not in text
    msgs = _bounded(lambda: _ws(client, "run_silent_end", acme["headers"]), 15)
    assert msgs[-1]["event"] == "status" and msgs[-1]["data"]["status"] == "failed"
    events = _bounded(lambda: _legacy("run_silent_legacy"), 15)
    assert events[-1].type == "status" and events[-1].status == "failed"


# ── c3-claim-after-abandon: no work beside an abandoned job ───────────


def test_c3_claim_a_lost_lease_ends_the_wait_at_once(acme: dict[str, Any]) -> None:
    q = JobQueue()
    _enqueue(q, acme, "run_lost", sleep=20)
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.ignore_cancel_and_sleep},
                    lease_seconds=5, heartbeat_seconds=0.2, job_timeout_seconds=60)
    t, _ = _in_thread(worker.run_once)
    _wait_file(acme["gates"] / "started")
    assert q.cancel_run("run_lost") is True
    started = time.monotonic()
    t.join(5)
    assert not t.is_alive(), "the worker kept waiting on a job whose lease it lost"
    assert time.monotonic() - started < 5
    assert q.result("run_lost") is None
    assert q.get_run("run_lost").status == "canceled"  # type: ignore[union-attr]
    assert worker.healthy() is True


def test_c3_claim_no_new_job_runs_beside_an_abandoned_one(acme: dict[str, Any]) -> None:
    q = JobQueue()
    _enqueue(q, acme, "run_tick", handler="keep_ticking")
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.by_payload},
                    job_timeout_seconds=2.0, poll_seconds=0.05)
    assert worker.run_once() is True  # times out and abandons run_tick
    assert _job_row("run_tick")[1].startswith("JOB_TIMEOUT")  # type: ignore[union-attr]
    _enqueue(q, acme, "run_next", handler="quick")
    tick = acme["gates"] / "tick"
    assert tick.exists(), "run_tick's handler ran before its time limit"
    before = tick.read_text()
    assert worker.run_once() is True
    time.sleep(0.3)
    assert tick.read_text() == before, "the abandoned handler still runs beside the next job"
    assert q.get_run("run_next").status == "completed"  # type: ignore[union-attr]


def test_c3_claim_nothing_while_an_abandoned_job_is_alive(acme: dict[str, Any]) -> None:
    q = JobQueue()
    _enqueue(q, acme, "run_waiting", handler="quick")
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.by_payload}, poll_seconds=0.05)
    release = threading.Event()
    survivor = threading.Thread(target=release.wait, args=(30,), daemon=True)  # a job that survived kill
    survivor.start()
    worker.abandoned.append(survivor)
    try:
        assert worker.run_once() is False, "claimed a job while an abandoned one is alive"
        assert q.get_run("run_waiting").status == "queued"  # type: ignore[union-attr]
        assert worker.healthy() is False
    finally:
        release.set()
        survivor.join()
    assert worker.run_once() is True
    assert q.get_run("run_waiting").status == "completed"  # type: ignore[union-attr]


# ── c3-provenance-upload: no upload once the lease is gone ─────────────


def test_c3_provenance_upload_needs_the_lease(acme: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from ucgle_f1 import artifacts

    uploads: list[str] = []

    def transport(req: httpx.Request) -> httpx.Response:
        uploads.append(req.url.path)
        return httpx.Response(200, json={"Key": req.url.path})

    real = artifacts.ArtifactStore.__init__
    monkeypatch.setattr(
        artifacts.ArtifactStore, "__init__",
        lambda self, **_: real(self, transport=httpx.MockTransport(transport)),
    )
    monkeypatch.setenv("SUPABASE_URL", "https://example-project.supabase.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    q = JobQueue()
    _enqueue(q, acme, "run_prov")
    # The heartbeat is slow, so only the upload path itself can notice the cancel.
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.provenance_after_gate},
                    heartbeat_seconds=60, job_timeout_seconds=60)
    t, _ = _in_thread(worker.run_once)
    _wait_file(acme["gates"] / "started")
    assert q.cancel_run("run_prov") is True
    (acme["gates"] / "go").write_text("")
    t.join(30)
    assert not t.is_alive()
    assert uploads == [], "provenance.json was uploaded for a canceled run"
    assert q.provenance("run_prov") is None


def test_r3b_provenance_upload_in_flight_when_the_lease_is_lost_leaves_no_object(
    acme: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Round 3B (c3-provenance-upload partial): the run is canceled while the Storage upload is
    in flight. The row is refused, and no object stays behind for the canceled run."""
    import httpx

    from ucgle_f1 import artifacts

    posted: list[str] = []
    deleted: list[str] = []
    in_flight, release = threading.Event(), threading.Event()

    def transport(req: httpx.Request) -> httpx.Response:
        if req.method == "DELETE":
            deleted.append(req.url.path)
            return httpx.Response(200, json={"message": "Successfully deleted"})
        posted.append(req.url.path)
        in_flight.set()
        release.wait(30)  # a slow Storage answer
        return httpx.Response(200, json={"Key": req.url.path})

    real = artifacts.ArtifactStore.__init__
    monkeypatch.setattr(
        artifacts.ArtifactStore, "__init__",
        lambda self, **_: real(self, transport=httpx.MockTransport(transport)),
    )
    monkeypatch.setenv("SUPABASE_URL", "https://example-project.supabase.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    q = JobQueue()
    _enqueue(q, acme, "run_prov_late")
    worker = Worker(q, ("cpu",), handlers={"qcompass.run": handlers.provenance_after_gate},
                    heartbeat_seconds=60, job_timeout_seconds=60)
    t, _ = _in_thread(worker.run_once)
    _wait_file(acme["gates"] / "started")
    (acme["gates"] / "go").write_text("")
    assert in_flight.wait(30), "the provenance upload never started"
    assert q.cancel_run("run_prov_late") is True
    release.set()
    t.join(30)
    assert not t.is_alive()
    assert q.get_run("run_prov_late").status == "canceled"  # type: ignore[union-attr]
    assert q.provenance("run_prov_late") is None
    live = sorted(set(posted) - set(deleted))
    assert live == [], f"an object stayed in run-artifacts for the canceled run: {live}"


@pytest.mark.parametrize("value", [10 ** 400, 1e-300, 0.05])
def test_r3b_timeout_parse_huge_ints_and_tiny_limits_are_refused(value: float) -> None:
    """Round 3B (c3-timeout-parse NIT): 10**400 raised OverflowError, 1e-300 was accepted."""
    with pytest.raises(ValueError, match="job_timeout_seconds"):
        Worker(JobQueue(), ("cpu",), job_timeout_seconds=value)


def test_r3b_timeout_parse_minimum_is_the_wait_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    from ucgle_f1 import worker as worker_mod

    assert worker_mod.MIN_JOB_TIMEOUT_SECONDS == 0.1
    assert Worker(JobQueue(), ("cpu",), job_timeout_seconds=0.1).job_timeout_seconds == 0.1
    monkeypatch.setenv("QCOMPASS_JOB_TIMEOUT_SECONDS", "1e-300")
    with pytest.raises(ValueError, match="QCOMPASS_JOB_TIMEOUT_SECONDS"):
        Worker(JobQueue(), ("cpu",))


# ── c3-healthy-race: /healthz never drops an abandoned job ─────────────


class _Alive:
    def is_alive(self) -> bool:
        return True


class _Interleaved(list):  # type: ignore[type-arg]
    """A list that, when an iteration over it runs to its end, lets another
    thread append before the iteration returns: the window in which a probe
    that rebinds the list to a filtered copy drops the new entry."""

    def __init__(self, *items: Any) -> None:
        super().__init__(items)
        self.window = threading.Event()
        self.appended = threading.Event()

    def __iter__(self) -> Any:
        yield from list.__iter__(self)
        self.window.set()
        self.appended.wait(5)


def test_c3_healthy_race_never_drops_an_abandoned_entry() -> None:
    worker = Worker(JobQueue(), ("cpu",))
    entries = _Interleaved(_Alive())
    worker.abandoned = entries
    probe = threading.Thread(target=worker.healthy, daemon=True)  # /healthz on its own thread
    probe.start()
    entries.window.wait(2)
    late = _Alive()
    worker.abandoned.append(late)  # the loop thread abandons another job meanwhile
    entries.appended.set()
    probe.join(10)
    assert any(x is late for x in list.__iter__(worker.abandoned)), (
        "an abandoned entry appended while /healthz ran was dropped"
    )
    assert worker.healthy() is False


# ── migration reversibility (R13) ──────────────────────────────────────


def test_c3_attempt_lease_migration_is_reversible() -> None:
    url = _url()

    def state() -> dict[str, Any]:
        with psycopg.connect(url) as conn:
            procs = {
                (r[0], r[1]): r[2] for r in conn.execute(
                    "select proname, pg_get_function_identity_arguments(oid), prosrc from pg_proc "
                    "where proname in ('heartbeat_job', 'complete_job')"
                )
            }
            trigger = conn.execute(
                "select count(*) from pg_trigger where tgname = 'runs_status_transition'"
            ).fetchone()[0]
        return {"procs": procs, "trigger": trigger}

    hb3 = ("heartbeat_job", "_job_id uuid, _worker_id text, _lease_seconds integer")
    c4 = ("complete_job", "_job_id uuid, _worker_id text, _result jsonb, _error text")
    after = state()
    assert after["trigger"] == 1
    assert "raise exception" in after["procs"][hb3] and "raise exception" in after["procs"][c4]
    rollback("20261102105000", url)
    try:
        before = state()
        assert before["trigger"] == 0
        assert set(before["procs"]) == {hb3, c4, ("complete_job", "_job_id uuid, _result jsonb, _error text")}
        assert "locked_by = _worker_id" in before["procs"][hb3] and "attempts" not in before["procs"][hb3]
        assert "locked_by = _worker_id" in before["procs"][c4] and "attempts" not in before["procs"][c4]
    finally:
        assert apply_migrations(url) == ["20261102105000"]
    assert state() == after
