"""qfull-gravity — SYK / JT / sparse-SYK domain plugin for QCompass."""

from __future__ import annotations

from .classical import ClassicalOutcome, compute_reference
from .manifest import (
    BackendPreference,
    GravityProblem,
    JTParams,
    ModelDomain,
    ProblemKind,
    SparseSYKParams,
    SYKParams,
    load_instance,
    model_domain_for_kind,
)
from .sim import (
    GravityInstance,
    GravityResult,
    GravitySimulation,
    PathTaken,
)

__version__ = "0.1.0"

__all__ = [
    "BackendPreference",
    "ClassicalOutcome",
    "GravityInstance",
    "GravityProblem",
    "GravityResult",
    "GravitySimulation",
    "JTParams",
    "ModelDomain",
    "PathTaken",
    "ProblemKind",
    "SYKParams",
    "SparseSYKParams",
    "compute_reference",
    "load_instance",
    "model_domain_for_kind",
]
