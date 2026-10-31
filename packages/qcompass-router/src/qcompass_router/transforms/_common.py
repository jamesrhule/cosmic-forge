"""Shared helpers for the transform modules (one implementation).

Every transform under :mod:`qcompass_router.transforms` goes through
:func:`run_addon_transform`, which soft-imports the qiskit addon,
measures depth before/after plus wall-clock, and returns the unified
:class:`~qcompass_router.decision.TransformRecord`. The router's
auto-transform trigger uses :func:`circuit_depth` too, so depth is
measured one way everywhere.
"""

from __future__ import annotations

import contextlib
import importlib
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from ..decision import TransformName, TransformRecord

_QASM_HEADER_PREFIXES = (
    "//",
    "OPENQASM",
    "include",
    "qreg ",
    "creg ",
    "qubit",
    "bit ",
)


def try_import(name: str) -> Any | None:
    """Best-effort import; returns the module or None."""
    try:
        return importlib.import_module(name)
    except Exception:  # noqa: BLE001
        return None


def qasm_depth(qasm: str) -> int:
    """Cheap upper-bound depth proxy for QASM text: gate-bearing lines."""
    depth = 0
    for raw in qasm.splitlines():
        line = raw.strip()
        if not line or line.startswith(_QASM_HEADER_PREFIXES):
            continue
        if line.endswith(";"):
            depth += 1
    return depth


def circuit_depth(circuit: Any) -> int:
    """Best-effort depth measurement.

    QASM strings use :func:`qasm_depth`; circuit objects use their
    ``depth()`` method; sequence-like inputs fall back to ``len``;
    anything else is 0.
    """
    if circuit is None:
        return 0
    if isinstance(circuit, str):
        return qasm_depth(circuit)
    # A circuit whose depth() raises falls through to len(); best effort.
    with contextlib.suppress(Exception):
        depth_fn = getattr(circuit, "depth", None)
        if callable(depth_fn):
            return int(depth_fn())
    try:
        return len(circuit)
    except Exception:  # noqa: BLE001
        return 0


@contextmanager
def measure_ms() -> Iterator[list[float]]:
    """Context manager capturing elapsed milliseconds in ``result[0]``."""
    box: list[float] = [0.0]
    start = time.perf_counter()
    try:
        yield box
    finally:
        box[0] = (time.perf_counter() - start) * 1000.0


def run_addon_transform(
    name: TransformName,
    circuit: Any,
    parameters: dict[str, Any],
    *,
    module: str,
    call: Callable[[Any, Any], Any | None],
    fidelity_loss_if_applied: float = 0.0,
) -> tuple[Any, TransformRecord]:
    """Run one addon-backed transform and record it.

    ``call(addon, circuit)`` returns the transformed circuit, or None
    when the addon exposes no usable entry point. Missing SDKs and
    addon errors are graceful pass-throughs; the record's ``notes``
    say which path ran.
    """
    addon = try_import(module)
    depth_before = circuit_depth(circuit)
    out = circuit
    fidelity_loss = 0.0
    with measure_ms() as ms:
        if addon is None:
            notes = "SDK absent — pass-through."
        else:
            try:
                result = call(addon, circuit)
            except Exception as exc:  # noqa: BLE001 — graceful no-op
                notes = (
                    f"{module} importable; call failed "
                    f"({type(exc).__name__}) — pass-through."
                )
            else:
                if result is None:
                    notes = f"{module} importable; no usable entry point — pass-through."
                else:
                    out = result
                    fidelity_loss = fidelity_loss_if_applied
                    notes = f"applied via {module}."
    return out, TransformRecord(
        name=name,
        parameters=parameters,
        fidelity_loss=fidelity_loss,
        notes=notes,
        depth_before=depth_before,
        depth_after=circuit_depth(out),
        runtime_ms=ms[0],
    )


def call_first(
    *names: str, kwargs: dict[str, Any] | None = None,
) -> Callable[[Any, Any], Any | None]:
    """``call`` for addons whose transform is one function taking the circuit.

    ``kwargs`` are forwarded to the addon function unchanged (6B passthrough).
    """
    extra = dict(kwargs or {})

    def _call(addon: Any, circuit: Any) -> Any | None:
        for attr in names:
            fn = getattr(addon, attr, None)
            if callable(fn):
                return fn(circuit, **extra)
        return None

    return _call
