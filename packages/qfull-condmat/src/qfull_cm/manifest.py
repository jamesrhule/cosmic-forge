"""CondMat domain manifest.

Wraps the four condensed-matter problem classes the plugin
recognises today:

- ``hubbard``       — Hubbard model, free-form lattice + (U, t)
- ``heisenberg``    — XXZ Heisenberg chain (L, J, Jz)
- ``frustrated``    — frustrated-spin model (J1-J2 chain or
                      triangular lattice)
- ``otoc``          — Loschmidt-echo OTOC schedule on a
                      Heisenberg-class Hamiltonian
"""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


ProblemKind = Literal["hubbard", "heisenberg", "frustrated", "otoc"]
LatticeName = Literal["chain", "ladder", "square", "triangular"]
BackendPreference = Literal["classical", "ibm", "analog", "auto"]


class HubbardParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    L: tuple[int, int]              # (Lx, Ly); chain when Ly == 1
    U: float = 4.0
    t: float = 1.0
    n_electrons: int | None = None  # None → half-filling


class HeisenbergParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    L: int = Field(ge=2)
    J: float = 1.0
    Jz: float = 1.0                 # Jz / J anisotropy
    boundary: Literal["open", "periodic"] = "open"


class FrustratedParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    L: int = Field(ge=4)
    J1: float = 1.0
    J2: float = 0.5
    lattice: Literal["chain", "triangular"] = "chain"


class OtocParams(BaseModel):
    """Loschmidt-echo OTOC parameters."""

    model_config = ConfigDict(extra="forbid")
    L: int = Field(ge=4, description="Number of sites / qubits.")
    n_steps: int = Field(default=20, ge=1)
    dt: float = Field(default=0.1, gt=0.0)
    operator_site: int = Field(default=0, ge=0)


class CondMatProblem(BaseModel):
    """Typed payload for ``Manifest.problem`` when ``domain='condmat'``."""

    model_config = ConfigDict(extra="forbid")

    kind: ProblemKind
    backend_preference: BackendPreference = "auto"
    shots: int = Field(default=1024, ge=1)
    seed: int = 0
    hubbard: HubbardParams | None = None
    heisenberg: HeisenbergParams | None = None
    frustrated: FrustratedParams | None = None
    otoc: OtocParams | None = None

    @model_validator(mode="after")
    def _kind_matches_payload(self) -> "CondMatProblem":
        attr = self.kind
        present = getattr(self, attr)
        if present is None:
            msg = f"kind={self.kind!r} requires the matching '{attr}' payload."
            raise ValueError(msg)
        return self

    def canonical_payload(self) -> dict[str, Any]:
        block = getattr(self, self.kind)
        return {
            "kind": self.kind,
            "params": block.model_dump() if block else None,
        }


def load_instance(name: str) -> CondMatProblem:
    """Load a bundled YAML instance or arbitrary path."""
    candidate = Path(name)
    if candidate.is_file():
        text = candidate.read_text()
    else:
        try:
            text = (
                resources.files("qfull_cm.instances")
                .joinpath(f"{name.lower()}.yaml")
                .read_text()
            )
        except (FileNotFoundError, ModuleNotFoundError) as exc:
            msg = (
                f"Unknown instance {name!r}. Pass a YAML path or one of "
                "hubbard_4x4 / heisenberg_chain_10 / otoc_chain_8."
            )
            raise FileNotFoundError(msg) from exc
    payload = yaml.safe_load(text)
    return CondMatProblem.model_validate(payload)
