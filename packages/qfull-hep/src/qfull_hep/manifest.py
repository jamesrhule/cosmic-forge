"""HEP domain manifest."""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


ProblemKind = Literal["schwinger", "zN", "su2_toy"]
BackendPreference = Literal["classical", "ibm", "ionq", "scadapt_vqe", "auto"]


class SchwingerParams(BaseModel):
    """Schwinger 1+1D parameters (Kogut-Susskind staggered fermions)."""

    model_config = ConfigDict(extra="forbid")
    L: int = Field(ge=2, le=20)
    m: float = Field(default=0.0, description="Bare fermion mass.")
    g: float = Field(default=1.0, description="Gauge coupling.")
    theta: float = Field(default=0.0, description="θ-angle.")


class ZNParams(BaseModel):
    """Z_N lattice gauge structural payload (no kernel yet)."""

    model_config = ConfigDict(extra="forbid")
    N: int = Field(ge=2)
    Lx: int = Field(ge=2)
    Ly: int = Field(ge=2)


class SU2Params(BaseModel):
    """Toy SU(2) lattice gauge structural payload."""

    model_config = ConfigDict(extra="forbid")
    L: int = Field(ge=2)
    g: float = Field(default=1.0)


class HEPProblem(BaseModel):
    """``Manifest.problem`` payload for ``domain='hep'``."""

    model_config = ConfigDict(extra="forbid")

    kind: ProblemKind
    backend_preference: BackendPreference = "auto"
    shots: int = Field(default=1024, ge=1)
    seed: int = 0
    schwinger: SchwingerParams | None = None
    zN: ZNParams | None = None
    su2_toy: SU2Params | None = None

    @model_validator(mode="after")
    def _kind_matches_payload(self) -> "HEPProblem":
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


def load_instance(name: str) -> HEPProblem:
    candidate = Path(name)
    if candidate.is_file():
        text = candidate.read_text()
    else:
        try:
            text = (
                resources.files("qfull_hep.instances")
                .joinpath(f"{name.lower()}.yaml")
                .read_text()
            )
        except (FileNotFoundError, ModuleNotFoundError) as exc:
            msg = (
                f"Unknown instance {name!r}. Pass a YAML path or one of "
                "schwinger_l4 / schwinger_l6 / schwinger_l10."
            )
            raise FileNotFoundError(msg) from exc
    payload = yaml.safe_load(text)
    return HEPProblem.model_validate(payload)
