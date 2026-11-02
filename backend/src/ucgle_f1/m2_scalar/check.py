"""Submit-time check of a run's potential, bounded in time and CPU (W1 API3).

A run's potential must compile in M2's units with every parameter bound and
have a starting field value, or the worker would only refuse it later. The
API checks this at submit: the qcompass run route
(``LeptogenesisSimulation.validate_problem``) and the agent's
``validate_config`` (so ``start_run``, ``POST /api/runs`` and
``scan_parameters`` too).

A built-in kind compiles a fixed expression and is checked in-process. A
custom potential is tenant-controlled sympy work, so it is compiled in a
short-lived "spawn" child process with a wall-clock limit, confined like the
worker's job processes (``proc_limits``: ``RLIMIT_CPU``, and death with the
API process on Linux). A child that has not answered by the limit is killed
and the check fails, so no request holds an API thread or a core for long.
The caps in :mod:`.potentials` make every accepted expression cheap; this
limit holds even if they miss one. At most :data:`MAX_CONCURRENT_COMPILES`
children run at once.

Every failure is a :class:`ValueError` whose message says what is wrong; the
routes answer it with 422 INVALID_INPUT.
"""

from __future__ import annotations

import math
import multiprocessing
import os
import threading
import time
from collections.abc import Callable
from multiprocessing.connection import Connection
from typing import Any

from ..domain import EnginePotential, Potential
from ..proc_limits import confine_child
from . import potentials
from .trajectory import potential_args

# Wall-clock limit of one custom-potential compile (an accepted one takes
# well under a second, most of it the child's imports).
CUSTOM_COMPILE_TIMEOUT_SECONDS = 10.0
# Custom-potential compiles running at once (each child is a Python process
# with sympy loaded); a request waits for a slot within its own limit.
MAX_CONCURRENT_COMPILES = 4
# CPU seconds a child may use beyond its wall-clock limit before RLIMIT_CPU
# stops it (defence in depth, as in the worker).
_CPU_SLACK_SECONDS = 5
_MAX_MESSAGE_CHARS = 2000
_SPAWN = multiprocessing.get_context("spawn")
_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_COMPILES)


def _refusal(kind: str, exc: BaseException) -> str:
    if isinstance(exc, ValueError):
        return str(exc)[:_MAX_MESSAGE_CHARS]
    # SyntaxError from lambdify, KeyError, TypeError, RecursionError…: the
    # potential is refused (422), not a server error.
    return f"{kind} potential: it does not compile ({type(exc).__name__}: {exc})"[:_MAX_MESSAGE_CHARS]


def _compile_and_bind(compile_fn: Callable[[Potential], Any], pot: EnginePotential) -> None:
    potential_args(compile_fn(pot), dict(pot.params))


def _child_main(
    conn: Connection, compile_fn: Callable[[Potential], Any], kind: str,
    params: dict[str, float], source: str | None, parent_pid: int, cpu_seconds: int,
) -> None:
    """Entry point of the compile child: compile, bind, report one outcome."""
    confine_child(parent_pid, cpu_seconds)
    outcome: tuple[str, str | None]
    try:
        pot = EnginePotential.model_construct(kind=kind, params=params, customPython=source)
        _compile_and_bind(compile_fn, pot)
        outcome = ("ok", None)
    except BaseException as exc:  # noqa: BLE001 - reported to the API as the refusal
        outcome = ("refused", _refusal(kind, exc))
    try:
        conn.send(outcome)
    except (OSError, ValueError):  # the API stopped listening (timed out)
        pass
    finally:
        conn.close()


def _stop(proc: Any) -> None:
    proc.join(1.0)
    if proc.is_alive():
        proc.terminate()
        proc.join(2.0)
    if proc.is_alive():
        proc.kill()
        proc.join()
    proc.close()


def _compile_in_child(pot: EnginePotential, remaining: float, limit: float) -> None:
    reader, writer = _SPAWN.Pipe(duplex=False)
    cpu_seconds = math.ceil(limit) + _CPU_SLACK_SECONDS
    proc = _SPAWN.Process(
        target=_child_main,
        # The compile function is passed by reference, so the child runs the
        # one this module sees (``potentials.compile_potential``).
        args=(writer, potentials.compile_potential, pot.kind, dict(pot.params),
              pot.customPython, os.getpid(), cpu_seconds),
        name="potential-check", daemon=True,
    )
    outcome: tuple[str, str | None] | None = None
    try:
        proc.start()
    except BaseException:
        reader.close()
        writer.close()
        raise
    writer.close()  # the child holds its own end: EOF if it dies without reporting
    try:
        if reader.poll(max(remaining, 0.0)):
            try:
                outcome = reader.recv()
            except (EOFError, OSError):
                outcome = ("died", None)
    finally:
        reader.close()
        _stop(proc)
    if outcome is None:
        raise ValueError(
            f"custom potential: compiling it did not finish within {limit:g} s, so it was "
            "stopped; simplify the expression",
        )
    status, message = outcome
    if status == "refused":
        raise ValueError(message)
    if status != "ok":
        raise ValueError("custom potential: the compile process stopped before it reported")


def check_potential(pot: Potential, *, timeout: float | None = None) -> None:
    """Refuse (ValueError) a potential the worker could not run.

    It must compile in M2's units with every parameter bound
    (``compile_potential`` + ``potential_args``) and have a starting field
    value (``initial_field``: a custom potential needs ``params['phi0']``).
    """
    engine = pot.engine()
    limit = CUSTOM_COMPILE_TIMEOUT_SECONDS if timeout is None else timeout
    try:
        if engine.kind == "custom":
            deadline = time.monotonic() + limit
            if not _SLOTS.acquire(timeout=limit):
                raise ValueError(
                    f"custom potential: it could not be checked within {limit:g} s because the "
                    "server is compiling other custom potentials; try again",
                )
            try:
                _compile_in_child(engine, deadline - time.monotonic(), limit)
            finally:
                _SLOTS.release()
        else:
            _compile_and_bind(potentials.compile_potential, engine)
        from ..m7_infer.couplings import initial_field  # the pipeline's own rule

        initial_field(engine)
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - any refusal of the potential is a 422
        raise ValueError(_refusal(engine.kind, exc)) from exc


__all__ = ["CUSTOM_COMPILE_TIMEOUT_SECONDS", "MAX_CONCURRENT_COMPILES", "check_potential"]
