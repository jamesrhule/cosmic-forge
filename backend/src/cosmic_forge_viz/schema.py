"""Per-domain visualization frame schemas.

One schema for every consumer (P0-02 unification of the agent-branch
and router-branch ``cosmic_forge_viz``):

* Field names, casing and nesting of the six original domains follow
  the router-branch wire contract, which mirrors the frontend types in
  ``src/types/visualizer.ts`` (cosmology) and ``src/types/manifest.ts``
  (other domains).
* The agent-branch additions are kept: gravity and statmech frames,
  ``HepFrame.particle_obs``, ``NuclearFrame.model_domain``, the
  chemistry Slater flow matrix, and the ``VisualizationTimeline``
  container used by the M8 qcompass routes.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DomainName = Literal[
    "cosmology",
    "chemistry",
    "condmat",
    "hep",
    "nuclear",
    "amo",
    "gravity",
    "statmech",
]
Domain = DomainName

# Coarse-grained phase labels used for transport-bar colour coding.
# The cosmology subset matches `Phase` in src/types/visualizer.ts.
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
    phase: Phase
    active_terms: list[str] = Field(default_factory=list)
    provenance_ref: str | None = None


# ── Cosmology (UCGLE-F1) ──────────────────────────────────────────


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
    domain: Literal["cosmology"] = "cosmology"
    t_cosmic_seconds: float = 0.0
    modes: list[_ModeSample] = Field(default_factory=list)
    B_plus: float = 0.0
    B_minus: float = 0.0
    xi_dot_H: float = 0.0
    sgwb_snapshot: _SgwbSnapshot | None = None
    anomaly_integrand: _AnomalyIntegrand | None = None
    lepton_flow: _LeptonFlow | None = None


# ── Chemistry ─────────────────────────────────────────────────────


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
    domain: Literal["chemistry"] = "chemistry"
    iteration: int = 0
    orbitals: list[_Orbital] = Field(default_factory=list)
    energy_convergence: list[float] = Field(default_factory=list)
    slater_determinants: list[_SlaterDeterminant] = Field(default_factory=list)
    slater: list[list[float]] = Field(
        default_factory=list,
        description="Orbital→orbital Slater-flow weight matrix (Sankey view).",
    )
    hamiltonian_terms: list[_HamiltonianTerm] = Field(default_factory=list)


# ── Condensed matter ──────────────────────────────────────────────


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
    domain: Literal["condmat"] = "condmat"
    lattice_sites: list[_LatticeSite] = Field(default_factory=list)
    bond_strengths: list[_Bond] = Field(default_factory=list)
    otoc_butterfly: _OtocButterfly | None = None
    spectral_function_Akw: _SpectralFunction | None = None


# ── HEP / lattice gauge ───────────────────────────────────────────


class _Plaquette(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cell: tuple[int, int, int]
    flux: float
    energy: float = 0.0


class ParticleObservableEntry(BaseModel):
    """Mirrors :class:`qfull_hep.ParticleObservable` over the wire."""

    model_config = ConfigDict(extra="forbid")
    value: float | None = None
    unit: str = ""
    uncertainty: float | None = None
    status: str = "unavailable"
    notes: str = ""


class HepFrame(BaseFrame):
    domain: Literal["hep"] = "hep"
    plaquettes: list[_Plaquette] = Field(default_factory=list)
    chiral_condensate: float = 0.0
    string_tension: float = 0.0
    particle_obs: dict[str, ParticleObservableEntry] = Field(default_factory=dict)


# ── Nuclear ───────────────────────────────────────────────────────


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
    domain: Literal["nuclear"] = "nuclear"
    shell_occupation: list[_ShellOccupation] = Field(default_factory=list)
    lnv_tracker: _LnvTracker | None = None
    model_domain: Literal[
        "1+1D_toy", "few_body_3d", "effective_hamiltonian",
    ] = "1+1D_toy"


# ── AMO / neutral-atom arrays ─────────────────────────────────────


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
    domain: Literal["amo"] = "amo"
    atom_positions: list[_AtomPosition] = Field(default_factory=list)
    blockade_radii: list[_BlockadeRadius] = Field(default_factory=list)
    correlations: _Correlations | None = None


# ── Gravity (SYK / JT) ────────────────────────────────────────────


class GravityFrame(BaseFrame):
    """The frontend surfaces ``provenance_warning`` prominently whenever
    ``is_learned_hamiltonian`` is true."""

    domain: Literal["gravity"] = "gravity"
    spectrum: list[float] = Field(default_factory=list)
    spectral_form_factor: list[float] = Field(default_factory=list)
    is_learned_hamiltonian: bool = False
    provenance_warning: str | None = None
    model_domain: Literal[
        "toy_SYK_1+1D", "JT_matrix_model", "SYK_sparse",
    ] = "toy_SYK_1+1D"


# ── Statistical mechanics ─────────────────────────────────────────


class StatmechFrame(BaseFrame):
    domain: Literal["statmech"] = "statmech"
    estimate: float = 0.0
    sigma: float = 0.0
    truth: float | None = None
    history: list[float] = Field(default_factory=list)


VisualizationFrame = Annotated[
    CosmologyFrame | ChemistryFrame | CondmatFrame | HepFrame | NuclearFrame | AmoFrame | GravityFrame | StatmechFrame,
    Field(discriminator="domain"),
]


class VisualizationManifest(BaseModel):
    """Wire-level metadata returned by GET /api/runs/{domain}/{id}/manifest."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    domain: DomainName
    frame_count: int
    formula_variant: str | None = None
    """For cosmology runs: F1..F7. None for other domains."""
    bake_uri: str | None = None
    """Zarr store URI when `baker.bake_timeline` has been called."""
    metadata: dict[str, Any] = Field(default_factory=dict)


_FRAME_CLASSES: dict[str, type[BaseFrame]] = {
    "cosmology": CosmologyFrame,
    "chemistry": ChemistryFrame,
    "condmat": CondmatFrame,
    "hep": HepFrame,
    "nuclear": NuclearFrame,
    "amo": AmoFrame,
    "gravity": GravityFrame,
    "statmech": StatmechFrame,
}


def frame_for_domain(domain: str) -> type[BaseFrame]:
    """Return the concrete frame class for ``domain`` or raise ``KeyError``."""
    try:
        return _FRAME_CLASSES[domain]
    except KeyError as exc:
        msg = f"Unknown domain {domain!r}; valid: {sorted(_FRAME_CLASSES)}"
        raise KeyError(msg) from exc


frame_class_for_domain = frame_for_domain


class VisualizationTimeline(BaseModel):
    """Container for a full per-run timeline (JSON snapshot on disk)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    domain: DomainName
    schema_version: int = 1
    synthetic: bool = Field(
        default=False,
        description="True when frames come from the synthetic generator (R7).",
    )
    formula_variant: str | None = None
    frames: list[dict[str, Any]] = Field(default_factory=list)

    def append(self, frame: BaseFrame) -> None:
        self.frames.append(frame.model_dump(mode="json"))

    def parsed_frames(self) -> list[BaseFrame]:
        cls = frame_for_domain(self.domain)
        return [cls.model_validate(f) for f in self.frames]
