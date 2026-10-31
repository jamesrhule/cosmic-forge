"""ChemistrySimulation — qcompass.Simulation protocol implementation.

Mirrors the structural pattern of
``backend/src/ucgle_f1/adapters/qcompass.py::LeptogenesisSimulation``:

- qcompass-core imports are deferred to method bodies so this module
  can be imported on a base install without the optional dep.
- ``run()`` writes a provenance sidecar to
  ``${QCOMPASS_ARTIFACTS:-~/.qcompass/artifacts}/<run_id>.provenance.json``.
- ``validate()`` returns a typed dict summary the bench harness
  records.

Backend dispatch:
    classical → :func:`classical.compute_reference`
    sqd       → :func:`quantum_sqd.run_sqd`     (paired with classical)
    dice      → :func:`quantum_dice.run_dice`   (paired with classical, Linux only)
    auto      → SQD when its SDK is importable; else classical.
"""

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
from .manifest import ChemistryProblem
from .quantum_dice import is_dice_available, run_dice
from .quantum_sqd import run_sqd

if TYPE_CHECKING:  # pragma: no cover - typing-only imports
    from qcompass_core import Manifest, ProvenanceRecord


PathTaken = Literal["classical", "sqd", "dice"]


@dataclass
class ChemistryInstance:
    """Materialised problem the simulation operates on."""

    run_id: str
    problem: ChemistryProblem
    raw_manifest: dict[str, Any]


@dataclass
class ChemistryResult:
    """Output of :meth:`ChemistrySimulation.run`."""

    instance: ChemistryInstance
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


class ChemistrySimulation:
    """qcompass.Simulation wrapper for the chemistry domain."""

    domain_name: str = "chemistry"

    def __init__(self, *, artifacts_root: Path | str | None = None) -> None:
        self._artifacts_root = (
            Path(artifacts_root)
            if artifacts_root is not None
            else _default_artifacts_root()
        )

    # ── qcompass.Simulation protocol ──────────────────────────────

    def prepare(self, manifest: "Manifest" | dict[str, Any]) -> ChemistryInstance:
        manifest_obj = self._coerce_manifest(manifest)
        if manifest_obj.domain != "chemistry":
            msg = (
                f"ChemistrySimulation expects domain='chemistry', "
                f"got {manifest_obj.domain!r}."
            )
            raise ValueError(msg)
        problem = ChemistryProblem.model_validate(manifest_obj.problem)
        run_id = f"qcchem_{secrets.token_hex(6)}"
        return ChemistryInstance(
            run_id=run_id,
            problem=problem,
            raw_manifest=manifest_obj.model_dump(),
        )

    def run(self, instance: ChemistryInstance, backend: object) -> ChemistryResult:
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
        elif path == "sqd":
            sqd = run_sqd(instance.problem)
            classical_energy = sqd.classical_energy
            classical_hash = sqd.classical_hash
            classical_method = sqd.classical_method
            classical_warning = sqd.classical_warning
            quantum_energy = sqd.sqd_energy
            metadata = sqd.metadata
        elif path == "dice":
            dice = run_dice(instance.problem)
            classical_energy = dice.classical_energy
            classical_hash = dice.classical_hash
            classical_method = dice.classical_method
            classical_warning = dice.classical_warning
            quantum_energy = dice.dice_energy
            metadata = dice.metadata
        else:  # pragma: no cover - guarded by Literal
            msg = f"Unknown path: {path!r}"
            raise RuntimeError(msg)

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
        return ChemistryResult(
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
        self,
        result: ChemistryResult,
        reference: float | None,
    ) -> dict[str, Any]:
        """Compare against an external reference (e.g. literature value)."""
        primary_energy = (
            result.quantum_energy
            if result.quantum_energy is not None
            else result.classical_energy
        )
        relative_error: float | None
        if reference is None or reference == 0.0:
            relative_error = None
        else:
            relative_error = abs(primary_energy - reference) / abs(reference)
        return {
            "domain": self.domain_name,
            "molecule": result.instance.problem.molecule,
            "path_taken": result.path_taken,
            "classical_energy": result.classical_energy,
            "quantum_energy": result.quantum_energy,
            "classical_method": result.classical_method,
            "classical_hash": result.classical_hash,
            "provenance_warning": result.classical_warning,
            "reference": reference,
            "relative_error": relative_error,
            "provenance_sidecar": str(result.sidecar_path),
        }

    @classmethod
    def manifest_schema(cls) -> dict[str, Any]:
        return ChemistryProblem.model_json_schema()

    # ── Private helpers ───────────────────────────────────────────

    def _coerce_manifest(
        self, manifest: "Manifest" | dict[str, Any]
    ) -> "Manifest":
        try:
            qcompass_core = importlib.import_module("qcompass_core")
        except ImportError as exc:  # pragma: no cover - exercised in CI
            msg = (
                "qcompass-core is required for ChemistrySimulation. "
                "Install with `pip install qfull-chemistry` (qcompass-core "
                "is a base dependency)."
            )
            raise ImportError(msg) from exc
        manifest_cls = qcompass_core.Manifest
        if isinstance(manifest, manifest_cls):
            return manifest
        if isinstance(manifest, dict):
            return manifest_cls.model_validate(manifest)
        msg = (
            f"Expected qcompass_core.Manifest or dict, got "
            f"{type(manifest).__name__}."
        )
        raise TypeError(msg)

    def _write_provenance(
        self,
        instance: ChemistryInstance,
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
        emit_provenance = qcompass_core.emit_provenance

        provenance = emit_provenance(
            classical_reference_hash=classical_hash,
            calibration_hash=None,
            error_mitigation=None,
        )

        self._artifacts_root.mkdir(parents=True, exist_ok=True)
        sidecar = self._artifacts_root / f"{instance.run_id}.provenance.json"

        envelope = {
            "schemaVersion": 1,
            "runId": instance.run_id,
            "domain": ChemistrySimulation.domain_name,
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


# ── Module helpers ────────────────────────────────────────────────────


def _resolve_path(preference: str) -> PathTaken:
    """Resolve the user's ``backend_preference`` to a concrete path."""
    if preference == "classical":
        return "classical"
    if preference == "sqd":
        return "sqd"
    if preference == "dice":
        return "dice"
    if preference == "auto":
        # Prefer SQD when available; degrade to classical.
        try:
            importlib.import_module("qiskit_addon_sqd")
            return "sqd"
        except ImportError:
            return "classical"
    msg = f"Unknown backend_preference: {preference!r}"
    raise ValueError(msg)


def _default_artifacts_root() -> Path:
    """Resolve the artifacts root.

    Honours ``QCOMPASS_ARTIFACTS`` (workspace-level convention) so
    every qfull-* package writes to the same location, and falls
    back to ``~/.qcompass/artifacts``.
    """
    env = os.environ.get("QCOMPASS_ARTIFACTS")
    if env:
        return Path(env)
    return Path.home() / ".qcompass" / "artifacts"
