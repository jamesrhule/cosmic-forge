"""Synthetic frame generators.

Used by the test suite, the CLI ``demo``/``bake`` commands, the
visualizer empty state, and the M8 qcompass visualization route until
real run output is baked (P4-04). Output is deterministic for a given
(domain, seed, total_frames, options) tuple. Everything produced here
is synthetic: manifests carry ``metadata["synthetic"] = True`` and
timelines carry ``synthetic = True`` (R7).
"""

from __future__ import annotations

import math
import random
import zlib
from collections.abc import Iterable

from .formulas import (
    active_terms_for_variant,
    default_active_terms,
    formulas_at_phase,
)
from .phases import phase_for, progression
from .schema import (
    AmoFrame,
    BaseFrame,
    ChemistryFrame,
    CondmatFrame,
    CosmologyFrame,
    GravityFrame,
    HepFrame,
    NuclearFrame,
    ParticleObservableEntry,
    StatmechFrame,
    VisualizationManifest,
    VisualizationTimeline,
)

DOMAINS: tuple[str, ...] = (
    "cosmology", "chemistry", "condmat", "hep", "nuclear", "amo", "gravity", "statmech",
)


def stable_seed(text: str) -> int:
    """Process-independent seed from a string (``hash()`` is salted per process)."""
    return zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def _tau(i: int, total: int, tau_max: float | None) -> float:
    if tau_max is None:
        return float(i)
    return i * tau_max / max(1, total - 1)


# ── Cosmology ─────────────────────────────────────────────────────


def cosmology_frames(
    *,
    total_frames: int = 60,
    formula_variant: str = "F1",
    seed: int = 0,
    n_modes: int = 12,
    couplings: dict[str, float] | None = None,
    tau_max: float | None = None,
) -> list[CosmologyFrame]:
    rng = _rng(seed)
    out: list[CosmologyFrame] = []
    for i in range(total_frames):
        phase = phase_for("cosmology", i, total_frames)
        in_window = phase == "gb_window"
        modes = []
        for m in range(n_modes):
            k = 0.1 + m * 0.3
            phi = rng.random() * math.tau
            modes.append(
                {
                    "k": k,
                    "h_plus_re": math.cos(phi) * (1.0 + 0.05 * m),
                    "h_plus_im": math.sin(phi) * (1.0 + 0.05 * m),
                    "h_minus_re": math.cos(phi + 0.1) * (1.0 - 0.03 * m),
                    "h_minus_im": math.sin(phi + 0.1) * (1.0 - 0.03 * m),
                    "alpha_sq_minus_beta_sq": 0.05 * (m + 1) * (1 if in_window else 0.1),
                    "in_tachyonic_window": in_window,
                    "kk_level": (m % 4) if formula_variant in {"F3", "F5", "F7"} else None,
                }
            )
        terms = active_terms_for_variant(
            formula_variant, phase=phase, in_tachyonic_window=in_window,
        )
        if couplings is not None:
            terms = terms + [f for f in formulas_at_phase(phase, couplings) if f not in terms]
        out.append(
            CosmologyFrame(
                tau=_tau(i, total_frames, tau_max),
                phase=phase,
                t_cosmic_seconds=i * 1e-32,
                modes=modes,
                B_plus=math.exp(-((i - total_frames / 2) ** 2) / (2 * total_frames)),
                B_minus=0.5 * math.exp(-((i - total_frames / 2) ** 2) / (2 * total_frames)),
                xi_dot_H=0.4 if in_window else 0.05,
                active_terms=terms,
            )
        )
    return out


# ── Chemistry ─────────────────────────────────────────────────────


