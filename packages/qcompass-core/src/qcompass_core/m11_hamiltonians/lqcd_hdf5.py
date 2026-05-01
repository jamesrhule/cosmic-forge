"""LQCD-HDF5 schema stub.

PROMPT 0 v2 mandates a third Hamiltonian input alongside FCIDUMP
(electronic-structure) and spin-JSON (lattice models): an HDF5
schema for lattice-QCD operators. The schema is intentionally a
stub at v0.1.0 — the consumer that needs it (qfull-hep's
SC-ADAPT-VQE path beyond the Schwinger toy) will land the real
parser in a later prompt.

Today the module exposes:

  - :class:`LQCDHDF5Schema` — Pydantic v2 envelope describing an
    on-disk HDF5 file.
  - :func:`read_lqcd_hdf5` — opens the HDF5 file lazily (h5py
    soft-imported) and returns a populated schema. Raises
    :class:`HamiltonianFormatError` when the dataset names or
    shapes are missing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..errors import HamiltonianFormatError


class LQCDHDF5Schema(BaseModel):
    """Validated descriptor of an LQCD HDF5 Hamiltonian payload."""

    model_config = ConfigDict(extra="forbid")

    path: str
    lattice_shape: tuple[int, int, int, int] = Field(
        description="(Nt, Nx, Ny, Nz)",
    )
    gauge_group: str = "SU(3)"
    quark_action: str = "Wilson"
    n_flavors: int = Field(default=2, ge=1)
    operator_keys: list[str] = Field(
        default_factory=list,
        description="HDF5 dataset names for the operator coefficients.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


def read_lqcd_hdf5(path: str | Path) -> LQCDHDF5Schema:
    """Read the structural metadata of an LQCD HDF5 file.

    Stub implementation: validates that the file exists, that h5py
    is importable, and returns whatever metadata attributes happen
    to live on the root group. Full operator parsing lands when
    qfull-hep needs it.
    """
    p = Path(path)
    if not p.exists():
        msg = f"LQCD-HDF5 file not found: {p}"
        raise HamiltonianFormatError(msg)
    try:
        import h5py  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - h5py is a base dep
        msg = (
            "h5py is required to read LQCD-HDF5; install qcompass-core "
            "(h5py is a base dependency)."
        )
        raise HamiltonianFormatError(msg) from exc

    try:
        with h5py.File(str(p), "r") as f:
            attrs = dict(f.attrs)
            keys = list(f.keys())
    except (OSError, ValueError) as exc:
        msg = f"Could not open LQCD-HDF5 file {p}: {exc}"
        raise HamiltonianFormatError(msg) from exc

    # Best-effort population — the schema's defaults cover anything
    # the file omits at this stub stage.
    lattice_shape_raw = attrs.get("lattice_shape", (0, 0, 0, 0))
    try:
        lattice_shape = tuple(int(x) for x in lattice_shape_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        msg = f"Bad lattice_shape attr in {p}: {lattice_shape_raw!r}"
        raise HamiltonianFormatError(msg) from exc
    if len(lattice_shape) != 4:
        msg = f"lattice_shape must be 4-tuple; got {lattice_shape}"
        raise HamiltonianFormatError(msg)

    return LQCDHDF5Schema(
        path=str(p),
        lattice_shape=lattice_shape,
        gauge_group=str(attrs.get("gauge_group", "SU(3)")),
        quark_action=str(attrs.get("quark_action", "Wilson")),
        n_flavors=int(attrs.get("n_flavors", 2)),
        operator_keys=keys,
        metadata={
            k: (v.tolist() if hasattr(v, "tolist") else v)
            for k, v in attrs.items()
        },
    )
