"""M11 — Hamiltonian registry.

Read/validate the canonical input formats QCompass plugins consume:

- **FCIDUMP** (electronic-structure two-electron integrals).
- **Spin-Hamiltonian JSON** (lattice / model Hamiltonians).
- **LQCD-HDF5** (lattice-QCD operator dump; PROMPT 0 v2 stub).
- **LatticeGaugeHamiltonian** (Schwinger / Z_N / SU(2) toy;
  PROMPT 5 v2 §M11 extension).
- **NuclearShellHamiltonian** (NCSM / few-body shell-model
  descriptor; PROMPT 5 v2 §M11 extension).

The reader validates structure and returns Pydantic models that
plugins consume. HDF5 writers are exposed as stubs; the actual
serialisation lands when the first plugin needs it.
"""

from __future__ import annotations

from .fcidump import FCIDUMP, read_fcidump, write_fcidump_stub
from .lattice_gauge import (
    LatticeGaugeHamiltonian,
    read_lattice_gauge_hdf5,
    write_lattice_gauge_hdf5_stub,
)
from .lqcd_hdf5 import LQCDHDF5Schema, read_lqcd_hdf5
from .nuclear_shell import (
    NuclearShellHamiltonian,
    read_nuclear_shell_hdf5,
    write_nuclear_shell_hdf5_stub,
)
from .spin_json import SpinHamiltonian, validate_spin_hamiltonian

__all__ = [
    "FCIDUMP",
    "LQCDHDF5Schema",
    "LatticeGaugeHamiltonian",
    "NuclearShellHamiltonian",
    "SpinHamiltonian",
    "read_fcidump",
    "read_lattice_gauge_hdf5",
    "read_lqcd_hdf5",
    "read_nuclear_shell_hdf5",
    "validate_spin_hamiltonian",
    "write_fcidump_stub",
    "write_lattice_gauge_hdf5_stub",
    "write_nuclear_shell_hdf5_stub",
]
