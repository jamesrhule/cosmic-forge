"""qcompass.Simulation adapter for the cosmology.ucglef1 plugin.

Exposes the existing UCGLE-F1 M1-M7 pipeline through the
:class:`qcompass_core.Simulation` protocol. ZERO edits to M1-M8
internals: this file only constructs and dispatches into the public
``RunPipeline.run`` + ``build_run_result`` surface.

The adapter is registered in ``backend/pyproject.toml`` under

    [project.entry-points."qcompass.domains"]
    cosmology.ucglef1 = "ucgle_f1.adapters.qcompass:LeptogenesisSimulation"

so :func:`qcompass_core.get_simulation('cosmology.ucglef1')` returns
this class once both packages are installed.

Soft-import contract: importing this module without qcompass-core
present succeeds. Instantiating :class:`LeptogenesisSimulation`
without qcompass-core raises a clear :class:`ImportError`. This
keeps cosmic-forge's base install lean while making the contract
observable for type-checkers (which see the protocol annotations).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..domain import RunConfig, RunResult
from ..m7_infer.audit import run_audit
from ..m7_infer.pipeline import RunPipeline, build_run_result
from .cosmology_manifest import CosmologyManifest, to_run_config

if TYPE_CHECKING:  # pragma: no cover - typing-only imports
    from qcompass_core import Manifest, ProvenanceRecord


def _qcompass_required(symbol: str) -> "Any":
    """Raise a clear error when qcompass-core is missing.

    Called from :class:`LeptogenesisSimulation` constructors / methods
    that genuinely need qcompass-core types. Importers of *this* module
    that never instantiate the adapter never trip this guard.
    """
    msg = (
        f"qcompass-core is required to use {symbol}. "
        "Install with `pip install ucgle_f1[qcompass]` or add "
        "`qcompass-core>=0.1,<0.2` to your environment."
    )
    raise ImportError(msg)


@dataclass
class CosmologyInstance:
    """Materialised problem the adapter operates on.

    ``run_id`` is generated at :meth:`prepare` time so the provenance
    sidecar can be addressed before :meth:`run` completes.
    """

    run_id: str
    cfg: RunConfig
    raw_manifest: dict[str, Any]


@dataclass
class CosmologyResult:
    """Output of :meth:`LeptogenesisSimulation.run`."""

    instance: CosmologyInstance
    run_result: RunResult
    eta_B: float
    F_GB: float
    provenance: "ProvenanceRecord"
    sidecar_path: Path
    backend_name: str
    wall_seconds: float
    extra: dict[str, Any] = field(default_factory=dict)


class LeptogenesisSimulation:
    """qcompass.Simulation wrapper around the M1-M7 pipeline.

    ``backend`` is accepted but not consumed: the existing pipeline
    runs on the host CPU. We record the backend name in the result so
    callers can correlate with their :class:`BackendRequest`.
    """

    domain_name: str = "cosmology.ucglef1"

    def __init__(self, *, seed: int = 0, artifacts_root: Path | str | None = None):
        self._seed = int(seed)
        self._artifacts_root = (
            Path(artifacts_root)
            if artifacts_root is not None
            else _default_artifacts_root()
        )

    # ── qcompass.Simulation protocol ──────────────────────────────

    def prepare(self, manifest: "Manifest") -> CosmologyInstance:
        manifest = self._coerce_manifest(manifest)
        if manifest.domain not in {"cosmology", "gravity"}:
            msg = (
                f"LeptogenesisSimulation expects domain='cosmology' (or "
                f"'gravity'), got {manifest.domain!r}."
            )
            raise ValueError(msg)
        problem = CosmologyManifest.model_validate(manifest.problem)
        cfg = to_run_config(problem)
        run_id = f"qcrun_{secrets.token_hex(6)}"
        return CosmologyInstance(
            run_id=run_id,
            cfg=cfg,
            raw_manifest=manifest.model_dump(),
        )

    def run(self, instance: CosmologyInstance, backend: object) -> CosmologyResult:
        t0 = time.perf_counter()
        pr = RunPipeline(seed=self._seed).run(instance.cfg)
        run_result = build_run_result(
            run_id=instance.run_id,
            cfg=instance.cfg,
            pr=pr,
            audit_runner=run_audit,
        )
        wall = time.perf_counter() - t0

        sidecar_path, provenance = self._write_provenance(
            instance,
            run_result=run_result,
            backend_name=getattr(backend, "name", "classical_cpu"),
        )
        return CosmologyResult(
            instance=instance,
            run_result=run_result,
            eta_B=run_result.eta_B.value,
            F_GB=run_result.F_GB,
            provenance=provenance,
            sidecar_path=sidecar_path,
            backend_name=getattr(backend, "name", "classical_cpu"),
            wall_seconds=wall,
        )

    def validate(
        self,
        result: CosmologyResult,
        reference: float | None,
    ) -> dict[str, Any]:
        """Compare against a literature ``η_B`` value (or skip if ``None``).

        The reference is the *target* literature value (e.g. V2's
        6.1×10⁻¹⁰); the audit details are already captured in
        ``result.run_result.audit``. We surface a compact summary
        the caller can record in their bench harness.
        """
        eta = result.eta_B
        if reference is None or reference == 0.0:
            relative_error = None
        else:
            relative_error = abs(eta - reference) / abs(reference)
        return {
            "domain": self.domain_name,
            "eta_B": eta,
            "F_GB": result.F_GB,
            "reference": reference,
            "relative_error": relative_error,
            "audit_summary": result.run_result.audit.summary.model_dump(),
            "wall_seconds": result.wall_seconds,
            "provenance_sidecar": str(result.sidecar_path),
        }

    @classmethod
    def manifest_schema(cls) -> dict[str, Any]:
        """JSON Schema for the ``Manifest.problem`` payload."""
        return CosmologyManifest.model_json_schema()

    # ── Private helpers ───────────────────────────────────────────

    def _coerce_manifest(self, manifest: "Manifest" | dict[str, Any]) -> "Manifest":
        try:
            from qcompass_core import Manifest as QCManifest
        except ImportError:  # pragma: no cover - exercised in CI
            _qcompass_required("LeptogenesisSimulation.prepare")

        if isinstance(manifest, QCManifest):
            return manifest
        if isinstance(manifest, dict):
            return QCManifest.model_validate(manifest)
        msg = f"Expected qcompass_core.Manifest or dict, got {type(manifest).__name__}."
        raise TypeError(msg)

    def _write_provenance(
        self,
        instance: CosmologyInstance,
        *,
        run_result: RunResult,
        backend_name: str,
    ) -> tuple[Path, "ProvenanceRecord"]:
        try:
            from qcompass_core import emit_provenance
        except ImportError:  # pragma: no cover - exercised in CI
            _qcompass_required("LeptogenesisSimulation.run")

        result_blob = run_result.model_dump(mode="json")
        canonical = json.dumps(
            result_blob, sort_keys=True, separators=(",", ":")
        ).encode()
        ref_hash = hashlib.sha256(canonical).hexdigest()
        provenance = emit_provenance(
            classical_reference_hash=ref_hash,
            calibration_hash=None,
            error_mitigation=None,
        )

        self._artifacts_root.mkdir(parents=True, exist_ok=True)
        sidecar = self._artifacts_root / f"{instance.run_id}.provenance.json"
        # Canonical JSON layout so the sidecar itself is hash-stable
        # and diff-friendly. Pydantic's default ordering is preserved
        # via ``model_dump_json`` for the provenance record + a small
        # envelope describing the run.
        envelope = {
            "schemaVersion": 1,
            "runId": instance.run_id,
            "domain": LeptogenesisSimulation.domain_name,
            "backend": backend_name,
            "createdAt": datetime.now(UTC).isoformat(),
            "manifest": instance.raw_manifest,
            "provenance": provenance.model_dump(mode="json"),
            "metrics": {
                "eta_B": run_result.eta_B.value,
                "F_GB": run_result.F_GB,
                "audit_passed": run_result.audit.summary.passed,
                "audit_total": run_result.audit.summary.total,
            },
        }
        sidecar.write_text(json.dumps(envelope, indent=2, sort_keys=False))
        return sidecar, provenance


def _default_artifacts_root() -> Path:
    """Resolve the artifacts root.

    Honours ``UCGLE_F1_ARTIFACTS`` (already used by the M8 agent
    sandbox) so adapter sidecars co-locate with the rest of the run
    artifacts, then falls back to ``~/.ucgle_f1/artifacts``.
    """
    env = os.environ.get("UCGLE_F1_ARTIFACTS")
    if env:
        return Path(env)
    return Path.home() / ".ucgle_f1" / "artifacts"
