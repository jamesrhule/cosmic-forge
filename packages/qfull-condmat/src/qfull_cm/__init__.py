"""qfull-condmat — condensed-matter domain plugin for QCompass."""

from __future__ import annotations

from .classical import ClassicalOutcome, compute_reference
from .manifest import (
    BackendPreference,
    CondMatProblem,
    FrustratedParams,
    HeisenbergParams,
    HubbardParams,
    LatticeName,
    OtocParams,
    ProblemKind,
    load_instance,
)
from .quantum_analog import AnalogOutcome, run_analog
from .quantum_ibm import IBMOutcome, run_ibm
from .sim import (
    CondMatInstance,
    CondMatResult,
    CondMatSimulation,
    PathTaken,
)

__version__ = "0.1.0"

__all__ = [
    "AnalogOutcome",
    "BackendPreference",
    "ClassicalOutcome",
    "CondMatInstance",
    "CondMatProblem",
    "CondMatResult",
    "CondMatSimulation",
    "FrustratedParams",
    "HeisenbergParams",
    "HubbardParams",
    "IBMOutcome",
    "LatticeName",
    "OtocParams",
    "PathTaken",
    "ProblemKind",
    "compute_reference",
    "load_instance",
    "run_analog",
    "run_ibm",
]
