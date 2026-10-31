"""Shared helpers for transform modules."""

from __future__ import annotations

import importlib
import time
from contextlib import contextmanager
from typing import Any, Iterator


def try_import(name: str):
    """Best-effort import; returns the module or None."""
    try:
        return importlib.import_module(name)
    except Exception:  # noqa: BLE001
        return None


def circuit_depth(circuit: Any) -> int:
    """Best-effort depth measurement.

    Falls back to `len(...)` for sequence-like inputs and finally to 0.
    Used purely for `TransformRecord.depth_before/after`.
    """
    if circuit is None:
        return 0
    try:
        depth_fn = getattr(circuit, "depth", None)
        if callable(depth_fn):
            return int(depth_fn())
    except Exception:  # noqa: BLE001
        pass
    try:
        return len(circuit)
    except Exception:  # noqa: BLE001
        return 0


@contextmanager
def measure_ms() -> Iterator[list[float]]:
    """Context manager capturing elapsed milliseconds in `result[0]`."""
    box: list[float] = [0.0]
    start = time.perf_counter()
    try:
        yield box
    finally:
        box[0] = (time.perf_counter() - start) * 1000.0