def chemistry_frames(
    *, total_frames: int = 60, seed: int = 0, n_orbitals: int = 8, tau_max: float | None = None,
) -> list[ChemistryFrame]:
    rng = _rng(seed)
    energies: list[float] = []
    base = -1.5
    for _ in range(total_frames):
        last = energies[-1] if energies else 0.0
        energies.append(last + (base - last) * 0.18 + rng.uniform(-0.005, 0.005))
    out: list[ChemistryFrame] = []
    half = n_orbitals // 2
    for i in range(total_frames):
        phase = phase_for("chemistry", i, total_frames)
        orbitals = [
            {
                "index": o,
                "energy_hartree": -1.0 / (o + 1) + rng.uniform(-0.01, 0.01),
                "occupation": 2.0 if o < half else 0.0,
                "coefficients": [],
            }
            for o in range(n_orbitals)
        ]
        slater = [
            [0.1 * math.exp(-abs(p - q) - 0.05 * i) for q in range(n_orbitals)]
            for p in range(n_orbitals)
        ]
        out.append(
            ChemistryFrame(
                tau=_tau(i, total_frames, tau_max),
                phase=phase,
                iteration=i,
                orbitals=orbitals,
                energy_convergence=list(energies[: i + 1]),
                slater_determinants=[
                    {
                        "label": "|HF⟩",
                        "weight": 0.92 - 0.001 * i,
                        "occupations": [1] * half + [0] * (n_orbitals - half),
                    },
                    {
                        "label": "|S1⟩",
                        "weight": max(0.0, 0.07 + 0.0008 * i),
                        "occupations": [1] * (half - 1) + [0, 1] + [0] * (n_orbitals - half - 1),
                    },
                ],
                slater=slater,
                hamiltonian_terms=[
                    {"label": "h_pq", "coefficient": -0.5, "operator": "a†_p a_q"},
                    {"label": "g_pqrs", "coefficient": 0.25, "operator": "a†_p a†_q a_s a_r"},
                ],
                active_terms=default_active_terms("chemistry"),
            )
        )
    return out


# ── Condensed matter ──────────────────────────────────────────────


def condmat_frames(
    *, total_frames: int = 60, seed: int = 0, lattice: int = 6, tau_max: float | None = None,
) -> list[CondmatFrame]:
    rng = _rng(seed)
    sites = [
        {"index": x * lattice + y, "x": float(x), "y": float(y), "z": 0.0,
         "spin": rng.choice([-1.0, 1.0])}
        for x in range(lattice)
        for y in range(lattice)
    ]
    bonds: list[dict] = []
    for x in range(lattice):
        for y in range(lattice):
            i = x * lattice + y
            if x + 1 < lattice:
                bonds.append({"a": i, "b": i + lattice, "strength": 1.0})
            if y + 1 < lattice:
                bonds.append({"a": i, "b": i + 1, "strength": 1.0})
    out: list[CondmatFrame] = []
    for i in range(total_frames):
        phase = phase_for("condmat", i, total_frames)
        n_t, n_d = 12, lattice
        intensity = [
            [math.exp(-((d - 0.4 * t) ** 2) / 4) * (0.4 + 0.6 * (i / total_frames))
             for d in range(n_d)]
            for t in range(n_t)
        ]
        for b in bonds:
            b["strength"] = 1.0 + 0.2 * math.sin(0.1 * i + 0.3 * b["a"])
        out.append(
            CondmatFrame(
                tau=_tau(i, total_frames, tau_max),
                phase=phase,
                lattice_sites=sites,
                bond_strengths=[dict(b) for b in bonds],
                otoc_butterfly={
                    "times": [t * 0.1 for t in range(n_t)],
                    "distances": [float(d) for d in range(n_d)],
                    "intensity": intensity,
                },
                spectral_function_Akw={
                    "omega": [-3 + k * 0.1 for k in range(60)],
                    "k": [k * (math.pi / 8) for k in range(8)],
                    "Akw": [[math.exp(-(o - k * 0.5) ** 2) for o in range(60)] for k in range(8)],
                },
                active_terms=default_active_terms("condmat"),
            )
        )
    return out


# ── HEP ───────────────────────────────────────────────────────────


def hep_frames(
    *, total_frames: int = 60, seed: int = 0, lattice: int = 4, tau_max: float | None = None,
) -> list[HepFrame]:
    rng = _rng(seed)
    out: list[HepFrame] = []
    for i in range(total_frames):
        phase = phase_for("hep", i, total_frames)
        plaquettes = [
            {"cell": (x, y, z), "flux": rng.uniform(-1, 1),
             "energy": 0.5 + 0.1 * math.sin(0.1 * i + x + y + z)}
            for x in range(lattice)
            for y in range(lattice)
            for z in range(lattice)
        ]
        cond = -0.3 + 0.05 * math.sin(0.05 * i)
        string_t = 0.25 - 0.001 * i
        particle_obs = {
            "chiral_condensate": ParticleObservableEntry(
                value=cond, unit="dimensionless", uncertainty=1.0 / math.sqrt(lattice),
                status="ok", notes="synthetic",
            ),
            "string_tension": ParticleObservableEntry(
                value=string_t, unit="g_squared_per_lattice_spacing", uncertainty=None,
                status="ok", notes="synthetic",
            ),
            "anomaly_density": ParticleObservableEntry(
                value=0.001 * math.sin(0.2 * i), unit="dimensionless",
                uncertainty=1.0 / lattice, status="ok", notes="synthetic",
            ),
        }
        out.append(
            HepFrame(
                tau=_tau(i, total_frames, tau_max),
                phase=phase,
                plaquettes=plaquettes,
                chiral_condensate=cond,
                string_tension=string_t,
                particle_obs=particle_obs,
                active_terms=default_active_terms("hep"),
            )
        )
    return out


