"""qfull-nuclear — ab-initio nuclear domain plugin for QCompass."""

from __future__ import annotations

from .classical import ClassicalOutcome, compute_reference
from .manifest import (
    BackendPreference,
    EffectiveHamiltonianParams,
    HypotheticalSearch,
    ModelDomain,
    NCSMParams,
    NuclearProblem,
    ProblemKind,
    ZeroNuBBToyParams,
    load_instance,
    model_domain_for_kind,
)
from .particle_obs import ParticleObservable, build_particle_obs
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
    "EffectiveHamiltonianParams",
    "HypotheticalSearch",
    "IBMOutcome",
    "IonQOutcome",
    "ModelDomain",
    "NCSMParams",
    "NuclearInstance",
    "NuclearProblem",
    "NuclearResult",
    "NuclearSimulation",
    "ParticleObservable",
    "PathTaken",
    "ProblemKind",
    "ZeroNuBBToyParams",
    "build_particle_obs",
    "compute_reference",
    "load_instance",
    "model_domain_for_kind",
    "run_ibm",
    "run_ionq",
]
