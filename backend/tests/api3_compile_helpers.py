"""Stand-ins for ``compile_potential`` in the W1 API3 tests (test_api3_submit_checks.py).

They are module-level functions so the API's compile child process (spawned,
so it imports them by name) runs them in place of the real compile; on the
base tree, where the compile ran in the API process, they run there.
"""

from __future__ import annotations

import os
import time
from typing import Any

SPIN_SECONDS = 120.0


def spin_compile(_pot: Any) -> Any:
    """A compile that holds a core (and the GIL) for two minutes."""
    end = time.monotonic() + SPIN_SECONDS
    n = 0
    while time.monotonic() < end:
        n += 1
    raise RuntimeError(f"spun {n} times")


def report_limits(_pot: Any) -> Any:
    """Refuse with the process's CPU limit and parent, so a test can read them."""
    import resource

    soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
    raise ValueError(f"custom potential: limits cpu=({soft}, {hard}) pid={os.getpid()} ppid={os.getppid()}")


# W1 R4-API (test_r4_api_capacity_and_scan.py) ---------------------------

HOLD_SECONDS = 4.0


def slow_real_compile(pot: Any) -> Any:
    """The real compile, after holding its slot for HOLD_SECONDS (a busy server)."""
    from ucgle_f1.m2_scalar import potentials

    time.sleep(HOLD_SECONDS)
    return potentials.compile_potential(pot)


def report_memory_and_priority(_pot: Any) -> Any:
    """Refuse with the child's address-space limit, its size and its niceness."""
    import resource

    from ucgle_f1.proc_limits import address_space_bytes

    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    raise ValueError(
        f"custom potential: limits as=({soft}, {hard}) vmsize={address_space_bytes()} "
        f"nice={os.nice(0)}",
    )


def allocate_compile(_pot: Any) -> Any:
    """A compile that allocates 2 GiB (a memory bomb that passed the caps)."""
    block = bytearray(2 << 30)
    return len(block)
