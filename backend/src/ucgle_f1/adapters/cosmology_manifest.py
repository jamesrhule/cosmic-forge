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

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..domain import (
    Couplings as _Couplings,
)
from ..domain import (
    Potential as _Potential,
)
from ..domain import (
    Reheating as _Reheating,
)
from ..domain import (
    RunConfig as _RunConfig,
)


PotentialKind = Literal["starobinsky", "natural", "hilltop", "custom"]
Precision = Literal["fast", "standard", "high"]


class CosmologyPotential(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: PotentialKind
    params: dict[str, float] = Field(default_factory=dict)
    customPython: str | None = None


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
