"""Statmech domain manifest."""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


ProblemKind = Literal["qae", "metropolis_ising", "tfd"]
BackendPreference = Literal["classical", "ibm", "ionq", "auto"]


class QAEParams(BaseModel):
    """Quantum amplitude estimation against a known integrand."""

    model_config = ConfigDict(extra="forbid")
    integrand: Literal["bell", "gaussian", "indicator"] = "bell"
    n_samples: int = Field(default=4096, ge=128)
    truth: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Closed-form expectation the estimator targets.",
    )


class IsingMetropolisParams(BaseModel):
    """Quantum Metropolis on a transverse-field Ising chain."""

    model_config = ConfigDict(extra="forbid")
    L: int = Field(ge=2, le=12, description="Chain length.")
    J: float = Field(default=1.0)
    h: float = Field(default=0.5, description="Transverse field strength.")
    beta: float = Field(default=1.0, gt=0.0)


class TFDParams(BaseModel):
    """Thermofield-double preparation parameters."""

    model_config = ConfigDict(extra="forbid")
    L: int = Field(ge=2, le=10)
    beta: float = Field(default=1.0, gt=0.0)
    J: float = Field(default=1.0)


class StatmechProblem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ProblemKind
    backend_preference: BackendPreference = "auto"
    shots: int = Field(default=1024, ge=1)
    seed: int = 0
    qae: QAEParams | None = None
    metropolis_ising: IsingMetropolisParams | None = None
    tfd: TFDParams | None = None

    @model_validator(mode="after")
    def _kind_matches_payload(self) -> "StatmechProblem":
        attr = self.kind
        present = getattr(self, attr)
        if present is None:
            msg = f"kind={self.kind!r} requires the matching '{attr}' payload."
            raise ValueError(msg)
        return self

    def canonical_payload(self) -> dict[str, Any]:
        block = getattr(self, self.kind)
        return {"kind": self.kind, "params": block.model_dump() if block else None}


def load_instance(name: str) -> StatmechProblem:
    candidate = Path(name)
    if candidate.is_file():
        text = candidate.read_text()
    else:
        try:
            text = (
                resources.files("qfull_stat.instances")
                .joinpath(f"{name.lower()}.yaml")
                .read_text()
            )
        except (FileNotFoundError, ModuleNotFoundError) as exc:
            msg = (
                f"Unknown instance {name!r}. Pass a YAML path or one of "
                "qae_bell / metropolis_ising_l6 / tfd_l4."
            )
            raise FileNotFoundError(msg) from exc
    payload = yaml.safe_load(text)
    return StatmechProblem.model_validate(payload)
