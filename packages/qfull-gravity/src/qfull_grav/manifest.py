"""Gravity domain manifest (PROMPT 9 v2 §A).

PROVENANCE (non-negotiable):
- ``is_learned_hamiltonian: bool`` — set True when the operator
  used by the kernel was fit / inferred (rather than derived from
  first principles).
- ``provenance_warning: str | None`` — REQUIRED whenever
  ``is_learned_hamiltonian=True``. The frontend visualizer
  surfaces this string prominently and audit S-grav-1 BLOCKS the
  merge if it's missing on a learned manifest (Jafferis-style guard).
- ``model_domain: Literal[...]`` — pinned caveat tag the visualizer
  uses for the per-frame banner.
"""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


ProblemKind = Literal["syk_dense", "syk_sparse", "jt_matrix"]
BackendPreference = Literal["classical", "ibm", "ionq", "auto"]
ModelDomain = Literal["toy_SYK_1+1D", "JT_matrix_model", "SYK_sparse"]


_KIND_TO_MODEL_DOMAIN: dict[str, ModelDomain] = {
    "syk_dense": "toy_SYK_1+1D",
    "syk_sparse": "SYK_sparse",
    "jt_matrix": "JT_matrix_model",
}


def model_domain_for_kind(kind: str) -> ModelDomain:
    """Return the canonical ``model_domain`` tag for a problem kind."""
    try:
        return _KIND_TO_MODEL_DOMAIN[kind]
    except KeyError as exc:
        msg = f"unknown gravity problem kind: {kind!r}"
        raise ValueError(msg) from exc


class SYKParams(BaseModel):
    """Sachdev-Ye-Kitaev model parameters (Majorana, q=4 random couplings)."""

    model_config = ConfigDict(extra="forbid")
    N: int = Field(ge=4, le=14, description="Number of Majorana fermions.")
    q: int = Field(default=4, ge=2, le=8)
    J: float = Field(default=1.0, gt=0.0, description="Coupling scale.")
    seed: int = Field(default=0)


class SparseSYKParams(BaseModel):
    """Sparsified SYK (Xu-Susskind 2020) — keeps O(N) random couplings."""

    model_config = ConfigDict(extra="forbid")
    N: int = Field(ge=4, le=20)
    q: int = Field(default=4, ge=2, le=8)
    sparsity: float = Field(
        default=0.3, gt=0.0, le=1.0,
        description="Fraction of dense-SYK couplings retained.",
    )
    seed: int = Field(default=0)


class JTParams(BaseModel):
    """Jackiw-Teitelboim gravity matrix-model parameters."""

    model_config = ConfigDict(extra="forbid")
    matrix_size: int = Field(ge=4, le=64, description="N for the random matrix.")
    ensemble: Literal["GUE", "GOE", "GSE"] = "GUE"
    seed: int = Field(default=0)


class GravityProblem(BaseModel):
    """``Manifest.problem`` payload for ``domain='gravity'``."""

    model_config = ConfigDict(extra="forbid")

    kind: ProblemKind
    backend_preference: BackendPreference = "auto"
    shots: int = Field(default=1024, ge=1)
    seed: int = 0

    # PROMPT 9 v2 §A non-negotiable provenance fields.
    is_learned_hamiltonian: bool = Field(
        default=False,
        description=(
            "True when the operator was fit / inferred. Forces "
            "provenance_warning to be non-empty (audit S-grav-1)."
        ),
    )
    provenance_warning: str | None = Field(
        default=None,
        description=(
            "REQUIRED when is_learned_hamiltonian=True. Surfaced "
            "prominently by the frontend visualiser."
        ),
    )

    syk_dense: SYKParams | None = None
    syk_sparse: SparseSYKParams | None = None
    jt_matrix: JTParams | None = None

    @model_validator(mode="after")
    def _kind_matches_payload(self) -> "GravityProblem":
        attr = self.kind
        present = getattr(self, attr)
        if present is None:
            msg = f"kind={self.kind!r} requires the matching '{attr}' payload."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _learned_hamiltonian_requires_warning(self) -> "GravityProblem":
        # Jafferis-style guard: the manifest itself enforces that
        # learned-Hamiltonian runs ship a warning string. Audit
        # S-grav-1 verifies this guard is present in the schema.
        if self.is_learned_hamiltonian and not (
            self.provenance_warning and self.provenance_warning.strip()
        ):
            msg = (
                "GravityProblem with is_learned_hamiltonian=True MUST "
                "set provenance_warning to a non-empty string. The "
                "warning is surfaced verbatim by the visualiser; audit "
                "S-grav-1 BLOCKS merges when this guard fires."
            )
            raise ValueError(msg)
        return self

    @property
    def model_domain(self) -> ModelDomain:
        return model_domain_for_kind(self.kind)

    def canonical_payload(self) -> dict[str, Any]:
        block = getattr(self, self.kind)
        return {
            "kind": self.kind,
            "is_learned_hamiltonian": self.is_learned_hamiltonian,
            "provenance_warning": self.provenance_warning,
            "params": block.model_dump() if block else None,
        }


def load_instance(name: str) -> GravityProblem:
    candidate = Path(name)
    if candidate.is_file():
        text = candidate.read_text()
    else:
        try:
            text = (
                resources.files("qfull_grav.instances")
                .joinpath(f"{name.lower()}.yaml")
                .read_text()
            )
        except (FileNotFoundError, ModuleNotFoundError) as exc:
            msg = (
                f"Unknown instance {name!r}. Pass a YAML path or one of "
                "syk_n8 / syk_sparse_n12 / jt_n16."
            )
            raise FileNotFoundError(msg) from exc
    payload = yaml.safe_load(text)
    return GravityProblem.model_validate(payload)
