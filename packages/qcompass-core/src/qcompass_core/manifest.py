"""Manifest envelope and provenance record.

A :class:`Manifest` is the typed, JSON-serialisable description of a
single problem to be solved by a domain plugin. Every qfull-* package
accepts a Manifest via :meth:`Simulation.prepare` and emits a
:class:`ProvenanceRecord` alongside its Result so downstream tools
(qcompass-bench, qcompass-router, audit harnesses) can attribute
every numeric output to its inputs and the classical / quantum
references used to validate it.

The envelope is intentionally domain-agnostic: the ``problem`` field
is a free-form ``dict`` whose schema is defined by the receiving
plugin's :meth:`Simulation.manifest_schema`. Using ``dict`` rather
than a polymorphic discriminator keeps qcompass-core decoupled from
any specific qfull-* package — it MUST stay so per the package
boundary rule.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Domains keyed by qfull-* package suffix. Adding a new domain ALSO
# requires registering a plugin entry-point — that is the source of
# truth at runtime; this Literal is the source of truth at type-check
# time and during static schema validation.
DomainName = Literal[
    "cosmology",
    "chemistry",
    "condmat",
    "hep",
    "nuclear",
    "amo",
    "gravity",
    "statmech",
    # The "null" domain is reserved for in-process tests and the
    # built-in NullSim plugin shipped with qcompass-core.
    "null",
]


class BackendRequest(BaseModel):
    """How the caller wants the simulation executed.

    The router (M14) maps this to a concrete :class:`QBackend`
    instance. ``priority`` lets a caller express "I prefer quantum
    hardware but accept the classical reference if no QPU is
    available within budget".
    """

    model_config = ConfigDict(extra="forbid", serialize_by_alias=True)

    kind: Literal["classical", "quantum_simulator", "quantum_hardware", "auto"]
    target: str | None = Field(
        default=None,
        description="Specific backend identifier, e.g. 'local_aer', 'ibm_brisbane'.",
    )
    priority: list[str] = Field(
        default_factory=list,
        description="Ordered fallback list of backend identifiers.",
    )
    shots: int = Field(default=1024, ge=1)
    seed: int | None = Field(default=0)
    max_runtime_seconds: float = Field(default=3600.0, gt=0.0)


class ResourceEstimate(BaseModel):
    """Common output type for every M12 estimator adapter."""

    model_config = ConfigDict(extra="forbid", serialize_by_alias=True)

    physical_qubits: int = Field(ge=0)
    logical_qubits: int = Field(ge=0)
    t_count: int = Field(ge=0)
    rotation_count: int = Field(ge=0)
    depth: int = Field(ge=0)
    runtime_seconds: float = Field(ge=0.0)
    estimator: Literal["microsoft", "qrechem", "tfermion", "stub"]
    notes: str = ""


class ProvenanceRecord(BaseModel):
    """Output-side attribution.

    Attached to every :class:`Result` so downstream consumers can
    answer:
      - *which classical reference* validates this run?
      - *which device calibration* underpins the quantum data?
      - *which error-mitigation policy* was applied?
    """

    model_config = ConfigDict(extra="forbid", serialize_by_alias=True)

    classical_reference_hash: str
    resource_estimate: ResourceEstimate | None = None
    device_calibration_hash: str | None = None
    error_mitigation_config: dict[str, Any] | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class Manifest(BaseModel):
    """Top-level envelope handed to :meth:`Simulation.prepare`.

    Example
    -------
    >>> Manifest(
    ...     domain="null",
    ...     version="1.0",
    ...     problem={"label": "noop"},
    ...     backend_request=BackendRequest(kind="classical"),
    ... )
    """

    model_config = ConfigDict(extra="forbid", serialize_by_alias=True)

    domain: DomainName
    version: str = Field(pattern=r"^\d+\.\d+(?:\.\d+)?$")
    problem: dict[str, Any]
    backend_request: BackendRequest
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("problem")
    @classmethod
    def _problem_not_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            msg = "Manifest.problem must not be empty."
            raise ValueError(msg)
        return value