# ── Nuclear ───────────────────────────────────────────────────────


def nuclear_frames(
    *, total_frames: int = 60, seed: int = 0, model_domain: str = "1+1D_toy",
    tau_max: float | None = None,
) -> list[NuclearFrame]:
    rng = _rng(seed)
    shells = ["1s1/2", "1p3/2", "1p1/2", "1d5/2", "2s1/2", "1d3/2"]
    out: list[NuclearFrame] = []
    for i in range(total_frames):
        phase = phase_for("nuclear", i, total_frames)
        out.append(
            NuclearFrame(
                tau=_tau(i, total_frames, tau_max),
                phase=phase,
                shell_occupation=[
                    {"shell": s, "n": min(2 * (k + 1), 8) - 0.05 * i + rng.uniform(-0.1, 0.1),
                     "energy_MeV": -8.0 + 1.5 * k}
                    for k, s in enumerate(shells)
                ],
                lnv_tracker={
                    "delta_L": 2.0 if i > total_frames // 2 else 0.0,
                    "delta_B": 0.0,
                    "rate": 1e-26 * (1 + 0.01 * i),
                },
                model_domain=model_domain,  # type: ignore[arg-type]
                active_terms=default_active_terms("nuclear"),
            )
        )
    return out


# ── AMO ───────────────────────────────────────────────────────────


