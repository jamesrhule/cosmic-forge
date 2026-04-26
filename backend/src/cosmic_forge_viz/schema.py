"""Pydantic visualization frame schemas, one per domain.

The frontend mirrors these types; field names and casing are part of
the wire contract and must match the TypeScript declarations in
`src/types/visualizer.ts` (cosmology) and the new domain panels.
"""

from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

# Domain tag attached to every manifest. The frontend domain selector
# reads this to pick the right panel set.
Domain = Literal[
    "cosmology",
    "chemistry",
    "condmat",
    "hep",
    "nuclear",
    "amo",
]

# Coarse-grained phase labels. Cosmology has its own dedicated set
# (`Phase` in src/types/visualizer.ts); the new domains share a smaller
# generic vocabulary used for transport-bar color coding.
Phase = Literal[
    "inflation",
    "gb_window",
    "reheating",
    "radiation",
    "sphaleron",
    "warmup",
    "scf",
    "post_scf",
    "thermalize",
    "quench",
    "equilibrium",
    "vacuum",
    "string_break",
    "ground",
    "decay",
    "load",
    "rydberg",
    "measure",
]


class BaseFrame(BaseModel):
    """Fields shared by every per-domain frame."""

    model_config = ConfigDict(extra="forbid")

    tau: float
    """Wall-clock or simulated time within the run."""

    phase: Phase
    """Coarse-grained phase tag for transport-bar color coding."""

    active_terms: list[str] = Field(default_factory=list)
    """Active formula / Hamiltonian terms at this frame.

    For UCGLE F1–F7, see `formulas.active_terms_for_variant`. Other
    domains pass term IDs from their own Hamiltonian registry.
    """

    provenance_ref: str | None = None
    """ProvenanceRecord URI (qcompass-core manifest) for this frame, if any."""


# ---------------------------------------------------------------------------
# Cosmology — UCGLE-F1
# ---------------------------------------------------------------------------


class _ModeSample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    k: float
    h_plus_re: float
    h_plus_im: float
    h_minus_re: float
    h_minus_im: float
    alpha_sq_minus_beta_sq: float
    in_tachyonic_window: bool = False
    kk_level: int | None = None


class _SgwbSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    f_Hz: list[float]
    Omega_gw: list[float]
    chirality: list[float]


class _AnomalyIntegrand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    k: list[float]
    integrand: list[float]
    running_integral: list[float]
    cutoff: float


class _LeptonFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chiral_gw: float
    anomaly: float
    delta_N_L: float
    eta_B_running: float


class CosmologyFrame(BaseFrame):
    """UCGLE-F1 frame: modes, B±, sgwb, anomaly, lepton flow."""

    domain: Literal["cosmology"] = "cosmology"
    t_cosmic_seconds: float = 0.0
    modes: list[_ModeSample] = Field(default_factory=list)
    B_plus: float = 0.0
    B_minus: float = 0.0
    xi_dot_H: float = 0.0
    sgwb_snapshot: _SgwbSnapshot | None = None
    anomaly_integrand: _AnomalyIntegrand | None = None
    lepton_flow: _LeptonFlow | None = None


# ---------------------------------------------------------------------------
# Chemistry
# ---------------------------------------------------------------------------


