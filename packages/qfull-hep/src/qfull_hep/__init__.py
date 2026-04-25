"""qfull-hep — high-energy / lattice-gauge domain plugin for QCompass."""

from __future__ import annotations

from .classical import ClassicalOutcome, compute_reference
from .manifest import (
    BackendPreference,
    HEPProblem,
    ProblemKind,
    SU2Params,
    SchwingerParams,
    ZNParams,
    load_instance,
)
from .quantum_ibm import IBMOutcome, run_ibm
from .quantum_ionq import IonQOutcome, run_ionq
from .scadapt_vqe import is_available as scadapt_vqe_available
from .sim import (
    HEPInstance,
    HEPResult,
    HEPSimulation,
    PathTaken,
)

__version__ = "0.1.0"

__all__ = [
    "BackendPreference",
    "ClassicalOutcome",
    "HEPInstance",
    "HEPProblem",
    "HEPResult",
    "HEPSimulation",
    "IBMOutcome",
    "IonQOutcome",
    "PathTaken",
    "ProblemKind",
    "SU2Params",
    "SchwingerParams",
    "ZNParams",
    "compute_reference",
    "load_instance",
    "run_ibm",
    "run_ionq",
    "scadapt_vqe_available",
]
