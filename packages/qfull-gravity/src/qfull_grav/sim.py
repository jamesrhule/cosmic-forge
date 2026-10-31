"""GravitySimulation — qcompass.Simulation protocol (PROMPT 9 v2 §A)."""

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
from .manifest import GravityProblem, model_domain_for_kind

if TYPE_CHECKING:  # pragma: no cover
    from qcompass_core import Manifest, ProvenanceRecord


PathTaken = Literal["classical"]


@dataclass
class GravityInstance:
    run_id: str
    problem: GravityProblem
    raw_manifest: dict[str, Any]


@dataclass
class GravityResult:
    instance: GravityInstance
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
    # PROMPT 9 v2 §A — provenance contract.
    is_learned_hamiltonian: bool = False
    provenance_warning: str | None = None
    model_domain: str = "toy_SYK_1+1D"


class GravitySimulation:
    domain_name: str = "gravity"

    def __init__(self, *, artifacts_root: Path | str | None = None) -> None:
        self._artifacts_root = (
            Path(artifacts_root)
            if artifacts_root is not None
            else _default_artifacts_root()
        )

    def prepare(
        self, manifest: "Manifest" | dict[str, Any],
    ) -> GravityInstance:
        manifest_obj = self._coerce_manifest(manifest)
        if manifest_obj.domain != "gravity":
            msg = (
                f"GravitySimulation expects domain='gravity', "
                f"got {manifest_obj.domain!r}."
            )
            raise ValueError(msg)
        problem = GravityProblem.model_validate(manifest_obj.problem)
        run_id = f"qcgrav_{secrets.token_hex(6)}"
        return GravityInstance(
            run_id=run_id,
            problem=problem,
            raw_manifest=manifest_obj.model_dump(),
        )

    def run(
        self, instance: GravityInstance, backend: object,
    ) -> GravityResult:
        backend_name = getattr(backend, "name", "classical_cpu")
        outcome = compute_reference(instance.problem)
        classical_energy = outcome["energy"]
        classical_hash = outcome["hash"]
        classical_method = outcome["method_used"]
        classical_warning = outcome["warning"]
        metadata: dict[str, Any] = {"classical": outcome["metadata"]}
        model_domain = model_domain_for_kind(instance.problem.kind)
        sidecar_path, provenance = self._write_provenance(
            instance,
            classical_hash=classical_hash,
            classical_warning=classical_warning,
            classical_energy=classical_energy,
            quantum_energy=None,
            backend_name=backend_name,
            path_taken="classical",
            metadata=metadata,
            model_domain=model_domain,
        )
        return GravityResult(
            instance=instance,
            path_taken="classical",
            classical_energy=classical_energy,
            classical_method=classical_method,
            classical_hash=classical_hash,
            classical_warning=classical_warning,
            quantum_energy=None,
            provenance=provenance,
            sidecar_path=sidecar_path,
            backend_name=backend_name,
            metadata=metadata,
            is_learned_hamiltonian=instance.problem.is_learned_hamiltonian,
            provenance_warning=instance.problem.provenance_warning,
            model_domain=model_domain,
        )

    def validate(
        self, result: GravityResult, reference: float | None,
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
            "provenance_warning": result.provenance_warning,
            "is_learned_hamiltonian": result.is_learned_hamiltonian,
            "model_domain": result.model_domain,
            "reference": reference,
            "relative_error": rel,
            "provenance_sidecar": str(result.sidecar_path),
        }

    @classmethod
    def manifest_schema(cls) -> dict[str, Any]:
        return GravityProblem.model_json_schema()

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
        instance: GravityInstance,
        *,
        classical_hash: str,
        classical_warning: str | None,
        classical_energy: float,
        quantum_energy: float | None,
        backend_name: str,
        path_taken: PathTaken,
        metadata: dict[str, Any],
        model_domain: str,
    ) -> tuple[Path, "ProvenanceRecord"]:
        qcompass_core = importlib.import_module("qcompass_core")
        # Always tag the model_domain. When the manifest carries a
        # provenance_warning, embed it in error_mitigation_config
        # so audit S-grav-1 can verify propagation.
        em_config: dict[str, Any] = {"model_domain": model_domain}
        if instance.problem.provenance_warning:
            em_config["provenance_warning"] = instance.problem.provenance_warning
        if instance.problem.is_learned_hamiltonian:
            em_config["is_learned_hamiltonian"] = True
        provenance = qcompass_core.emit_provenance(
            classical_reference_hash=classical_hash,
            calibration_hash=None,
            error_mitigation=em_config,
        )
        self._artifacts_root.mkdir(parents=True, exist_ok=True)
        sidecar = self._artifacts_root / f"{instance.run_id}.provenance.json"
        envelope = {
            "schemaVersion": 1,
            "runId": instance.run_id,
            "domain": GravitySimulation.domain_name,
            "backend": backend_name,
            "createdAt": datetime.now(UTC).isoformat(),
            "manifest": instance.raw_manifest,
            "pathTaken": path_taken,
            "provenance": provenance.model_dump(mode="json"),
            "provenance_warning": (
                instance.problem.provenance_warning or classical_warning
            ),
            "is_learned_hamiltonian": instance.problem.is_learned_hamiltonian,
            "model_domain": model_domain,
            "metrics": {
                "classical_energy": classical_energy,
                "quantum_energy": quantum_energy,
            },
            "metadata": metadata,
        }
        sidecar.write_text(json.dumps(envelope, indent=2, default=str))
        return sidecar, provenance


def _default_artifacts_root() -> Path:
    env = os.environ.get("QCOMPASS_ARTIFACTS")
    if env:
        return Path(env)
    return Path.home() / ".qcompass" / "artifacts"
