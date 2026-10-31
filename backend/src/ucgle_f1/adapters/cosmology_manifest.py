"""Cosmology manifest for the ``cosmology.ucglef1`` qcompass plugin.

Mirrors the existing :class:`ucgle_f1.domain.RunConfig` 1-for-1 so a
caller targeting the qcompass protocol can pass the same payload the
M8 agent already accepts. No new fields. Field names, casing, and
defaults match the frontend contract at ``src/types/domain.ts`` and
the Pydantic source of truth at
``backend/src/ucgle_f1/domain.py::RunConfig``.

Why a separate model rather than re-exporting :class:`RunConfig`?

  - :class:`RunConfig` is the *internal* envelope every run uses; it
    carries optional ``agent`` traceability fields that don't belong
    in a generic Manifest.problem dict.
  - Pinning a *manifest-shaped* model here lets us evolve the
    qcompass surface independently of the legacy run config without
    drifting either side.

The two stay in lock-step via :func:`from_run_config` and
:func:`to_run_config`, both of which are exercised by the adapter
tests.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema, model_validator

from ..domain import (
    Couplings as _Couplings,
)
from ..domain import (
    Potential as _Potential,
)
from ..domain import potential_forms_text, potential_params_json_schema
from ..domain import (
    Reheating as _Reheating,
)
from ..domain import (
    RunConfig as _RunConfig,
)


Precision = Literal["fast", "standard", "high"]


class CosmologyPotential(_Potential):
    """The run route's potential (W1-PARAMS): :class:`ucgle_f1.domain.Potential`'s
    forms, units and checks (one model, R20), with every parameter of the
    chosen form required, so an incomplete config is refused at submit (422)
    instead of failing in the worker."""

    params: Annotated[
        dict[str, float], WithJsonSchema(potential_params_json_schema(required=True)),
    ] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _complete(self) -> CosmologyPotential:
        missing = self.missing_params()
        if missing:
            forms = potential_forms_text(self.kind)
            msg = f"{self.kind} potential: missing {', '.join(missing)}; {forms}"
            raise ValueError(msg)
        if self.kind == "custom" and not self.customPython:
            raise ValueError("custom potential: customPython is required")
        return self


class CosmologyCouplings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    xi: float
    theta_grav: float
    f_a: float
    M_star: float
    M1: float
    S_E2: float


class CosmologyReheating(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Gamma_phi: float
    T_reh_GeV: float


class CosmologyManifest(BaseModel):
    """The ``problem`` payload for ``Manifest(domain="cosmology", ...)``.

    The qcompass envelope wraps this in a
    :class:`qcompass_core.Manifest`; the adapter unwraps and
    converts to :class:`RunConfig`.
    """

    model_config = ConfigDict(extra="forbid")

    potential: CosmologyPotential
    couplings: CosmologyCouplings
    reheating: CosmologyReheating
    precision: Precision = "standard"


def from_run_config(cfg: _RunConfig) -> CosmologyManifest:
    """Project a :class:`RunConfig` (loses ``agent`` traceability)."""
    return CosmologyManifest(
        potential=CosmologyPotential(**cfg.potential.model_dump()),
        couplings=CosmologyCouplings(**cfg.couplings.model_dump()),
        reheating=CosmologyReheating(**cfg.reheating.model_dump()),
        precision=cfg.precision,
    )


def to_run_config(manifest: CosmologyManifest) -> _RunConfig:
    """Inflate a :class:`CosmologyManifest` to a :class:`RunConfig`.

    No agent metadata is attached; runs spawned via the qcompass path
    are expected to populate ``cfg.agent`` themselves before any
    ``start_run`` call (the M8 agent does this).
    """
    return _RunConfig(
        potential=_Potential(**manifest.potential.model_dump()),
        couplings=_Couplings(**manifest.couplings.model_dump()),
        reheating=_Reheating(**manifest.reheating.model_dump()),
        precision=manifest.precision,
        agent=None,
    )
