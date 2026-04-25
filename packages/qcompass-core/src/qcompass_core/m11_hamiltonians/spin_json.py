"""Spin-Hamiltonian JSON schema.

Domain-agnostic envelope for lattice / model Hamiltonians. The
canonical form lists single-site terms (h_i operator coefficients)
and pair couplings keyed by (site_a, site_b, operator).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..errors import HamiltonianFormatError


class SiteTerm(BaseModel):
    """Single-site term (e.g. transverse field)."""

    model_config = ConfigDict(extra="forbid")

    site: int = Field(ge=0)
    op: Literal["X", "Y", "Z", "I", "Sx", "Sy", "Sz", "Sp", "Sm", "n"]
    coeff: float


class PairTerm(BaseModel):
    """Two-site coupling (e.g. exchange interaction)."""

    model_config = ConfigDict(extra="forbid")

    site_a: int = Field(ge=0)
    site_b: int = Field(ge=0)
    op_a: str
    op_b: str
    coeff: float


class SpinHamiltonian(BaseModel):
    """Validated spin-Hamiltonian description."""

    model_config = ConfigDict(extra="forbid")

    n_sites: int = Field(ge=1)
    spin: float = Field(default=0.5, ge=0.5)
    site_terms: list[SiteTerm] = Field(default_factory=list)
    pair_terms: list[PairTerm] = Field(default_factory=list)
    boundary: Literal["open", "periodic", "twisted"] = "open"

    @model_validator(mode="after")
    def _check_indices(self) -> "SpinHamiltonian":
        for term in self.site_terms:
            if term.site >= self.n_sites:
                msg = f"site_term references site {term.site} out of range."
                raise ValueError(msg)
        for term in self.pair_terms:
            if term.site_a >= self.n_sites or term.site_b >= self.n_sites:
                msg = (
                    f"pair_term ({term.site_a},{term.site_b}) out of range "
                    f"for n_sites={self.n_sites}."
                )
                raise ValueError(msg)
        return self


def validate_spin_hamiltonian(payload: dict[str, object]) -> SpinHamiltonian:
    """Parse and validate a spin-Hamiltonian dict.

    Raises :class:`HamiltonianFormatError` for any parsing failure so
    callers can catch the QCompass-family exception uniformly.
    """
    try:
        return SpinHamiltonian.model_validate(payload)
    except Exception as exc:
        raise HamiltonianFormatError(str(exc)) from exc
