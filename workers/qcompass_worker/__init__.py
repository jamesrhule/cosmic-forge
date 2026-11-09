"""QCompass worker service (P3-02): ``python -m qcompass_worker --classes cpu,gpu_small``.

The loop itself is :mod:`ucgle_f1.worker`; this package is the deployable
entrypoint (``workers/`` per Part 4's repository layout).
"""

from ucgle_f1.worker import HANDLERS, Worker, main

__all__ = ["HANDLERS", "Worker", "main"]
