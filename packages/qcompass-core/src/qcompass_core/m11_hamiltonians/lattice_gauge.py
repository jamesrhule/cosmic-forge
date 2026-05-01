"""LatticeGaugeHamiltonian schema (PROMPT 5 v2 §M11 extension).

Domain-agnostic envelope for lattice-gauge problem instances —
Schwinger 1+1D, Z_N, toy SU(2) plaquette evolution all parse into
this. Plugins (qfull-hep) consume the validated model.

Round-trips with HDF5 via :func:`read_lattice_gauge_hdf5` /
:func:`write_lattice_gauge_hdf5_stub`. The HDF5 form mirrors the
existing :mod:`lqcd_hdf5` pattern: lazy ``h5py`` import, root-group
attributes, optional dataset ``operator_keys``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..errors import HamiltonianFormatError


GaugeGroup = Literal["U(1)", "Z_N", "SU(2)", "SU(3)"]
FermionEncoding = Literal[
    "kogut_susskind",
    "wilson",
    "staggered",
    "domain_wall",
    "none",
]


class LatticeGaugeHamiltonian(BaseModel):
    """Validated lattice-gauge problem instance.

    Carries the structural metadata the qfull-hep plugin's classical
    kernel + audit need: gauge group, lattice geometry, fermion
    encoding, mass + θ-angle. The ``operator_keys`` list records
    HDF5 dataset names when the instance was deserialised from disk.
    """

    model_config = ConfigDict(extra="forbid")

    gauge_group: GaugeGroup
    dimension: int = Field(ge=1, le=4, description="Spatial dim (1, 2, 3, 4).")
    lattice_shape: tuple[int, ...] = Field(
        description="Per-axis site count; len matches ``dimension`` + time.",
    )
    fermion_encoding: FermionEncoding = "none"
    mass: float = Field(default=0.0, description="Bare fermion mass.")
    coupling: float = Field(default=1.0, description="Gauge coupling g.")
    theta: float | None = Field(
        default=None,
        description="θ-angle (None when gauge_group has no topological term).",
    )
    n_flavors: int = Field(default=1, ge=1)
    operator_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _shape_matches_dimension(self) -> "LatticeGaugeHamiltonian":
        # Spatial axes + 1 time axis OR pure-spatial (dimension only).
        spatial = self.dimension
        if len(self.lattice_shape) not in (spatial, spatial + 1):
            msg = (
                f"lattice_shape {self.lattice_shape} length must equal "
                f"dimension={spatial} or dimension+1 (time-extended)."
            )
            raise ValueError(msg)
        if any(n < 2 for n in self.lattice_shape):
            msg = f"lattice_shape entries must all be ≥ 2; got {self.lattice_shape}"
            raise ValueError(msg)
        return self


def read_lattice_gauge_hdf5(path: str | Path) -> LatticeGaugeHamiltonian:
    """Read structural metadata from an HDF5 file into a model.

    Mirrors :func:`read_lqcd_hdf5`: lazy ``h5py`` import, root-group
    attributes, dataset names → ``operator_keys``.
    """
    p = Path(path)
    if not p.exists():
        msg = f"LatticeGauge HDF5 file not found: {p}"
        raise HamiltonianFormatError(msg)
    try:
        import h5py  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - h5py is a base dep
        msg = "h5py is required to read lattice-gauge HDF5."
        raise HamiltonianFormatError(msg) from exc

    try:
        with h5py.File(str(p), "r") as f:
            attrs = dict(f.attrs)
            keys = list(f.keys())
    except (OSError, ValueError) as exc:
        msg = f"Could not open lattice-gauge HDF5 file {p}: {exc}"
        raise HamiltonianFormatError(msg) from exc

    shape_raw = attrs.get("lattice_shape")
    if shape_raw is None:
        msg = f"missing required attr 'lattice_shape' in {p}"
        raise HamiltonianFormatError(msg)
    try:
        lattice_shape = tuple(int(x) for x in shape_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        msg = f"bad lattice_shape attr in {p}: {shape_raw!r}"
        raise HamiltonianFormatError(msg) from exc

    return LatticeGaugeHamiltonian(
        gauge_group=str(attrs.get("gauge_group", "U(1)")),  # type: ignore[arg-type]
        dimension=int(attrs.get("dimension", 1)),
        lattice_shape=lattice_shape,
        fermion_encoding=str(attrs.get("fermion_encoding", "none")),  # type: ignore[arg-type]
        mass=float(attrs.get("mass", 0.0)),
        coupling=float(attrs.get("coupling", 1.0)),
        theta=(
            None if attrs.get("theta") is None
            else float(attrs.get("theta"))  # type: ignore[arg-type]
        ),
        n_flavors=int(attrs.get("n_flavors", 1)),
        operator_keys=keys,
        metadata={
            k: (v.tolist() if hasattr(v, "tolist") else v)
            for k, v in attrs.items()
        },
    )


def write_lattice_gauge_hdf5_stub(
    model: LatticeGaugeHamiltonian, path: str | Path,
) -> None:
    """Write the model's metadata to an HDF5 file (no operator data).

    Mirrors :func:`write_fcidump_stub`'s contract: writes only the
    schema attributes so consumers can round-trip the descriptor.
    """
    try:
        import h5py  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - h5py base dep
        msg = "h5py is required to write lattice-gauge HDF5."
        raise HamiltonianFormatError(msg) from exc

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(str(p), "w") as f:
        f.attrs["gauge_group"] = model.gauge_group
        f.attrs["dimension"] = model.dimension
        f.attrs["lattice_shape"] = list(model.lattice_shape)
        f.attrs["fermion_encoding"] = model.fermion_encoding
        f.attrs["mass"] = model.mass
        f.attrs["coupling"] = model.coupling
        if model.theta is not None:
            f.attrs["theta"] = model.theta
        f.attrs["n_flavors"] = model.n_flavors
