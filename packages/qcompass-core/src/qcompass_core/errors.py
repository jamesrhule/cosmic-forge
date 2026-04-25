"""Error hierarchy for the qcompass-core protocol layer.

All exceptions raised by qcompass-core (and recommended for
qfull-* implementers) inherit from :class:`QCompassError` so callers
can catch the family with a single ``except`` clause.
"""

from __future__ import annotations


class QCompassError(Exception):
    """Base class for every qcompass-core exception."""


class ManifestValidationError(QCompassError):
    """Raised when a :class:`Manifest` fails Pydantic validation."""


class UnknownDomainError(QCompassError):
    """Raised by the registry when a requested domain name is not registered."""


class ProvenanceError(QCompassError):
    """Raised when a :class:`ProvenanceRecord` cannot be assembled or verified."""


class BackendUnavailableError(QCompassError):
    """Raised by the M14 router when no backend can satisfy the request."""


class ResourceEstimationError(QCompassError):
    """Raised when an M12 estimator adapter cannot return an estimate."""


class HamiltonianFormatError(QCompassError):
    """Raised when an M11 input file cannot be parsed."""


class ClassicalReferenceError(QCompassError):
    """Raised when an M13 reference adapter fails (missing dep, runtime error)."""
