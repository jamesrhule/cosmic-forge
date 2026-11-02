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
