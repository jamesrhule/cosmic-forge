"""M11 — Hamiltonian registry.

Read/validate the canonical input formats QCompass plugins consume:

- **FCIDUMP** (electronic-structure two-electron integrals).
- **Spin-Hamiltonian JSON** (lattice / model Hamiltonians).
- **LQCD-HDF5** (lattice-QCD operator dump; PROMPT 0 v2 stub).

The reader validates structure and returns Pydantic models that
plugins consume. HDF5 writers are exposed as stubs; the actual
serialisation lands when the first plugin needs it.
"""

from __future__ import annotations

from .fcidump import FCIDUMP, read_fcidump, write_fcidump_stub
from .lqcd_hdf5 import LQCDHDF5Schema, read_lqcd_hdf5
from .spin_json import SpinHamiltonian, validate_spin_hamiltonian

__all__ = [
    "FCIDUMP",
    "LQCDHDF5Schema",
    "SpinHamiltonian",
    "read_fcidump",
    "read_lqcd_hdf5",
    "validate_spin_hamiltonian",
    "write_fcidump_stub",
]
