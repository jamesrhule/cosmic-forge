"""Circuit transform stack (depth reduction + error mitigation).

Each transform wraps one ``qiskit-addon`` (lazy-imported) and
returns a :class:`TransformRecord` the router copies into the
``RoutingDecision.transforms_applied`` list. Plugins can then
forward the records into their ``ProvenanceRecord.error_mitigation_config``
so audit ``A-router-6`` can verify propagation end-to-end.
"""

from __future__ import annotations

from typing import Any

from ..decision import TransformRecord
from .aqc_tensor import apply_aqc_tensor
from .cutting import apply_cutting
from .mpf import apply_mpf
from .obp import apply_obp


_REGISTRY = {
    "aqc_tensor": apply_aqc_tensor,
    "mpf": apply_mpf,
    "obp": apply_obp,
    "cutting": apply_cutting,
}


def apply_transforms(
    circuit: Any,
    names: list[str],
    *,
    parameters: dict[str, dict[str, Any]] | None = None,
) -> tuple[Any, list[TransformRecord]]:
    """Apply ``names`` (in order) to ``circuit``; return the result + records.

    ``parameters[name]`` may be supplied per transform; missing entries
    default to ``{}``. Each transform records itself; the records are
    flattened in execution order and surface in
    :attr:`RoutingDecision.transforms_applied`.
    """
    records: list[TransformRecord] = []
    params = parameters or {}
    out = circuit
    for name in names:
        fn = _REGISTRY.get(name)
        if fn is None:
            msg = f"Unknown transform: {name!r}"
            raise ValueError(msg)
        out, record = fn(out, **params.get(name, {}))
        records.append(record)
    return out, records


def auto_select_transforms(
    circuit: Any,
    *,
    device_max_depth: int,
    measured_depth: int | None = None,
) -> list[str]:
    """PROMPT 7 v2 §PART A: pick transforms when circuit depth > device max.

    Heuristic (intentionally simple — leaderboard-grade, not a full
    pass-manager): when the circuit's depth exceeds the chosen
    backend's supported max, return an ordered list of transforms
    that progressively trade off fidelity for shallower circuits:

      depth >= 1.5×max → ["aqc_tensor"]                 (compress)
      depth >= 2.0×max → ["aqc_tensor", "obp"]          (+ operator-bp)
      depth >= 3.0×max → ["aqc_tensor", "obp", "cutting"]  (+ wire-cut)
      depth >= 4.0×max → ["aqc_tensor", "obp", "cutting", "mpf"]

    ``measured_depth`` defaults to ``getattr(circuit, "depth",
    lambda: 0)()`` when ``circuit`` is a Qiskit-style circuit.
    Passing ``None`` falls back to the attribute probe; passing a
    concrete int skips the probe (useful for tests).
    """
    depth = measured_depth
    if depth is None:
        depth_attr = getattr(circuit, "depth", None)
        depth = depth_attr() if callable(depth_attr) else 0
    if device_max_depth <= 0 or depth <= device_max_depth:
        return []
    ratio = depth / device_max_depth
    if ratio >= 4.0:
        return ["aqc_tensor", "obp", "cutting", "mpf"]
    if ratio >= 3.0:
        return ["aqc_tensor", "obp", "cutting"]
    if ratio >= 2.0:
        return ["aqc_tensor", "obp"]
    return ["aqc_tensor"]


__all__ = [
    "apply_aqc_tensor",
    "apply_cutting",
    "apply_mpf",
    "apply_obp",
    "apply_transforms",
    "auto_select_transforms",
]
