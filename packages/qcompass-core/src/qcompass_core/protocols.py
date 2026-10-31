"""PEP 544 typing.Protocol contracts for QCompass plugins.

Every qfull-* package implements :class:`Simulation`. Quantum plugins
additionally implement :class:`QProvider` / :class:`QBackend` /
:class:`QEstimator` so the M14 router and M12 estimator can dispatch
without importing the implementations.

All four protocols are :func:`runtime_checkable` so callers can use
``isinstance(obj, Simulation)`` for reflective dispatch — handy for
the registry's lookup and for the test harness when a plugin is
registered programmatically (no entry-point installed).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .manifest import Manifest, ProvenanceRecord, ResourceEstimate

# --- Opaque domain types ------------------------------------------------------
# We deliberately keep these as `Any` aliases. Each plugin defines its
# own concrete dataclasses (e.g. a chemistry plugin might use a
# `Molecule` instance for `Instance`). qcompass-core must remain
# domain-agnostic, so we only describe the *positions* in the protocol.


Instance = Any
Result = Any
Reference = Any
AuditStub = Any


@runtime_checkable
class Simulation(Protocol):
    """A domain plugin entry point.

    Lifecycle: ``prepare`` materialises an instance from a manifest;
    ``run`` executes it on a backend; ``validate`` compares the result
    to a classical or analytical reference and returns a
    :class:`AuditStub` that the bench harness records.
    """

    def prepare(self, manifest: Manifest) -> Instance:
        """Materialise an :class:`Instance` from a validated manifest."""

    def run(self, instance: Instance, backend: "QBackend") -> Result:
        """Execute ``instance`` on ``backend`` and return a result."""

    def validate(self, result: Result, reference: Reference) -> AuditStub:
        """Compare ``result`` against ``reference``; return an audit stub."""

    @classmethod
    def manifest_schema(cls) -> dict[str, Any]:
        """Return the JSON Schema this plugin accepts under ``Manifest.problem``."""


@runtime_checkable
class QProvider(Protocol):
    """A vendor or simulator integration (IBM, Azure, IonQ, local Aer, …).

    The provider is the factory layer that yields backends. M14
    introspects providers to populate the catalogue.
    """

    name: str

    def list_backends(self) -> list[str]:
        """Names of backends this provider can hand out."""

    def get_backend(self, name: str) -> "QBackend":
        """Return the named backend or raise :class:`BackendUnavailableError`."""


@runtime_checkable
class QBackend(Protocol):
    """A concrete execution target.

    Quantum simulators, real QPUs, and the classical-CPU fallback all
    satisfy this protocol. Each carries a snapshotable
    :attr:`calibration_hash` so the :class:`ProvenanceRecord` can
    attribute every shot to a specific device + calibration epoch.
    """

    name: str
    provider: str
    calibration_hash: str | None

    def submit(self, payload: Any, *, shots: int, seed: int | None) -> Any:
        """Submit a payload (e.g. circuit, transpiled IR) for execution."""

    def cost_estimate(self, payload: Any) -> ResourceEstimate:
        """Approximate the cost of running ``payload`` on this backend."""


@runtime_checkable
class QEstimator(Protocol):
    """Resource-estimator adapter (M12).

    Implementations wrap an external estimator (Microsoft Resource
    Estimator, QREChem, TFermion, …) and return a unified
    :class:`ResourceEstimate`. Heavy SDKs are imported lazily so the
    base install of qcompass-core stays light.
    """

    name: str

    def estimate(self, manifest: Manifest, payload: Any) -> ResourceEstimate:
        """Return a unified resource estimate for ``payload``."""


def emit_provenance(
    classical_reference_hash: str,
    *,
    estimate: ResourceEstimate | None = None,
    calibration_hash: str | None = None,
    error_mitigation: dict[str, Any] | None = None,
) -> ProvenanceRecord:
    """Convenience constructor used by plugins to emit a record.

    Plugins typically have all four pieces of information at the end
    of :meth:`Simulation.run` and call this once. Keeping the
    constructor here means qfull-* packages do not have to know the
    field names of :class:`ProvenanceRecord` — only the keyword
    arguments here.
    """
    return ProvenanceRecord(
        classical_reference_hash=classical_reference_hash,
        resource_estimate=estimate,
        device_calibration_hash=calibration_hash,
        error_mitigation_config=error_mitigation,
    )