class _Orbital(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    energy_hartree: float
    occupation: float
    coefficients: list[float] = Field(default_factory=list)


class _SlaterDeterminant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    weight: float
    occupations: list[int]


class _HamiltonianTerm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    coefficient: float
    operator: str


class ChemistryFrame(BaseFrame):
    """Quantum chemistry: SCF / VQE / SQD progression."""

    domain: Literal["chemistry"] = "chemistry"
    iteration: int = 0
    orbitals: list[_Orbital] = Field(default_factory=list)
    energy_convergence: list[float] = Field(default_factory=list)
    slater_determinants: list[_SlaterDeterminant] = Field(default_factory=list)
    hamiltonian_terms: list[_HamiltonianTerm] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Condensed matter
# ---------------------------------------------------------------------------


class _LatticeSite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    x: float
    y: float
    z: float = 0.0
    spin: float = 0.0


class _Bond(BaseModel):
    model_config = ConfigDict(extra="forbid")
    a: int
    b: int
    strength: float


class _OtocButterfly(BaseModel):
    model_config = ConfigDict(extra="forbid")
    times: list[float]
    distances: list[float]
    intensity: list[list[float]]
    """`intensity[t][d]` = OTOC at time-index t, lattice-distance d."""


class _SpectralFunction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    omega: list[float]
    k: list[float]
    Akw: list[list[float]]


class CondmatFrame(BaseFrame):
    """Condensed-matter frame: lattice + OTOC + A(k,ω)."""

    domain: Literal["condmat"] = "condmat"
    lattice_sites: list[_LatticeSite] = Field(default_factory=list)
    bond_strengths: list[_Bond] = Field(default_factory=list)
    otoc_butterfly: _OtocButterfly | None = None
    spectral_function_Akw: _SpectralFunction | None = None


# ---------------------------------------------------------------------------
# HEP / lattice gauge
# ---------------------------------------------------------------------------


class _Plaquette(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cell: tuple[int, int, int]
    flux: float
    energy: float = 0.0


class HepFrame(BaseFrame):
    """High-energy physics: gauge plaquettes, chiral condensate, string tension."""

    domain: Literal["hep"] = "hep"
    plaquettes: list[_Plaquette] = Field(default_factory=list)
    chiral_condensate: float = 0.0
    string_tension: float = 0.0


# ---------------------------------------------------------------------------
# Nuclear
# ---------------------------------------------------------------------------


class _ShellOccupation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shell: str
    n: float
    energy_MeV: float = 0.0


class _LnvTracker(BaseModel):
    model_config = ConfigDict(extra="forbid")
    delta_L: float
    delta_B: float
    rate: float


class NuclearFrame(BaseFrame):
    """Nuclear-structure frame: shell occupations + LNV decay tracker."""

    domain: Literal["nuclear"] = "nuclear"
    shell_occupation: list[_ShellOccupation] = Field(default_factory=list)
    lnv_tracker: _LnvTracker | None = None


# ---------------------------------------------------------------------------
# AMO / neutral-atom arrays
# ---------------------------------------------------------------------------


class _AtomPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    x: float
    y: float
    z: float = 0.0
    rydberg: bool = False


class _BlockadeRadius(BaseModel):
    model_config = ConfigDict(extra="forbid")
    atom: int
    r_blockade: float


class _Correlations(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pairs: list[tuple[int, int]]
    g2: list[float]


class AmoFrame(BaseFrame):
    """Neutral-atom array frame."""

    domain: Literal["amo"] = "amo"
    atom_positions: list[_AtomPosition] = Field(default_factory=list)
    blockade_radii: list[_BlockadeRadius] = Field(default_factory=list)
    correlations: _Correlations | None = None


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


VisualizationFrame = Union[
    CosmologyFrame,
    ChemistryFrame,
    CondmatFrame,
    HepFrame,
    NuclearFrame,
    AmoFrame,
]


class VisualizationManifest(BaseModel):
    """Wire-level metadata returned by GET /api/runs/{domain}/{id}/manifest."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    domain: Domain
    frame_count: int
    formula_variant: str | None = None
    """For cosmology runs: F1..F7. None for other domains."""
    bake_uri: str | None = None
    """Zarr / HDF5 store URI when `baker.bake_timeline` has been called."""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_FRAME_BY_DOMAIN: dict[str, type[BaseFrame]] = {
    "cosmology": CosmologyFrame,
    "chemistry": ChemistryFrame,
    "condmat": CondmatFrame,
    "hep": HepFrame,
    "nuclear": NuclearFrame,
    "amo": AmoFrame,
}


def frame_for_domain(domain: str) -> type[BaseFrame]:
    """Return the concrete frame class for `domain` or raise `KeyError`."""
    try:
        return _FRAME_BY_DOMAIN[domain]
    except KeyError as exc:
        raise KeyError(
            f"unknown domain {domain!r}; valid: {sorted(_FRAME_BY_DOMAIN)}"
        ) from exc
