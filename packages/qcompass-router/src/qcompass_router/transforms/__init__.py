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


__all__ = [
    "apply_aqc_tensor",
    "apply_cutting",
    "apply_mpf",
    "apply_obp",
    "apply_transforms",
]
