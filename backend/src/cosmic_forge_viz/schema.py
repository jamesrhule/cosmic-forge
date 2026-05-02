"""Per-domain visualization frame schemas (PROMPT 7 v2 §PART B).

Every frame inherits :class:`BaseFrame` (tau / phase / active_terms /
provenance_ref) and adds the domain-specific channels the panels
consume. Frames serialise to JSON for REST snapshots and to
ormsgpack for the WS / SSE streams.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

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


class BaseFrame(BaseModel):
    """Common fields every frame carries."""

    model_config = ConfigDict(extra="forbid")

    tau: float = Field(
        description=(
            "Dimensionless elapsed time / step. For UCGLE-F1 this "
            "is conformal time τ; for chemistry it's the SCF "
            "iteration index; etc."
        ),
    )
    phase: str = Field(
        description=(
            "Domain-specific phase label, e.g. 'inflation' / "
            "'reheating' for cosmology, 'iter' for chemistry."
        ),
    )
    active_terms: list[str] = Field(
        default_factory=list,
        description=(
            "Names of the formulas / terms active at this frame. "
            "Cosmology populates this from the F1-F7 rules in "
            ":mod:`formulas`."
        ),
    )
    provenance_ref: str | None = Field(
        default=None,
        description="run_id of the originating ProvenanceRecord.",
    )


# ── Cosmology ───────────────────────────────────────────────────────


class CosmologyModeBlock(BaseModel):
    """Light-cone / mode-frequency snapshot."""

    model_config = ConfigDict(extra="forbid")

    k: list[float] = Field(default_factory=list)
    omega_re: list[float] = Field(default_factory=list)
    omega_im: list[float] = Field(default_factory=list)


class CosmologyFrame(BaseFrame):
    """sGB-CS visualisation frame (UCGLE-F1)."""

    domain: Literal["cosmology"] = "cosmology"
    modes: CosmologyModeBlock = Field(default_factory=CosmologyModeBlock)
    B_plus: list[float] = Field(default_factory=list)
    B_minus: list[float] = Field(default_factory=list)
    sgwb: list[float] = Field(
        default_factory=list,
        description="Stochastic GW background spectrum h²Ω_GW(f).",
    )
    anomaly: float = Field(default=0.0, description="η_anomaly proxy.")
    lepton_flow: float = Field(
        default=0.0,
        description="Net lepton-number flow (J_L) at this τ.",
    )


# ── Chemistry ──────────────────────────────────────────────────────


class ChemistryFrame(BaseFrame):
    """SCF / VQE iteration frame."""

    domain: Literal["chemistry"] = "chemistry"
    orbitals: list[float] = Field(
        default_factory=list,
        description="Per-orbital occupation (length = n_orbitals).",
    )
    energy_convergence: list[float] = Field(
        default_factory=list,
        description="ΔE per iteration (Ha).",
    )
    slater: list[list[float]] = Field(
        default_factory=list,
        description="Slater-flow Sankey weights between (i,j) orbitals.",
    )


# ── Condmat ────────────────────────────────────────────────────────


class CondmatFrame(BaseFrame):
    """Lattice-model frame."""

    domain: Literal["condmat"] = "condmat"
    lattice_sites: list[list[float]] = Field(
        default_factory=list,
        description="(N, 2) site coordinates.",
    )
    bond_strengths: list[float] = Field(
        default_factory=list,
        description="One scalar per bond; len matches the lattice graph.",
    )
    otoc: list[list[float]] = Field(
        default_factory=list,
        description="OTOC (out-of-time-order) heatmap, indexed [t][site].",
    )
    spectral: list[list[float]] = Field(
        default_factory=list,
        description="A(k, ω) heatmap, indexed [k][ω].",
    )


# ── HEP ────────────────────────────────────────────────────────────


class ParticleObservableEntry(BaseModel):
    """Mirrors :class:`qfull_hep.ParticleObservable` over the wire."""

    model_config = ConfigDict(extra="forbid")
    value: float | None = None
    unit: str = ""
    uncertainty: float | None = None
    status: str = "unavailable"
    notes: str = ""


class HepFrame(BaseFrame):
    """Lattice-gauge frame."""

    domain: Literal["hep"] = "hep"
    plaquettes: list[float] = Field(
        default_factory=list,
        description="Per-plaquette gauge action density.",
    )
    chiral_condensate: float = Field(default=0.0)
    string_tension: float = Field(default=0.0)
    particle_obs: dict[str, ParticleObservableEntry] = Field(
        default_factory=dict,
        description=(
            "Mirror of HEPResult.particle_obs (chiral_condensate / "
            "string_tension / anomaly_density). The frontend's "
            "ParticleObservablesTable consumes this."
        ),
    )


# ── Nuclear ────────────────────────────────────────────────────────


class NuclearFrame(BaseFrame):
    """Nuclear-shell / 0νββ frame."""

    domain: Literal["nuclear"] = "nuclear"
    shell_occupation: list[float] = Field(
        default_factory=list,
        description="Per-shell occupation; len = single-particle dim.",
    )
    lnv_tracker: float = Field(
        default=0.0,
        description=(
            "Lepton-number-violation signal at this τ; 0 = none, "
            "1 = qualitative LNV present."
        ),
    )
    model_domain: Literal[
        "1+1D_toy", "few_body_3d", "effective_hamiltonian",
    ] = "1+1D_toy"


# ── AMO ────────────────────────────────────────────────────────────


class AmoFrame(BaseFrame):
    """Rydberg / atom-array frame."""

    domain: Literal["amo"] = "amo"
    atom_positions: list[list[float]] = Field(
        default_factory=list,
        description="(N, 3) atom coordinates in μm.",
    )
    blockade_radii: list[float] = Field(
        default_factory=list,
        description="Per-atom Rydberg blockade radius in μm.",
    )
    correlations: list[list[float]] = Field(
        default_factory=list,
        description="(N, N) Rydberg-Rydberg correlation matrix.",
    )


# ── Gravity (PROMPT 9 v2 §A) ──────────────────────────────────────


class GravityFrame(BaseFrame):
    """SYK / JT visualisation frame.

    Carries the v2 provenance fields prominently — the frontend's
    visualizer surfaces ``provenance_warning`` next to the SFF
    panel whenever ``is_learned_hamiltonian`` is true.
    """

    domain: Literal["gravity"] = "gravity"
    spectrum: list[float] = Field(
        default_factory=list,
        description="Sorted eigenvalues of the SYK / JT Hamiltonian.",
    )
    spectral_form_factor: list[float] = Field(
        default_factory=list,
        description="g(t) at evenly-spaced t values.",
    )
    is_learned_hamiltonian: bool = False
    provenance_warning: str | None = None
    model_domain: Literal[
        "toy_SYK_1+1D", "JT_matrix_model", "SYK_sparse",
    ] = "toy_SYK_1+1D"


# ── Statmech (PROMPT 9 v2 §B) ─────────────────────────────────────


class StatmechFrame(BaseFrame):
    """QAE / Metropolis / TFD visualisation frame."""

    domain: Literal["statmech"] = "statmech"
    estimate: float = Field(
        default=0.0,
        description="QAE estimate, ⟨E⟩, or partition function snapshot.",
    )
    sigma: float = Field(
        default=0.0, description="1σ uncertainty on the estimate.",
    )
    truth: float | None = Field(
        default=None,
        description="Closed-form ground truth (when available).",
    )
    history: list[float] = Field(
        default_factory=list,
        description="Per-step trace of the Markov / QAE estimator.",
    )


VisualizationFrame = Annotated[
    Union[
        CosmologyFrame,
        ChemistryFrame,
        CondmatFrame,
        HepFrame,
        NuclearFrame,
        AmoFrame,
        GravityFrame,
        StatmechFrame,
    ],
    Field(discriminator="domain"),
]


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


def frame_class_for_domain(domain: str) -> type[BaseFrame]:
    """Return the Pydantic frame class for ``domain``."""
    try:
        return _FRAME_CLASSES[domain]
    except KeyError as exc:
        msg = f"Unknown domain: {domain!r}"
        raise KeyError(msg) from exc


class VisualizationTimeline(BaseModel):
    """Container for a full per-run timeline."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    domain: DomainName
    schema_version: int = 1
    frames: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Frames stored as dicts so a single timeline can carry "
            "any subclass without losing type info on round-trip."
        ),
    )

    def append(self, frame: BaseFrame) -> None:
        self.frames.append(frame.model_dump(mode="json"))

    def parsed_frames(self) -> list[BaseFrame]:
        cls = frame_class_for_domain(self.domain)
        return [cls.model_validate(f) for f in self.frames]
