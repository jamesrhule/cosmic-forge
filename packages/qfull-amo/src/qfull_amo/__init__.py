"""qfull-amo — neutral-atom Rydberg / cold-atom domain plugin for QCompass."""

from __future__ import annotations

from .classical import ClassicalOutcome, compute_reference
from .manifest import (
    AMOProblem,
    BackendPreference,
    MISParams,
    ProblemKind,
    RydbergParams,
    load_instance,
)
from .quantum_analog import AnalogOutcome, run_analog
from .quantum_bloqade import BloqadeOutcome, run_bloqade
from .quantum_pulser import PulserOutcome, run_pulser
from .sim import (
    AMOInstance,
    AMOResult,
    AMOSimulation,
    PathTaken,
)

__version__ = "0.1.0"

__all__ = [
    "AMOInstance",
    "AMOProblem",
    "AMOResult",
    "AMOSimulation",
    "AnalogOutcome",
    "BackendPreference",
    "BloqadeOutcome",
    "ClassicalOutcome",
    "MISParams",
    "PathTaken",
    "ProblemKind",
    "PulserOutcome",
    "RydbergParams",
    "compute_reference",
    "load_instance",
    "run_analog",
    "run_bloqade",
    "run_pulser",
]
