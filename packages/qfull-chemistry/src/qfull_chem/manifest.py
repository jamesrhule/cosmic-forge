"""Chemistry domain manifest.

The :class:`ChemistryProblem` model is the typed payload that goes
inside ``qcompass_core.Manifest.problem`` for the ``chemistry``
domain. It carries enough state to drive the classical reference,
SQD, and Dice paths without inventing physics fields outside the
chemistry vocabulary.

Four reference instances ship under ``instances/*.yaml``; load them
with :func:`load_instance`.
"""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Canonical molecules registered with built-in defaults.
MoleculeName = Literal["H2", "LiH", "N2", "FeMoco_toy"]

ReferenceMethod = Literal["FCI", "DMRG", "CCSD(T)"]
BackendPreference = Literal["classical", "sqd", "dice", "auto"]


class MoleculeDefaults(BaseModel):
    """Built-in default geometry/basis/reference for the four canonical molecules."""

    model_config = ConfigDict(extra="forbid")

    geometry: str
    basis: str
    reference: ReferenceMethod
    active_space: tuple[int, int] | None = None
    notes: str = ""


# Geometry strings are PySCF-format. Bond lengths are equilibrium
# values from standard sources (NIST CCCBDB / Reiher 2017).
MOLECULE_REGISTRY: dict[str, MoleculeDefaults] = {
    "H2": MoleculeDefaults(
        geometry="H 0 0 0; H 0 0 0.74",
        basis="sto-3g",
        reference="FCI",
        active_space=(2, 2),
    ),
    "LiH": MoleculeDefaults(
        geometry="Li 0 0 0; H 0 0 1.595",
        basis="6-31g",
        reference="DMRG",
        active_space=(4, 11),
    ),
    "N2": MoleculeDefaults(
        geometry="N 0 0 0; N 0 0 1.0975",
        basis="cc-pvdz",
        reference="CCSD(T)",
        active_space=None,
    ),
    "FeMoco_toy": MoleculeDefaults(
        geometry="",
        basis="reiher2017_active_space",
        reference="DMRG",
        active_space=(54, 54),
        notes=(
            "Reiher-2017 FeMoco toy active space. Geometry is irrelevant; "
            "the integrals are loaded from an FCIDUMP via fcidump_path."
        ),
    ),
}


class ChemistryProblem(BaseModel):
    """Typed payload for ``Manifest.problem`` when ``domain='chemistry'``."""

    model_config = ConfigDict(extra="forbid")

    molecule: str = Field(
        description=(
            "Either a registered name (H2, LiH, N2, FeMoco_toy) or a "
            "free-form label paired with an explicit ``geometry``."
        )
    )
    basis: str | None = Field(
        default=None,
        description="Basis set; falls back to MOLECULE_REGISTRY default when None.",
    )
    active_space: tuple[int, int] | None = Field(
        default=None,
        description="(n_electrons, n_orbitals) — None to skip active-space restriction.",
    )
    backend_preference: BackendPreference = "auto"
    reference: ReferenceMethod | None = Field(
        default=None,
        description="Classical reference method; falls back to the registered default.",
    )
    shots: int = Field(default=10_000, ge=1)
    seed: int = 0
    geometry: str | None = Field(
        default=None,
        description="PySCF atom string. Required for non-registered molecules.",
    )
    fcidump_path: Path | None = Field(
        default=None,
        description="Path to an FCIDUMP file (used by FeMoco_toy).",
    )
    charge: int = 0
    spin: int = Field(default=0, description="2 * S_z (signed).")

    @model_validator(mode="after")
    def _resolve_defaults(self) -> "ChemistryProblem":
        defaults = MOLECULE_REGISTRY.get(self.molecule)
        if defaults is not None:
            if self.basis is None:
                object.__setattr__(self, "basis", defaults.basis)
            if self.active_space is None:
                object.__setattr__(self, "active_space", defaults.active_space)
            if self.reference is None:
                object.__setattr__(self, "reference", defaults.reference)
            if self.geometry is None:
                object.__setattr__(self, "geometry", defaults.geometry)
        # Required-field guards for non-registered molecules.
        if defaults is None:
            if self.basis is None:
                msg = (
                    f"basis is required when molecule={self.molecule!r} is "
                    "not in MOLECULE_REGISTRY"
                )
                raise ValueError(msg)
            if self.geometry is None and self.fcidump_path is None:
                msg = (
                    f"geometry or fcidump_path is required for "
                    f"molecule={self.molecule!r}"
                )
                raise ValueError(msg)
        if self.reference is None:
            object.__setattr__(self, "reference", "FCI")
        if self.molecule == "FeMoco_toy" and self.fcidump_path is None:
            # We don't *require* a path during planning, but the
            # classical path will refuse to run without one. Surface
            # a clear info message rather than crashing later.
            pass
        return self

    def canonical_problem_payload(self) -> dict[str, Any]:
        """Stable dict used as the input to ``hash_payload``.

        Sorted keys, no Path objects (cast to strings), no numpy types.
        """
        payload: dict[str, Any] = {
            "molecule": self.molecule,
            "basis": self.basis,
            "active_space": list(self.active_space) if self.active_space else None,
            "reference": self.reference,
            "geometry": self.geometry,
            "fcidump_path": str(self.fcidump_path) if self.fcidump_path else None,
            "charge": self.charge,
            "spin": self.spin,
        }
        return payload


def load_instance(name: str) -> ChemistryProblem:
    """Load one of the bundled YAML instances.

    ``name`` is either a logical key (``"h2"``, ``"lih"``, ``"n2"``,
    ``"femoco_toy"``) or a path to a custom YAML file with the same
    schema.
    """
    candidate = Path(name)
    if candidate.is_file():
        text = candidate.read_text()
    else:
        try:
            text = (
                resources.files("qfull_chem.instances")
                .joinpath(f"{name.lower()}.yaml")
                .read_text()
            )
        except (FileNotFoundError, ModuleNotFoundError) as exc:
            msg = (
                f"Unknown instance {name!r}. Pass a YAML path or one of "
                "h2 / lih / n2 / femoco_toy."
            )
            raise FileNotFoundError(msg) from exc
    payload = yaml.safe_load(text)
    return ChemistryProblem.model_validate(payload)
