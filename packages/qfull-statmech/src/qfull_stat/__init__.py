"""qfull-statmech — QAE / quantum Metropolis / TFD domain plugin."""

from __future__ import annotations

from .classical import ClassicalOutcome, compute_reference
from .manifest import (
    BackendPreference,
    IsingMetropolisParams,
    ProblemKind,
    QAEParams,
    StatmechProblem,
    TFDParams,
    load_instance,
)
from .sim import (
    PathTaken,
    StatmechInstance,
    StatmechResult,
    StatmechSimulation,
)

__version__ = "0.1.0"

__all__ = [
    "BackendPreference",
    "ClassicalOutcome",
    "IsingMetropolisParams",
    "PathTaken",
    "ProblemKind",
    "QAEParams",
    "StatmechInstance",
    "StatmechProblem",
    "StatmechResult",
    "StatmechSimulation",
    "TFDParams",
    "compute_reference",
    "load_instance",
]
