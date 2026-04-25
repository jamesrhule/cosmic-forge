"""qfull-chemistry — chemistry domain plugin for QCompass.

Public surface
--------------
- :class:`ChemistryProblem` — typed payload for ``Manifest.problem``.
- :func:`load_instance` — load one of the bundled YAML reference manifests.
- :class:`ChemistrySimulation` — ``qcompass_core.Simulation`` implementation.
- :class:`ChemistryResult`, :class:`ChemistryInstance` — result envelopes.
- :func:`compute_reference` — direct access to the classical path
  (rarely needed; use :class:`ChemistrySimulation` for the full
  envelope).

This package MUST NOT import from ``ucgle_f1`` or any other
``qfull_*`` sibling. CI enforces with both a grep guard and
``tests/test_boundary.py``.
"""

from __future__ import annotations

from .classical import ClassicalOutcome, compute_reference
from .manifest import (
    MOLECULE_REGISTRY,
    BackendPreference,
    ChemistryProblem,
    MoleculeDefaults,
    MoleculeName,
    ReferenceMethod,
    load_instance,
)
from .quantum_dice import DiceOutcome, is_dice_available, run_dice
from .quantum_sqd import SQDOutcome, run_sqd
from .sim import (
    ChemistryInstance,
    ChemistryResult,
    ChemistrySimulation,
    PathTaken,
)

__version__ = "0.1.0"

__all__ = [
    "BackendPreference",
    "ChemistryInstance",
    "ChemistryProblem",
    "ChemistryResult",
    "ChemistrySimulation",
    "ClassicalOutcome",
    "DiceOutcome",
    "MOLECULE_REGISTRY",
    "MoleculeDefaults",
    "MoleculeName",
    "PathTaken",
    "ReferenceMethod",
    "SQDOutcome",
    "compute_reference",
    "is_dice_available",
    "load_instance",
    "run_dice",
    "run_sqd",
]
