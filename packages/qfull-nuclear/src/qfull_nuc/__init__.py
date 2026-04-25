"""qfull-nuclear — ab-initio nuclear domain plugin for QCompass."""

from __future__ import annotations

from .classical import ClassicalOutcome, compute_reference
from .manifest import (
    BackendPreference,
    NCSMParams,
    NuclearProblem,
    ProblemKind,
    ZeroNuBBToyParams,
    load_instance,
)
from .quantum_ibm import IBMOutcome, run_ibm
from .quantum_ionq import IonQOutcome, run_ionq
from .sim import (
    NuclearInstance,
    NuclearResult,
    NuclearSimulation,
    PathTaken,
)

__version__ = "0.1.0"

__all__ = [
    "BackendPreference",
    "ClassicalOutcome",
    "IBMOutcome",
    "IonQOutcome",
    "NCSMParams",
    "NuclearInstance",
    "NuclearProblem",
    "NuclearResult",
    "NuclearSimulation",
    "PathTaken",
    "ProblemKind",
    "ZeroNuBBToyParams",
    "compute_reference",
    "load_instance",
    "run_ibm",
    "run_ionq",
]
