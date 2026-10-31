"""NuclearShellHamiltonian schema (PROMPT 5 v2 §M11 extension).

Few-body / no-core shell-model Hamiltonian descriptor. Carries the
single-particle basis size, the path to the on-disk two-body matrix
elements, the valence space (model-space label), and (A, Z). The
qfull-nuclear plugin's classical kernel consumes the validated
model; production NCSM runs feed an HDF5 dump rather than inline
matrix elements.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..errors import HamiltonianFormatError


class NuclearShellHamiltonian(BaseModel):
    """Validated nuclear-shell-model Hamiltonian descriptor."""

    model_config = ConfigDict(extra="forbid")

    n_single_particle: int = Field(
        ge=2,
        description="Single-particle basis dimension (≥ 2).",
    )
    valence_space: str = Field(
        description="Model-space label, e.g. 'p-shell', 'sd-shell'.",
    )
    A: int = Field(
        ge=1, description="Mass number (total nucleons).",
    )
    Z: int = Field(
        ge=0, description="Atomic number (proton count).",
    )
    two_body_matrix_path: str | None = Field(
        default=None,
        description=(
            "Relative path to an HDF5 / TBME file. None for "
            "synthetic / inline matrix elements used by the audit."
        ),
    )
    two_body_inline: list[list[float]] | None = Field(
        default=None,
        description="Optional inline matrix (square; small instances).",
    )
    operator_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _Z_le_A(self) -> "NuclearShellHamiltonian":
        if self.Z > self.A:
            msg = f"Z={self.Z} cannot exceed A={self.A}."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _path_xor_inline(self) -> "NuclearShellHamiltonian":
        if (self.two_body_matrix_path is not None
                and self.two_body_inline is not None):
            msg = (
                "Set either two_body_matrix_path or two_body_inline, "
                "not both."
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _inline_square(self) -> "NuclearShellHamiltonian":
        if self.two_body_inline is None:
            return self
        n = len(self.two_body_inline)
        for row in self.two_body_inline:
            if len(row) != n:
                msg = (
                    "two_body_inline must be square; got rows of "
                    f"varying length (n={n})."
                )
                raise ValueError(msg)
        return self


def read_nuclear_shell_hdf5(path: str | Path) -> NuclearShellHamiltonian:
    """Read a NuclearShellHamiltonian descriptor from HDF5.

    Mirrors :func:`read_lqcd_hdf5`. Required attrs: ``A``, ``Z``,
    ``valence_space``, ``n_single_particle``. ``operator_keys`` is
    populated from the file's group keys.
    """
    p = Path(path)
    if not p.exists():
        msg = f"NuclearShell HDF5 file not found: {p}"
        raise HamiltonianFormatError(msg)
    try:
        import h5py  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - h5py base dep
        msg = "h5py is required to read nuclear-shell HDF5."
        raise HamiltonianFormatError(msg) from exc

    try:
        with h5py.File(str(p), "r") as f:
            attrs = dict(f.attrs)
            keys = list(f.keys())
    except (OSError, ValueError) as exc:
        msg = f"Could not open nuclear-shell HDF5 file {p}: {exc}"
        raise HamiltonianFormatError(msg) from exc

    for required in ("A", "Z", "valence_space", "n_single_particle"):
        if required not in attrs:
            msg = f"missing required attr {required!r} in {p}"
            raise HamiltonianFormatError(msg)

    return NuclearShellHamiltonian(
        n_single_particle=int(attrs["n_single_particle"]),
        valence_space=str(attrs["valence_space"]),
        A=int(attrs["A"]),
        Z=int(attrs["Z"]),
        two_body_matrix_path=str(p),
        operator_keys=keys,
        metadata={
            k: (v.tolist() if hasattr(v, "tolist") else v)
            for k, v in attrs.items()
        },
    )


def write_nuclear_shell_hdf5_stub(
    model: NuclearShellHamiltonian, path: str | Path,
) -> None:
    """Write the descriptor to an HDF5 file (attrs-only stub)."""
    try:
        import h5py  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - h5py base dep
        msg = "h5py is required to write nuclear-shell HDF5."
        raise HamiltonianFormatError(msg) from exc

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(str(p), "w") as f:
        f.attrs["A"] = model.A
        f.attrs["Z"] = model.Z
        f.attrs["valence_space"] = model.valence_space
        f.attrs["n_single_particle"] = model.n_single_particle
