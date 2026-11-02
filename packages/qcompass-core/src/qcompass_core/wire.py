"""Wire contract shared with the workbench frontend.

Mirrors the TypeScript types in ``src/lib/domains/types.ts``
(``DomainRunResult``, ``ProvenanceRecordExt``, ``ParticleObservable``,
``RunSummary``) and the verdict sample in
``public/fixtures/verdict/sample-verdict.yaml``. The FastAPI compute API
uses these as response models; the frontend fixtures validate against
them (``backend/tests/test_lovable_contract.py``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DomainId = Literal[
    "cosmology.ucglef1",
    "chemistry.molecular",
    "condmat.lattice",
    "amo.rydberg",
    "hep.lattice",
    "nuclear.structure",
    "gravity.syk",
    "statmech.sampling",
]

RunStatus = Literal["queued", "running", "completed", "failed"]
ModelDomain = Literal["1+1D_toy", "few_body_3d", "effective_hamiltonian"]


class _Wire(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResourceEstimateWire(_Wire):
    logical_qubits: int | None = None
    physical_qubits: int | None = None
    wallclock_s: float | None = None


class ProvenanceRecordExt(_Wire):
    classical_reference_hash: str | None = None
    device_calibration_hash: str | None = None
    device_calibration_at: str | None = None
    error_mitigation_config: dict[str, Any] | None = None
    resource_estimate: ResourceEstimateWire | None = None
    transforms_applied: list[str] | None = None
    model_domain: str | None = None
    provenance_warning: str | None = None
    is_learned_hamiltonian: bool | None = None
    arxiv_reference: str | None = None


class ParticleObservableWire(_Wire):
    label: str
    value: float
    uncertainty: float
    units: str
    provider: str
    backend: str
    calibration_at: str


class DomainRunResult(_Wire):
    id: str
    domain: DomainId
    label: str
    status: RunStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceRecordExt
    created_at: str
    particle_obs: dict[str, ParticleObservableWire] | None = None
    model_domain: ModelDomain | None = None
    is_learned_hamiltonian: bool | None = None
    synthetic: bool | None = None


class RunSummary(_Wire):
    id: str
    label: str
    status: RunStatus
    domain: DomainId
    created_at: str
    summary: str | None = None


class VerdictRow(_Wire):
    domain: DomainId
    status: Literal["DELIVERED", "PENDING", "FAILED"]
    evidence: list[str] = Field(default_factory=list)
    notes: str | None = None
    audit_archive_url: str | None = None


class VerdictSample(_Wire):
    generated_at: datetime
    reviewer: str
    rows: list[VerdictRow]


__all__ = [
    "DomainId",
    "DomainRunResult",
    "ModelDomain",
    "ParticleObservableWire",
    "ProvenanceRecordExt",
    "ResourceEstimateWire",
    "RunStatus",
    "RunSummary",
    "VerdictRow",
    "VerdictSample",
]
