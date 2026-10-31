"""HEPSimulation — qcompass.Simulation protocol."""

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
from .manifest import HEPProblem
from .particle_obs import ParticleObservable, build_particle_obs
from .quantum_ibm import run_ibm
from .quantum_ionq import run_ionq

if TYPE_CHECKING:  # pragma: no cover
    from qcompass_core import Manifest, ProvenanceRecord


PathTaken = Literal["classical", "ibm", "ionq", "scadapt_vqe"]


@dataclass
class HEPInstance:
    run_id: str
    problem: HEPProblem
    raw_manifest: dict[str, Any]


@dataclass
class HEPResult:
    instance: HEPInstance
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
    particle_obs: dict[str, ParticleObservable] = field(default_factory=dict)


class HEPSimulation:
    domain_name: str = "hep"

    def __init__(self, *, artifacts_root: Path | str | None = None) -> None:
        self._artifacts_root = (
            Path(artifacts_root)
            if artifacts_root is not None
            else _default_artifacts_root()
        )

    def prepare(self, manifest: "Manifest" | dict[str, Any]) -> HEPInstance:
        manifest_obj = self._coerce_manifest(manifest)
        if manifest_obj.domain != "hep":
            msg = f"HEPSimulation expects domain='hep', got {manifest_obj.domain!r}."
            raise ValueError(msg)
        problem = HEPProblem.model_validate(manifest_obj.problem)
        run_id = f"qchep_{secrets.token_hex(6)}"
        return HEPInstance(
            run_id=run_id,
            problem=problem,
            raw_manifest=manifest_obj.model_dump(),
        )

    def run(self, instance: HEPInstance, backend: object) -> HEPResult:
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
        elif path == "ibm":
            ibm = run_ibm(instance.problem)
            classical_energy = ibm.classical_energy
            classical_hash = ibm.classical_hash
            classical_method = ibm.classical_method
            classical_warning = ibm.classical_warning
            quantum_energy = ibm.quantum_energy
            metadata = ibm.metadata
        elif path == "ionq":
            ion = run_ionq(instance.problem)
            classical_energy = ion.classical_energy
            classical_hash = ion.classical_hash
            classical_method = ion.classical_method
            classical_warning = ion.classical_warning
            quantum_energy = ion.quantum_energy
            metadata = ion.metadata
        else:
            msg = (
                "scadapt_vqe path requires the vendored module; "
                "see scadapt_vqe/__init__.py."
            )
            raise NotImplementedError(msg)

        classical_metadata = (
            metadata.get("classical")
            if isinstance(metadata.get("classical"), dict)
            else {}
        )
        particle_obs = build_particle_obs(instance.problem, classical_metadata)
        sidecar_path, provenance = self._write_provenance(
            instance,
            classical_hash=classical_hash,
            classical_warning=classical_warning,
            classical_energy=classical_energy,
            quantum_energy=quantum_energy,
            backend_name=backend_name,
            path_taken=path,
            metadata=metadata,
            particle_obs=particle_obs,
        )
        return HEPResult(
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
            particle_obs=particle_obs,
        )

    def validate(
        self, result: HEPResult, reference: float | None,
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
        return HEPProblem.model_json_schema()

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
        instance: HEPInstance,
        *,
        classical_hash: str,
        classical_warning: str | None,
        classical_energy: float,
        quantum_energy: float | None,
        backend_name: str,
        path_taken: PathTaken,
        metadata: dict[str, Any],
        particle_obs: dict[str, ParticleObservable] | None = None,
    ) -> tuple[Path, "ProvenanceRecord"]:
        qcompass_core = importlib.import_module("qcompass_core")
        provenance = qcompass_core.emit_provenance(
            classical_reference_hash=classical_hash,
            calibration_hash=None,
            error_mitigation=None,
        )
        self._artifacts_root.mkdir(parents=True, exist_ok=True)
        sidecar = self._artifacts_root / f"{instance.run_id}.provenance.json"
        envelope = {
            "schemaVersion": 1,
            "runId": instance.run_id,
            "domain": HEPSimulation.domain_name,
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
            "particle_obs": particle_obs or {},
        }
        sidecar.write_text(json.dumps(envelope, indent=2, default=str))
        return sidecar, provenance


def _resolve_path(preference: str) -> PathTaken:
    if preference in {"classical", "ibm", "ionq", "scadapt_vqe"}:
        return preference  # type: ignore[return-value]
    if preference == "auto":
        for candidate, module in (("ibm", "qiskit_aer"), ("ionq", "braket")):
            try:
                importlib.import_module(module)
                return candidate  # type: ignore[return-value]
            except ImportError:
                continue
        return "classical"
    msg = f"Unknown backend_preference: {preference!r}"
    raise ValueError(msg)


def _default_artifacts_root() -> Path:
    env = os.environ.get("QCOMPASS_ARTIFACTS")
    if env:
        return Path(env)
    return Path.home() / ".qcompass" / "artifacts"
