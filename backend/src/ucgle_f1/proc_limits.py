"""Confinement for short-lived child processes (one implementation, R20).

The worker runs each job in a "spawn" child (``worker.py``), and the API
compiles a tenant's custom potential in one at submit
(``m2_scalar/check.py``). Both children call :func:`confine_child` first:
on Linux the child dies with its parent (``PR_SET_PDEATHSIG``), and on
POSIX its CPU time is capped (``RLIMIT_CPU``), so it stops even if the
parent's wall-clock kill never comes.
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


def confine_child(parent_pid: int, cpu_seconds: int) -> None:
    """Die with the parent (Linux), and cap this process's CPU time (RLIMIT_CPU)."""
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


__all__ = ["confine_child", "cpu_count"]
