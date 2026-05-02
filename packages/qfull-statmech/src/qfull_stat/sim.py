"""StatmechSimulation — qcompass.Simulation protocol."""

from __future__ import annotations

import importlib
import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from .classical import compute_reference
from .manifest import StatmechProblem

if TYPE_CHECKING:  # pragma: no cover
    from qcompass_core import Manifest, ProvenanceRecord


PathTaken = Literal["classical"]


@dataclass
class StatmechInstance:
    run_id: str
    problem: StatmechProblem
    raw_manifest: dict[str, Any]


@dataclass
class StatmechResult:
    instance: StatmechInstance
    path_taken: PathTaken
    classical_energy: float
    classical_method: str
    classical_hash: str
    classical_warning: str | None
    quantum_energy: float | None
    provenance: "ProvenanceRecord"
    sidecar_path: Path
    backend_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


class StatmechSimulation:
    domain_name: str = "statmech"

    def __init__(self, *, artifacts_root: Path | str | None = None) -> None:
        self._artifacts_root = (
            Path(artifacts_root)
            if artifacts_root is not None
            else _default_artifacts_root()
        )

    def prepare(
        self, manifest: "Manifest" | dict[str, Any],
    ) -> StatmechInstance:
        manifest_obj = self._coerce_manifest(manifest)
        if manifest_obj.domain != "statmech":
            msg = (
                f"StatmechSimulation expects domain='statmech', "
                f"got {manifest_obj.domain!r}."
            )
            raise ValueError(msg)
        problem = StatmechProblem.model_validate(manifest_obj.problem)
        run_id = f"qcstat_{secrets.token_hex(6)}"
        return StatmechInstance(
            run_id=run_id, problem=problem,
            raw_manifest=manifest_obj.model_dump(),
        )

    def run(
        self, instance: StatmechInstance, backend: object,
    ) -> StatmechResult:
        backend_name = getattr(backend, "name", "classical_cpu")
        outcome = compute_reference(instance.problem)
        sidecar_path, provenance = self._write_provenance(
            instance,
            outcome=outcome,
            backend_name=backend_name,
            path_taken="classical",
        )
        return StatmechResult(
            instance=instance,
            path_taken="classical",
            classical_energy=outcome["energy"],
            classical_method=outcome["method_used"],
            classical_hash=outcome["hash"],
            classical_warning=outcome["warning"],
            quantum_energy=None,
            provenance=provenance,
            sidecar_path=sidecar_path,
            backend_name=backend_name,
            metadata={"classical": outcome["metadata"]},
        )

    def validate(
        self, result: StatmechResult, reference: float | None,
    ) -> dict[str, Any]:
        primary = (
            result.quantum_energy if result.quantum_energy is not None
            else result.classical_energy
        )
        rel = (
            None if reference is None or reference == 0.0
            else abs(primary - reference) / abs(reference)
        )
        return {
            "domain": self.domain_name,
            "kind": result.instance.problem.kind,
            "path_taken": result.path_taken,
            "classical_energy": result.classical_energy,
            "classical_method": result.classical_method,
            "classical_hash": result.classical_hash,
            "reference": reference,
            "relative_error": rel,
            "provenance_sidecar": str(result.sidecar_path),
        }

    @classmethod
    def manifest_schema(cls) -> dict[str, Any]:
        return StatmechProblem.model_json_schema()

    def _coerce_manifest(
        self, manifest: "Manifest" | dict[str, Any],
    ) -> "Manifest":
        qcompass_core = importlib.import_module("qcompass_core")
        manifest_cls = qcompass_core.Manifest
        if isinstance(manifest, manifest_cls):
            return manifest
        if isinstance(manifest, dict):
            return manifest_cls.model_validate(manifest)
        msg = f"Expected Manifest or dict, got {type(manifest).__name__}."
        raise TypeError(msg)

    def _write_provenance(
        self,
        instance: StatmechInstance,
        *,
        outcome: dict[str, Any],
        backend_name: str,
        path_taken: PathTaken,
    ) -> tuple[Path, "ProvenanceRecord"]:
        qcompass_core = importlib.import_module("qcompass_core")
        em_config = {
            "model_domain": outcome["metadata"].get(
                "model_domain", "stat_mech_generic",
            ),
        }
        provenance = qcompass_core.emit_provenance(
            classical_reference_hash=outcome["hash"],
            calibration_hash=None,
            error_mitigation=em_config,
        )
        self._artifacts_root.mkdir(parents=True, exist_ok=True)
        sidecar = self._artifacts_root / f"{instance.run_id}.provenance.json"
        envelope = {
            "schemaVersion": 1,
            "runId": instance.run_id,
            "domain": StatmechSimulation.domain_name,
            "backend": backend_name,
            "createdAt": datetime.now(UTC).isoformat(),
            "manifest": instance.raw_manifest,
            "pathTaken": path_taken,
            "provenance": provenance.model_dump(mode="json"),
            "provenance_warning": outcome["warning"],
            "metrics": {
                "classical_energy": outcome["energy"],
                "quantum_energy": None,
            },
            "metadata": {"classical": outcome["metadata"]},
        }
        sidecar.write_text(json.dumps(envelope, indent=2, default=str))
        return sidecar, provenance


def _default_artifacts_root() -> Path:
    env = os.environ.get("QCOMPASS_ARTIFACTS")
    if env:
        return Path(env)
    return Path.home() / ".qcompass" / "artifacts"
