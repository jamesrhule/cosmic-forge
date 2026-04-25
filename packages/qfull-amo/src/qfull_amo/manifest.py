"""AMO domain manifest."""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


ProblemKind = Literal["rydberg_ground_state", "mis_toy"]
BackendPreference = Literal["classical", "bloqade", "bloqade_analog", "pulser", "auto"]


class RydbergParams(BaseModel):
    """Rydberg-array parameters."""

    model_config = ConfigDict(extra="forbid")
    L: int = Field(ge=2, le=14, description="Number of atoms.")
    blockade_radius: float = Field(default=1.0, gt=0.0)
    detuning: float = Field(default=0.0)
    rabi: float = Field(default=1.0, gt=0.0)
    geometry: Literal["chain", "ring"] = "chain"


class MISParams(BaseModel):
    """MIS toy problem on a small graph (encoded as adjacency list)."""

    model_config = ConfigDict(extra="forbid")
    n_nodes: int = Field(ge=2, le=12)
    edges: list[tuple[int, int]] = Field(default_factory=list)


class AMOProblem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ProblemKind
    backend_preference: BackendPreference = "auto"
    shots: int = Field(default=1024, ge=1)
    seed: int = 0
    rydberg_ground_state: RydbergParams | None = None
    mis_toy: MISParams | None = None

    @model_validator(mode="after")
    def _kind_matches_payload(self) -> "AMOProblem":
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


def load_instance(name: str) -> AMOProblem:
    candidate = Path(name)
    if candidate.is_file():
        text = candidate.read_text()
    else:
        try:
            text = (
                resources.files("qfull_amo.instances")
                .joinpath(f"{name.lower()}.yaml")
                .read_text()
            )
        except (FileNotFoundError, ModuleNotFoundError) as exc:
            msg = (
                f"Unknown instance {name!r}. Pass a YAML path or one of "
                "rydberg_chain_8 / rydberg_ring_6 / mis_path_5."
            )
            raise FileNotFoundError(msg) from exc
    payload = yaml.safe_load(text)
    return AMOProblem.model_validate(payload)
