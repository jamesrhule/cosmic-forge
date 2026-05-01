"""qcompass-core — domain-agnostic protocols, registry, and base modules.

Public surface
--------------
- :class:`Manifest`, :class:`BackendRequest`, :class:`ProvenanceRecord`,
  :class:`ResourceEstimate` — typed envelope.
- :class:`Simulation`, :class:`QProvider`, :class:`QBackend`,
  :class:`QEstimator` — PEP 544 protocols.
- :func:`get_simulation`, :func:`list_domains`, :func:`register` —
  plugin registry.
- :class:`Router`, :func:`get_backend`, :func:`available_backends`,
  :func:`register_provider` — M14 router.
- :class:`FCIDUMP`, :func:`read_fcidump`, :class:`SpinHamiltonian` — M11.
- :class:`StubEstimator`, :class:`AzureMicrosoftEstimatorAdapter`,
  :class:`QREChemAdapter`, :class:`TFermionAdapter` — M12 adapters.
- :class:`PySCFAdapter`, :class:`Block2Adapter`, :class:`QuimbAdapter`,
  :class:`IpieAdapter` — M13 adapters.

The built-in ``null`` plugin is registered via the
``qcompass.domains`` entry-point group.
"""

from __future__ import annotations

from .errors import (
    BackendUnavailableError,
    ClassicalReferenceError,
    HamiltonianFormatError,
    ManifestValidationError,
    ProvenanceError,
    QCompassError,
    ResourceEstimationError,
    UnknownDomainError,
)
from .m11_hamiltonians import (
    FCIDUMP,
    LQCDHDF5Schema,
    SpinHamiltonian,
    read_fcidump,
    read_lqcd_hdf5,
    validate_spin_hamiltonian,
)
from .m12_resource_estimator import (
    AzureMicrosoftEstimatorAdapter,
    QREChemAdapter,
    StubEstimator,
    TFermionAdapter,
)
from .m13_classical_reference import (
    Block2Adapter,
    ClassicalReference,
    IpieAdapter,
    PySCFAdapter,
    QuimbAdapter,
    hash_payload,
)
from .m14_backend_router import (
    ClassicalCPUBackend,
    LocalAerBackend,
    Router,
    available_backends,
    get_backend,
    register_provider,
    reset_router,
)
from .manifest import (
    BackendRequest,
    DomainName,
    Manifest,
    ProvenanceRecord,
    ResourceEstimate,
)
from .protocols import (
    QBackend,
    QEstimator,
    QProvider,
    Simulation,
    emit_provenance,
)
from .registry import get_simulation, list_domains, register, reset_registry

__version__ = "0.1.0"

__all__ = [
    "AzureMicrosoftEstimatorAdapter",
    "BackendRequest",
    "BackendUnavailableError",
    "Block2Adapter",
    "ClassicalCPUBackend",
    "ClassicalReference",
    "ClassicalReferenceError",
    "DomainName",
    "FCIDUMP",
    "HamiltonianFormatError",
    "IpieAdapter",
    "LocalAerBackend",
    "Manifest",
    "ManifestValidationError",
    "ProvenanceError",
    "ProvenanceRecord",
    "PySCFAdapter",
    "QBackend",
    "QCompassError",
    "QEstimator",
    "QProvider",
    "QREChemAdapter",
    "QuimbAdapter",
    "ResourceEstimate",
    "ResourceEstimationError",
    "LQCDHDF5Schema",
    "Router",
    "Simulation",
    "SpinHamiltonian",
    "StubEstimator",
    "TFermionAdapter",
    "UnknownDomainError",
    "available_backends",
    "emit_provenance",
    "get_backend",
    "get_simulation",
    "hash_payload",
    "list_domains",
    "read_fcidump",
    "read_lqcd_hdf5",
    "register",
    "register_provider",
    "reset_registry",
    "reset_router",
    "validate_spin_hamiltonian",
]
