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
children run at once, and at most :data:`MAX_COMPILES_PER_TENANT` of them
(running or waiting) for one tenant.

Capacity is separate from the compile (W1 R4-API): a request waits at most
:data:`CUSTOM_COMPILE_WAIT_SECONDS` for a free slot, and its compile limit
starts when it has one. A refusal for capacity is a
:class:`CompileCapacityError` (503 UNAVAILABLE when every slot is busy, 429
RATE_LIMITED when the tenant has its share running), with a Retry-After; it
never says to simplify the expression.

Every other failure is a :class:`ValueError` whose message says what is
wrong; the routes answer it with 422 INVALID_INPUT.
"""

from __future__ import annotations

import math
import multiprocessing
import os
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from multiprocessing.connection import Connection
from typing import Any

from ..domain import EnginePotential, Potential
from ..proc_limits import cap_address_space, confine_child
from . import potentials
from .trajectory import potential_args

# Wall-clock limit of one custom-potential compile (an accepted one takes
# well under a second, most of it the child's imports).
CUSTOM_COMPILE_TIMEOUT_SECONDS = 10.0
# Custom-potential compiles running at once (each child is a Python process
# with sympy loaded).
MAX_CONCURRENT_COMPILES = 4
# How long a request waits for a free slot; its compile limit starts once it
# has one (W1 R4-API: the wait used to come out of the 10 s compile limit).
CUSTOM_COMPILE_WAIT_SECONDS = 5.0
# One tenant's checks, running or waiting for a slot, at once: no tenant can
# hold every slot (W1 R4-API, Decision-by-build: half the slots).
MAX_COMPILES_PER_TENANT = 2
# Retry-After (seconds) of a capacity refusal: an accepted compile takes about
# 1 s, so a slot is usually free well within it.
CAPACITY_RETRY_AFTER_SECONDS = 5
# CPU seconds a child may use beyond its wall-clock limit before RLIMIT_CPU
# stops it (defence in depth, as in the worker).
_CPU_SLACK_SECONDS = 5
# How far a compile child's address space may grow once its imports are
# loaded (RLIMIT_AS, W1 R4-API, Decision-by-build). Measured on this image:
# after imports a child is ~0.54 GiB of address space (0.12 GiB resident),
# and compiling grows it by at most ~0.05 GiB for the largest accepted
# expressions tried (a 29-factor tanh product, a 39-term trig sum). 256 MiB is
# five times that, and keeps four children (~0.4 GiB resident each at most)
# inside the API container's 2 GiB. Beyond it an allocation is a
# MemoryError, refused like any compile error. Measured after the imports so
# an image with JAX installed (a larger import) is not refused for it.
COMPILE_ADDRESS_SPACE_HEADROOM_BYTES = 256 << 20
# The child's niceness: it yields the API's one CPU to the API process.
COMPILE_NICENESS = 10
_MAX_MESSAGE_CHARS = 2000
_SPAWN = multiprocessing.get_context("spawn")
_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_COMPILES)
_TENANT_LOCK = threading.Lock()
_TENANT_ACTIVE: dict[str, int] = {}
# The tenant a check is for, when its caller cannot pass it (a plugin's
# ``validate_problem(problem)``); routes set it with :func:`compile_tenant`.
_TENANT: ContextVar[str | None] = ContextVar("potential_check_tenant", default=None)
_NO_TENANT = "-"  # in-process callers without a tenant share one share


class CompileCapacityError(ValueError):
    """A custom potential could not be checked for lack of capacity, not because of it.

    ``code`` is ``UNAVAILABLE`` (every compile slot stayed busy, 503) or
    ``RATE_LIMITED`` (the tenant already has its share running, 429);
    ``retry_after`` is the Retry-After in seconds. It is a ``ValueError`` so a
    caller that does not know it still refuses the request (422) rather than
    failing (500); the routes answer it with its own status.
    """

    def __init__(self, code: str, message: str, retry_after: int = CAPACITY_RETRY_AFTER_SECONDS) -> None:
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


@contextmanager
def compile_tenant(tenant: str | None) -> Iterator[None]:
    """Check potentials in this context (and threads started from it) for ``tenant``."""
    token = _TENANT.set(tenant)
    try:
        yield
    finally:
        _TENANT.reset(token)


@contextmanager
def _tenant_share(tenant: str) -> Iterator[None]:
    with _TENANT_LOCK:
        if _TENANT_ACTIVE.get(tenant, 0) >= MAX_COMPILES_PER_TENANT:
            raise CompileCapacityError(
                "RATE_LIMITED",
                f"custom potential: this tenant already has {MAX_COMPILES_PER_TENANT} custom "
                f"potentials being checked; retry in {CAPACITY_RETRY_AFTER_SECONDS} s",
            )
        _TENANT_ACTIVE[tenant] = _TENANT_ACTIVE.get(tenant, 0) + 1
    try:
        yield
    finally:
        with _TENANT_LOCK:
            left = _TENANT_ACTIVE[tenant] - 1
            if left:
                _TENANT_ACTIVE[tenant] = left
            else:
                del _TENANT_ACTIVE[tenant]


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
    confine_child(parent_pid, cpu_seconds, niceness=COMPILE_NICENESS)
    try:  # compile_potential's preferred backend, loaded before the memory cap
        import jax  # noqa: F401
    except ImportError:
        pass
    cap_address_space(COMPILE_ADDRESS_SPACE_HEADROOM_BYTES)
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


def _compile_in_child(pot: EnginePotential, limit: float) -> None:
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
        if reader.poll(limit):
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


def check_potential(
    pot: Potential, *, timeout: float | None = None, wait: float | None = None,
    tenant: str | None = None,
) -> None:
    """Refuse (ValueError) a potential the worker could not run.

    It must compile in M2's units with every parameter bound
    (``compile_potential`` + ``potential_args``) and have a starting field
    value (``initial_field``: a custom potential needs ``params['phi0']``).
    A custom potential's compile has ``timeout`` seconds (default
    :data:`CUSTOM_COMPILE_TIMEOUT_SECONDS`) from when it has a slot; it waits
    at most ``wait`` seconds (default :data:`CUSTOM_COMPILE_WAIT_SECONDS`) for
    one, as one of ``tenant``'s (default: :func:`compile_tenant`'s) checks.
    Capacity refusals are :class:`CompileCapacityError`.
    """
    engine = pot.engine()
    limit = CUSTOM_COMPILE_TIMEOUT_SECONDS if timeout is None else timeout
    slot_wait = CUSTOM_COMPILE_WAIT_SECONDS if wait is None else wait
    owner = tenant if tenant is not None else (_TENANT.get() or _NO_TENANT)
    try:
        if engine.kind == "custom":
            with _tenant_share(owner):
                if not _SLOTS.acquire(timeout=slot_wait):
                    raise CompileCapacityError(
                        "UNAVAILABLE",
                        f"custom potential: the server is compiling other custom potentials (all "
                        f"{MAX_CONCURRENT_COMPILES} slots stayed busy for {slot_wait:g} s), so it "
                        f"was not checked; retry in {CAPACITY_RETRY_AFTER_SECONDS} s",
                    )
                try:
                    _compile_in_child(engine, limit)
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


__all__ = [
    "CAPACITY_RETRY_AFTER_SECONDS", "CUSTOM_COMPILE_TIMEOUT_SECONDS", "CUSTOM_COMPILE_WAIT_SECONDS",
    "MAX_COMPILES_PER_TENANT", "MAX_CONCURRENT_COMPILES", "CompileCapacityError", "check_potential",
    "compile_tenant",
]
