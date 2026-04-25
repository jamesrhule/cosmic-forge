"""Built-in `null` domain plugin.

The simplest possible :class:`Simulation` implementation; used for
integration tests and as a reference template for new qfull-* plugins.

It performs no physics and emits a trivially-correct provenance
record so the bench harness has something to record without any
optional dependencies installed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from ..manifest import Manifest, ProvenanceRecord
from ..protocols import emit_provenance


@dataclass
class NullInstance:
    """Materialised problem the null plugin operates on."""

    label: str
    payload: dict[str, Any]


@dataclass
class NullResult:
    """Output of :meth:`NullSim.run`."""

    instance: NullInstance
    backend_name: str
    provenance: ProvenanceRecord


class NullSim:
    """Domain plugin that succeeds for any well-formed manifest."""

    def prepare(self, manifest: Manifest) -> NullInstance:
        if manifest.domain != "null":
            msg = f"NullSim accepts domain='null', got '{manifest.domain}'."
            raise ValueError(msg)
        return NullInstance(
            label=str(manifest.problem.get("label", "noop")),
            payload=dict(manifest.problem),
        )

    def run(self, instance: NullInstance, backend: Any) -> NullResult:
        # Hash the canonical JSON of the problem so two callers with
        # identical inputs see identical provenance.
        payload_bytes = json.dumps(
            instance.payload, sort_keys=True, separators=(",", ":")
        ).encode()
        ref_hash = hashlib.sha256(payload_bytes).hexdigest()
        prov = emit_provenance(classical_reference_hash=ref_hash)
        backend_name = getattr(backend, "name", "classical_cpu")
        return NullResult(instance=instance, backend_name=backend_name, provenance=prov)

    def validate(self, result: NullResult, reference: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "label": result.instance.label,
            "backend": result.backend_name,
            "matches_reference": reference is None or reference == result.provenance,
        }

    @classmethod
    def manifest_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
            },
            "required": [],
            "additionalProperties": True,
        }
