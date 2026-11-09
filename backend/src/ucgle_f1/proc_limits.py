"""Confinement for short-lived child processes (one implementation, R20).

The worker runs each job in a "spawn" child (``worker.py``), and the API
compiles a tenant's custom potential in one at submit
(``m2_scalar/check.py``). Both children call :func:`confine_child` first:
on Linux the child dies with its parent (``PR_SET_PDEATHSIG``), and on
POSIX its CPU time is capped (``RLIMIT_CPU``), so it stops even if the
parent's wall-clock kill never comes. A child may also lower its priority
(``nice``) and cap how far its address space grows (:func:`cap_address_space`,
``RLIMIT_AS``); the API's compile child does both (W1 R4-API), the worker's
job children do neither.
"""

from __future__ import annotations

import logging
import os
import sys

log = logging.getLogger(__name__)


def cpu_count() -> int:
    """CPUs this process may run on (its affinity mask, else the machine's)."""
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        return max(1, os.cpu_count() or 1)


def confine_child(parent_pid: int, cpu_seconds: int, *, niceness: int = 0) -> None:
    """Die with the parent (Linux), and cap this process's CPU time (RLIMIT_CPU).

    ``niceness`` also lowers its scheduling priority by that much
    (``os.nice``), so it yields the CPU to its parent.
    """
    if sys.platform.startswith("linux"):
        try:
            import ctypes
            import signal

            libc = ctypes.CDLL(None, use_errno=True)
            libc.prctl(1, int(signal.SIGKILL))  # PR_SET_PDEATHSIG
        except (OSError, AttributeError):  # pragma: no cover - libc without prctl
            pass
    if os.getppid() != parent_pid:
        os._exit(1)  # the parent is already gone
    if niceness:
        try:
            os.nice(niceness)
        except (AttributeError, OSError):  # pragma: no cover - not POSIX
            log.warning("could not lower a child process's priority", exc_info=True)
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
        log.warning("could not set RLIMIT_CPU for a child process", exc_info=True)


def address_space_bytes() -> int | None:
    """This process's current virtual memory size (Linux ``VmSize``), or None."""
    try:
        with open("/proc/self/status", encoding="ascii") as status:
            for line in status:
                if line.startswith("VmSize:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def cap_address_space(headroom_bytes: int) -> int | None:
    """Cap this process's address space (RLIMIT_AS) at its current size plus ``headroom_bytes``.

    Called once a child has imported what it needs, so the cap measures
    only what its work allocates; beyond it an allocation is a
    ``MemoryError``. Returns the limit set, or None where it cannot be
    measured or set (not Linux, or a stricter limit already in place).
    """
    current = address_space_bytes()
    if current is None:
        return None
    try:
        import resource

        _, hard = resource.getrlimit(resource.RLIMIT_AS)
        limit = current + headroom_bytes
        if hard != resource.RLIM_INFINITY:
            limit = min(limit, hard)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ImportError, ValueError, OSError):  # pragma: no cover - not POSIX, or stricter
        log.warning("could not set RLIMIT_AS for a child process", exc_info=True)
        return None
    return limit


__all__ = ["address_space_bytes", "cap_address_space", "confine_child", "cpu_count"]
