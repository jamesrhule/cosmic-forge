"""NuclearSimulation — qcompass.Simulation protocol."""

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
from .manifest import NuclearProblem
from .quantum_ibm import run_ibm
from .quantum_ionq import run_ionq

if TYPE_CHECKING:  # pragma: no cover
    from qcompass_core import Manifest, ProvenanceRecord


PathTaken = Literal["classical", "ionq", "ibm"]


@dataclass
class NuclearInstance:
    run_id: str
    problem: NuclearProblem
    raw_manifest: dict[str, Any]


@dataclass
class NuclearResult:
    instance: NuclearInstance
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


class NuclearSimulation:
    domain_name: str = "nuclear"

    def __init__(self, *, artifacts_root: Path | str | None = None) -> None:
        self._artifacts_root = (
            Path(artifacts_root)
            if artifacts_root is not None
            else _default_artifacts_root()
        )

    def prepare(self, manifest: "Manifest" | dict[str, Any]) -> NuclearInstance:
        manifest_obj = self._coerce_manifest(manifest)
        if manifest_obj.domain != "nuclear":
            msg = (
                f"NuclearSimulation expects domain='nuclear', "
                f"got {manifest_obj.domain!r}."
            )
            raise ValueError(msg)
        problem = NuclearProblem.model_validate(manifest_obj.problem)
        run_id = f"qcnuc_{secrets.token_hex(6)}"
        return NuclearInstance(
            run_id=run_id,
            problem=problem,
            raw_manifest=manifest_obj.model_dump(),
        )

    def run(self, instance: NuclearInstance, backend: object) -> NuclearResult:
        path = _resolve_path(instance.problem.backend_preference)
        backend_name = getattr(backend, "name", "classical_cpu")

        quantum_energy: float | None
        if path == "classical":
            outcome = compute_reference(instance.problem)
            classical_energy = outcome["energy"]
            classical_hash = outcome["hash"]
            classical_method = outcome["method_used"]
            classical_warning = outcome["warning"]
            quantum_energy = None
            metadata: dict[str, Any] = {"classical": outcome["metadata"]}
        elif path == "ionq":
            ion = run_ionq(instance.problem)
            classical_energy = ion.classical_energy
            classical_hash = ion.classical_hash
            classical_method = ion.classical_method
            classical_warning = ion.classical_warning
            quantum_energy = ion.quantum_energy
            metadata = ion.metadata
        else:
            ibm = run_ibm(instance.problem)
            classical_energy = ibm.classical_energy
            classical_hash = ibm.classical_hash
            classical_method = ibm.classical_method
            classical_warning = ibm.classical_warning
            quantum_energy = ibm.quantum_energy
            metadata = ibm.metadata

        sidecar_path, provenance = self._write_provenance(
            instance,
            classical_hash=classical_hash,
            classical_warning=classical_warning,
            classical_energy=classical_energy,
            quantum_energy=quantum_energy,
            backend_name=backend_name,
            path_taken=path,
            metadata=metadata,
        )
        return NuclearResult(
            instance=instance,
            path_taken=path,
            classical_energy=classical_energy,
            classical_method=classical_method,
            classical_hash=classical_hash,
            classical_warning=classical_warning,
            quantum_energy=quantum_energy,
            provenance=provenance,
            sidecar_path=sidecar_path,
            backend_name=backend_name,
            metadata=metadata,
        )

    def validate(
        self, result: NuclearResult, reference: float | None,
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
            "quantum_energy": result.quantum_energy,
            "classical_method": result.classical_method,
            "classical_hash": result.classical_hash,
            "provenance_warning": result.classical_warning,
            "reference": reference,
            "relative_error": rel,
            "provenance_sidecar": str(result.sidecar_path),
        }

    @classmethod
    def manifest_schema(cls) -> dict[str, Any]:
        return NuclearProblem.model_json_schema()

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
        instance: NuclearInstance,
        *,
        classical_hash: str,
        classical_warning: str | None,
        classical_energy: float,
        quantum_energy: float | None,
        backend_name: str,
        path_taken: PathTaken,
        metadata: dict[str, Any],
    ) -> tuple[Path, "ProvenanceRecord"]:
        qcompass_core = importlib.import_module("qcompass_core")
        # Always tag the model_domain on 0νββ-toy runs.
        em_config: dict[str, Any] | None = None
        if instance.problem.kind == "zero_nu_bb_toy":
            em_config = {"model_domain": "1+1D_toy"}
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
            "domain": NuclearSimulation.domain_name,
            "backend": backend_name,
            "createdAt": datetime.now(UTC).isoformat(),
            "manifest": instance.raw_manifest,
            "pathTaken": path_taken,
            "provenance": provenance.model_dump(mode="json"),
            "provenance_warning": classical_warning,
            "metrics": {
                "classical_energy": classical_energy,
                "quantum_energy": quantum_energy,
            },
            "metadata": metadata,
        }
        sidecar.write_text(json.dumps(envelope, indent=2, default=str))
        return sidecar, provenance


def _resolve_path(preference: str) -> PathTaken:
    if preference in {"classical", "ionq", "ibm"}:
        return preference  # type: ignore[return-value]
    if preference == "auto":
        # Spec says IonQ preferred, IBM fallback. Try the IonQ SDK
        # first, then IBM.
        try:
            importlib.import_module("braket")
            return "ionq"
        except ImportError:
            pass
        try:
            importlib.import_module("qiskit_aer")
            return "ibm"
        except ImportError:
            return "classical"
    msg = f"Unknown backend_preference: {preference!r}"
    raise ValueError(msg)


def _default_artifacts_root() -> Path:
    env = os.environ.get("QCOMPASS_ARTIFACTS")
    if env:
        return Path(env)
    return Path.home() / ".qcompass" / "artifacts"
