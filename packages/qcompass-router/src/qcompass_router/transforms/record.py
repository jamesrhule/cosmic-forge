"""TransformRecord re-export shim (PROMPT 7 v2 §PART A).

The canonical TransformRecord lives in :mod:`qcompass_router.decision`;
PROMPT 7 v2 §PART A names this file as the import path. Both work.

The router's :class:`RoutingDecision.transforms_applied` is a
``list[TransformRecord]`` and qfull-* plugins copy the list into
``ProvenanceRecord.error_mitigation_config`` so audit ``A-router-6``
can verify propagation end-to-end.
"""

from __future__ import annotations

from ..decision import TransformRecord

__all__ = ["TransformRecord"]
