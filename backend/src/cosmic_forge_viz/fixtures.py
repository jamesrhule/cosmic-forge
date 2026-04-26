"""Synthetic frame generators.

Used by the test suite, the CLI's `--demo` mode, and the visualizer
empty-state fallback. Output is deterministic for a given (domain,
seed, total_frames) tuple so tests can pin against specific values.
"""

from __future__ import annotations

import math
import random
from typing import Iterable

from cosmic_forge_viz.formulas import (
    active_terms_for_variant,
    default_active_terms,
)
from cosmic_forge_viz.phases import phase_for, progression
from cosmic_forge_viz.schema import (
    AmoFrame,
    BaseFrame,
    ChemistryFrame,
    CondmatFrame,
    CosmologyFrame,
    HepFrame,
    NuclearFrame,
    VisualizationManifest,
)


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


# ---------------------------------------------------------------------------
# Per-domain generators
# ---------------------------------------------------------------------------


def cosmology_frames(
    *,
    total_frames: int = 60,
    formula_variant: str = "F1",
    seed: int = 0,
    n_modes: int = 12,
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
        frame = CosmologyFrame(
            tau=float(i),
            phase=phase,
            t_cosmic_seconds=i * 1e-32,
            modes=modes,
            B_plus=math.exp(-((i - total_frames / 2) ** 2) / (2 * total_frames)),
            B_minus=0.5 * math.exp(-((i - total_frames / 2) ** 2) / (2 * total_frames)),
            xi_dot_H=0.4 if in_window else 0.05,
            active_terms=active_terms_for_variant(
                formula_variant,
                phase=phase,
                in_tachyonic_window=in_window,
            ),
            provenance_ref=None,
        )
        out.append(frame)
    return out


def chemistry_frames(
    *, total_frames: int = 60, seed: int = 0, n_orbitals: int = 8
) -> list[ChemistryFrame]:
    rng = _rng(seed)
    energies: list[float] = []
    base = -1.5
    for _ in range(total_frames):
        # SCF-like exponential convergence to a target.
        last = energies[-1] if energies else 0.0
        next_val = last + (base - last) * 0.18 + rng.uniform(-0.005, 0.005)
        energies.append(next_val)

    out: list[ChemistryFrame] = []
    for i in range(total_frames):
        phase = phase_for("chemistry", i, total_frames)
        orbitals = [
            {
                "index": o,
                "energy_hartree": -1.0 / (o + 1) + rng.uniform(-0.01, 0.01),
                "occupation": 2.0 if o < n_orbitals // 2 else 0.0,
                "coefficients": [],
            }
            for o in range(n_orbitals)
        ]
        out.append(
            ChemistryFrame(
                tau=float(i),
                phase=phase,
                iteration=i,
                orbitals=orbitals,
                energy_convergence=list(energies[: i + 1]),
                slater_determinants=[
                    {
                        "label": f"|HF⟩",
                        "weight": 0.92 - 0.001 * i,
                        "occupations": [1] * (n_orbitals // 2)
                        + [0] * (n_orbitals - n_orbitals // 2),
                    },
                    {
                        "label": f"|S1⟩",
                        "weight": max(0.0, 0.07 + 0.0008 * i),
                        "occupations": [1] * (n_orbitals // 2 - 1)
                        + [0, 1]
                        + [0] * (n_orbitals - n_orbitals // 2 - 1),
                    },
                ],
                hamiltonian_terms=[
                    {"label": "h_pq", "coefficient": -0.5, "operator": "a†_p a_q"},
                    {"label": "g_pqrs", "coefficient": 0.25, "operator": "a†_p a†_q a_s a_r"},
                ],
                active_terms=default_active_terms("chemistry"),
            )
        )
    return out


def condmat_frames(
    *, total_frames: int = 60, seed: int = 0, lattice: int = 6
) -> list[CondmatFrame]:
    rng = _rng(seed)
    sites = [
        {"index": x * lattice + y, "x": float(x), "y": float(y), "z": 0.0, "spin": rng.choice([-1.0, 1.0])}
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
        # Light-cone OTOC: distance grows linearly with time.
        n_t, n_d = 12, lattice
        intensity = [
            [
                math.exp(-((d - 0.4 * t) ** 2) / 4) * (0.4 + 0.6 * (i / total_frames))
                for d in range(n_d)
            ]
            for t in range(n_t)
        ]
        # Mutate one bond per frame for animation.
        for b in bonds:
            b["strength"] = 1.0 + 0.2 * math.sin(0.1 * i + 0.3 * b["a"])
        out.append(
            CondmatFrame(
                tau=float(i),
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


def hep_frames(*, total_frames: int = 60, seed: int = 0, lattice: int = 4) -> list[HepFrame]:
    rng = _rng(seed)
    out: list[HepFrame] = []
    for i in range(total_frames):
        phase = phase_for("hep", i, total_frames)
        plaquettes = [
            {
                "cell": (x, y, z),
                "flux": rng.uniform(-1, 1),
                "energy": 0.5 + 0.1 * math.sin(0.1 * i + x + y + z),
            }
            for x in range(lattice)
            for y in range(lattice)
            for z in range(lattice)
        ]
        out.append(
            HepFrame(
                tau=float(i),
                phase=phase,
                plaquettes=plaquettes,
                chiral_condensate=-0.3 + 0.05 * math.sin(0.05 * i),
                string_tension=0.25 - 0.001 * i,
                active_terms=default_active_terms("hep"),
            )
        )
    return out


def nuclear_frames(*, total_frames: int = 60, seed: int = 0) -> list[NuclearFrame]:
    rng = _rng(seed)
    shells = ["1s1/2", "1p3/2", "1p1/2", "1d5/2", "2s1/2", "1d3/2"]
    out: list[NuclearFrame] = []
    for i in range(total_frames):
        phase = phase_for("nuclear", i, total_frames)
        out.append(
            NuclearFrame(
                tau=float(i),
                phase=phase,
                shell_occupation=[
                    {
                        "shell": s,
                        "n": min(2 * (k + 1), 8) - 0.05 * i + rng.uniform(-0.1, 0.1),
                        "energy_MeV": -8.0 + 1.5 * k,
                    }
                    for k, s in enumerate(shells)
                ],
                lnv_tracker={
                    "delta_L": 2.0 if i > total_frames // 2 else 0.0,
                    "delta_B": 0.0,
                    "rate": 1e-26 * (1 + 0.01 * i),
                },
                active_terms=default_active_terms("nuclear"),
            )
        )
    return out


def amo_frames(*, total_frames: int = 60, seed: int = 0, n_atoms: int = 16) -> list[AmoFrame]:
    rng = _rng(seed)
    positions = [
        {
            "index": k,
            "x": (k % 4) * 5.0,
            "y": (k // 4) * 5.0,
            "z": 0.0,
            "rydberg": False,
        }
        for k in range(n_atoms)
    ]
    out: list[AmoFrame] = []
    for i in range(total_frames):
        phase = phase_for("amo", i, total_frames)
        # Promote a fraction of atoms to Rydberg state during rydberg phase.
        for k, p in enumerate(positions):
            p["rydberg"] = phase == "rydberg" and (k + i) % 3 == 0
        out.append(
            AmoFrame(
                tau=float(i),
                phase=phase,
                atom_positions=[dict(p) for p in positions],
                blockade_radii=[
                    {"atom": k, "r_blockade": 6.0 + rng.uniform(-0.2, 0.2)}
                    for k in range(n_atoms)
                ],
                correlations={
                    "pairs": [(k, (k + 1) % n_atoms) for k in range(n_atoms)],
                    "g2": [0.5 + 0.4 * math.sin(0.1 * i + k) for k in range(n_atoms)],
                },
                active_terms=default_active_terms("amo"),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Top-level dispatch
# ---------------------------------------------------------------------------


def synthesize_frames(
    domain: str,
    *,
    total_frames: int = 60,
    seed: int = 0,
    formula_variant: str = "F1",
) -> list[BaseFrame]:
    """Generate `total_frames` synthetic frames for `domain`."""
    if domain == "cosmology":
        return list(
            cosmology_frames(
                total_frames=total_frames,
                seed=seed,
                formula_variant=formula_variant,
            )
        )
    if domain == "chemistry":
        return list(chemistry_frames(total_frames=total_frames, seed=seed))
    if domain == "condmat":
        return list(condmat_frames(total_frames=total_frames, seed=seed))
    if domain == "hep":
        return list(hep_frames(total_frames=total_frames, seed=seed))
    if domain == "nuclear":
        return list(nuclear_frames(total_frames=total_frames, seed=seed))
    if domain == "amo":
        return list(amo_frames(total_frames=total_frames, seed=seed))
    raise ValueError(f"unknown domain {domain!r}")


def synthesize_manifest(
    *,
    domain: str,
    run_id: str,
    total_frames: int = 60,
    seed: int = 0,
    formula_variant: str | None = None,
) -> VisualizationManifest:
    """Manifest paired with `synthesize_frames(...)` output."""
    return VisualizationManifest(
        run_id=run_id,
        domain=domain,  # type: ignore[arg-type]
        frame_count=total_frames,
        formula_variant=formula_variant,
        bake_uri=None,
        metadata={
            "phases": list(progression(domain)),
            "seed": seed,
            "synthetic": True,
        },
    )