def amo_frames(
    *, total_frames: int = 60, seed: int = 0, n_atoms: int = 16, tau_max: float | None = None,
) -> list[AmoFrame]:
    rng = _rng(seed)
    positions = [
        {"index": k, "x": (k % 4) * 5.0, "y": (k // 4) * 5.0, "z": 0.0, "rydberg": False}
        for k in range(n_atoms)
    ]
    out: list[AmoFrame] = []
    for i in range(total_frames):
        phase = phase_for("amo", i, total_frames)
        for k, p in enumerate(positions):
            p["rydberg"] = phase == "rydberg" and (k + i) % 3 == 0
        out.append(
            AmoFrame(
                tau=_tau(i, total_frames, tau_max),
                phase=phase,
                atom_positions=[dict(p) for p in positions],
                blockade_radii=[
                    {"atom": k, "r_blockade": 6.0 + rng.uniform(-0.2, 0.2)} for k in range(n_atoms)
                ],
                correlations={
                    "pairs": [(k, (k + 1) % n_atoms) for k in range(n_atoms)],
                    "g2": [0.5 + 0.4 * math.sin(0.1 * i + k) for k in range(n_atoms)],
                },
                active_terms=default_active_terms("amo"),
            )
        )
    return out


# ── Gravity ───────────────────────────────────────────────────────


_GRAVITY_MODEL_DOMAINS = {"toy_SYK_1+1D", "JT_matrix_model", "SYK_sparse"}


def gravity_frames(
    *,
    total_frames: int = 60,
    seed: int = 0,
    is_learned_hamiltonian: bool = False,
    provenance_warning: str | None = None,
    model_domain: str = "toy_SYK_1+1D",
    tau_max: float | None = None,
) -> list[GravityFrame]:
    if model_domain not in _GRAVITY_MODEL_DOMAINS:
        model_domain = "toy_SYK_1+1D"
    out: list[GravityFrame] = []
    n = 16
    for i in range(total_frames):
        tau = _tau(i, total_frames, tau_max)
        out.append(
            GravityFrame(
                tau=tau,
                phase=phase_for("gravity", i, total_frames),
                spectrum=[
                    -2.0 + 4.0 * (j + 0.5) / n + 0.05 * math.sin(0.1 * tau + j + seed)
                    for j in range(n)
                ],
                spectral_form_factor=[0.5 + 0.4 * math.cos(0.2 * t + tau / 10.0) for t in range(8)],
                is_learned_hamiltonian=is_learned_hamiltonian,
                provenance_warning=provenance_warning,
                model_domain=model_domain,  # type: ignore[arg-type]
                active_terms=default_active_terms("gravity"),
            )
        )
    return out


# ── Statistical mechanics ─────────────────────────────────────────


def statmech_frames(
    *, total_frames: int = 60, seed: int = 0, tau_max: float | None = None,
) -> list[StatmechFrame]:
    out: list[StatmechFrame] = []
    truth = 0.5
    for i in range(total_frames):
        tau = _tau(i, total_frames, tau_max)
        out.append(
            StatmechFrame(
                tau=tau,
                phase=phase_for("statmech", i, total_frames),
                estimate=truth + 0.05 * math.sin(0.1 * tau + seed),
                sigma=0.01,
                truth=truth,
                history=[truth + 0.05 * math.cos(0.05 * (tau - j)) for j in range(min(i + 1, 32))],
                active_terms=default_active_terms("statmech"),
            )
        )
    return out


# ── Dispatch ──────────────────────────────────────────────────────


def synthesize_frames(
    domain: str,
    *,
    total_frames: int = 60,
    seed: int = 0,
    formula_variant: str = "F1",
    couplings: dict[str, float] | None = None,
    model_domain: str | None = None,
    is_learned_hamiltonian: bool = False,
    provenance_warning: str | None = None,
    tau_max: float | None = None,
) -> list[BaseFrame]:
    """Generate ``total_frames`` synthetic frames for ``domain``."""
    common = {"total_frames": total_frames, "seed": seed, "tau_max": tau_max}
    if domain == "cosmology":
        return list(cosmology_frames(formula_variant=formula_variant, couplings=couplings, **common))
    if domain == "chemistry":
        return list(chemistry_frames(**common))
    if domain == "condmat":
        return list(condmat_frames(**common))
    if domain == "hep":
        return list(hep_frames(**common))
    if domain == "nuclear":
        return list(nuclear_frames(model_domain=model_domain or "1+1D_toy", **common))
    if domain == "amo":
        return list(amo_frames(**common))
    if domain == "gravity":
        return list(
            gravity_frames(
                is_learned_hamiltonian=is_learned_hamiltonian,
                provenance_warning=provenance_warning,
                model_domain=model_domain or "toy_SYK_1+1D",
                **common,
            )
        )
    if domain == "statmech":
        return list(statmech_frames(**common))
    raise ValueError(f"unknown domain {domain!r}; valid: {list(DOMAINS)}")


def synthesize_manifest(
    *,
    domain: str,
    run_id: str,
    total_frames: int = 60,
    seed: int = 0,
    formula_variant: str | None = None,
) -> VisualizationManifest:
    """Manifest paired with :func:`synthesize_frames` output."""
    return VisualizationManifest(
        run_id=run_id,
        domain=domain,  # type: ignore[arg-type]
        frame_count=total_frames,
        formula_variant=formula_variant,
        bake_uri=None,
        metadata={"phases": list(progression(domain)), "seed": seed, "synthetic": True},
    )


def build_synthetic_timeline(
    domain: str,
    run_id: str,
    *,
    n_frames: int = 60,
    tau_max: float = 60.0,
    couplings: dict[str, float] | None = None,
    model_domain: str = "1+1D_toy",
    is_learned_hamiltonian: bool = False,
    provenance_warning: str | None = None,
    formula_variant: str = "F1",
) -> VisualizationTimeline:
    """A :class:`VisualizationTimeline` of synthetic frames for ``run_id``."""
    frames = synthesize_frames(
        domain,
        total_frames=n_frames,
        seed=stable_seed(run_id),
        formula_variant=formula_variant,
        couplings=couplings,
        model_domain=model_domain if domain in {"nuclear", "gravity"} else None,
        is_learned_hamiltonian=is_learned_hamiltonian,
        provenance_warning=provenance_warning,
        tau_max=tau_max,
    )
    timeline = VisualizationTimeline(
        run_id=run_id,
        domain=domain,  # type: ignore[arg-type]
        synthetic=True,
        formula_variant=formula_variant if domain == "cosmology" else None,
    )
    for frame in frames:
        frame.provenance_ref = run_id
        timeline.append(frame)
    return timeline


def stream_frames(timeline: VisualizationTimeline) -> Iterable[BaseFrame]:
    yield from timeline.parsed_frames()
