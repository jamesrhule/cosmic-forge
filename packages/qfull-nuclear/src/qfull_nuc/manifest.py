"""Nuclear domain manifest."""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


ProblemKind = Literal[
    "zero_nu_bb_toy",
    "ncsm_matrix_element",
    "effective_hamiltonian",
]
BackendPreference = Literal["classical", "ibm", "ionq", "auto"]
ModelDomain = Literal["1+1D_toy", "few_body_3d", "effective_hamiltonian"]


# ── Hypothetical-particle search hook (PROMPT 5 v2) ──────────────────


HypotheticalSearch = Literal[
    "heavy_neutrino_mixing",
    "sterile_neutrino_oscillation",
]


class EffectiveHamiltonianParams(BaseModel):
    """Toy effective-Hamiltonian descriptor for hypothetical-particle searches.

    PROMPT 5 v2 mandates a scaffold (no fitted physics): the search
    name + a small set of phenomenological knobs the audit can pin
    deterministic ground-state energies against.

    For ``heavy_neutrino_mixing``: ``mixing_angle`` controls the
    off-diagonal coupling between the active and heavy state.
    For ``sterile_neutrino_oscillation``: ``mass_splitting`` and
    ``oscillation_frequency`` set the two-state oscillation.
    """

    model_config = ConfigDict(extra="forbid")
    search: HypotheticalSearch
    mixing_angle: float = Field(
        default=0.05,
        description="Effective off-diagonal coupling (radians).",
    )
    mass_splitting: float = Field(
        default=1.0,
        description="ΔM between active + hypothetical state.",
    )
    oscillation_frequency: float = Field(
        default=0.0,
        description=(
            "Time-averaging frequency for sterile-oscillation toys; "
            "0 = static effective Hamiltonian."
        ),
    )
    notes: str = ""


class ZeroNuBBToyParams(BaseModel):
    """1+1D 0νββ toy parameters (Chernyshev et al. 2026)."""

    model_config = ConfigDict(extra="forbid")
    L: int = Field(ge=2, le=8, description="Lattice sites (small for ED).")
    g_GT: float = Field(default=1.0, description="Gamow-Teller coupling.")
    g_F: float = Field(default=0.5, description="Fermi coupling.")
    notes: str = ""


class NCSMParams(BaseModel):
    """Few-body no-core shell-model matrix-element parameters."""

    model_config = ConfigDict(extra="forbid")
    N_max: int = Field(ge=2, description="Truncation parameter.")
    bodies: int = Field(default=2, ge=2, le=4)
    operator: Literal["E1", "M1", "E2"] = "E1"


_KIND_TO_MODEL_DOMAIN: dict[str, ModelDomain] = {
    "zero_nu_bb_toy": "1+1D_toy",
    "ncsm_matrix_element": "few_body_3d",
    "effective_hamiltonian": "effective_hamiltonian",
}


def model_domain_for_kind(kind: str) -> ModelDomain:
    """Return the canonical ``model_domain`` tag for a problem kind.

    The frontend visualizer (PROMPT 7) uses this to pick the right
    caveat banner. New kinds MUST register here.
    """
    try:
        return _KIND_TO_MODEL_DOMAIN[kind]
    except KeyError as exc:
        msg = f"unknown nuclear problem kind: {kind!r}"
        raise ValueError(msg) from exc


class NuclearProblem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ProblemKind
    backend_preference: BackendPreference = "auto"
    shots: int = Field(default=1024, ge=1)
    seed: int = 0
    zero_nu_bb_toy: ZeroNuBBToyParams | None = None
    ncsm_matrix_element: NCSMParams | None = None
    effective_hamiltonian: EffectiveHamiltonianParams | None = None

    @model_validator(mode="after")
    def _kind_matches_payload(self) -> "NuclearProblem":
        attr = self.kind
        present = getattr(self, attr)
        if present is None:
            msg = f"kind={self.kind!r} requires the matching '{attr}' payload."
            raise ValueError(msg)
        return self

    @property
    def model_domain(self) -> ModelDomain:
        """Canonical model-domain tag (drives ProvenanceRecord)."""
        return model_domain_for_kind(self.kind)

    def canonical_payload(self) -> dict[str, Any]:
        block = getattr(self, self.kind)
        return {"kind": self.kind, "params": block.model_dump() if block else None}


def load_instance(name: str) -> NuclearProblem:
    candidate = Path(name)
    if candidate.is_file():
        text = candidate.read_text()
    else:
        try:
            text = (
                resources.files("qfull_nuc.instances")
                .joinpath(f"{name.lower()}.yaml")
                .read_text()
            )
        except (FileNotFoundError, ModuleNotFoundError) as exc:
            msg = (
                f"Unknown instance {name!r}. Pass a YAML path or one of "
                "zero_nu_bb_l4 / zero_nu_bb_l6 / ncsm_2body / "
                "heavy_neutrino_mixing / sterile_neutrino_osc."
            )
            raise FileNotFoundError(msg) from exc
    payload = yaml.safe_load(text)
    return NuclearProblem.model_validate(payload)
