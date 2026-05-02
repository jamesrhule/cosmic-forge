"""Synthetic visualisation-frame generator (PROMPT 7 v2 §PART B).

Used for:
  - the bundled ``public/fixtures/visualizations/<id>.json`` snapshots,
  - tests that exercise the schema / baker / server without
    spinning up a real qfull-* run.

The numbers are physical-shape-correct (right magnitudes, smooth
trajectories) but NOT physically meaningful — the audit gate for
real numerics is the per-domain S-* test suite.
"""

from __future__ import annotations

import math
from typing import Iterable

from .formulas import formulas_at_phase
from .phases import phase_for_tau
from .schema import (
    AmoFrame,
    BaseFrame,
    ChemistryFrame,
    CondmatFrame,
    CosmologyFrame,
    CosmologyModeBlock,
    HepFrame,
    NuclearFrame,
    ParticleObservableEntry,
    VisualizationTimeline,
)


# ── Per-domain frame builders ───────────────────────────────────────


def _cosmology_frame(
    tau: float,
    tau_max: float,
    *,
    couplings: dict[str, float] | None = None,
) -> CosmologyFrame:
    phase = phase_for_tau("cosmology", tau, tau_max)
    active = formulas_at_phase(phase, couplings)
    n_modes = 12
    ks = [0.1 * (i + 1) for i in range(n_modes)]
    omega_re = [
        0.5 * k * math.cos(0.3 * tau + i * 0.2)
        for i, k in enumerate(ks)
    ]
    omega_im = [-0.05 * k for k in ks]
    sgwb = [
        1e-12 * math.exp(-((math.log(k) - tau / 50.0) ** 2))
        for k in ks
    ]
    return CosmologyFrame(
        tau=tau, phase=phase, active_terms=active,
        modes=CosmologyModeBlock(k=ks, omega_re=omega_re, omega_im=omega_im),
        B_plus=[0.5 * math.cos(0.1 * tau + i) for i in range(8)],
        B_minus=[0.5 * math.sin(0.1 * tau + i) for i in range(8)],
        sgwb=sgwb,
        anomaly=1e-9 * math.tanh(tau / 30.0),
        lepton_flow=1e-10 * math.sin(0.05 * tau),
    )


def _chemistry_frame(tau: float, tau_max: float) -> ChemistryFrame:
    phase = phase_for_tau("chemistry", tau, tau_max)
    n_orb = 8
    orbitals = [
        2.0 * math.exp(-0.1 * abs(i - 3) - 0.01 * tau)
        for i in range(n_orb)
    ]
    energies = [
        -1.137 - 1e-3 * math.exp(-tau / 5.0)
        for _ in range(int(tau) + 1)
    ]
    slater = [
        [0.1 * math.exp(-abs(i - j) - 0.05 * tau) for j in range(n_orb)]
        for i in range(n_orb)
    ]
    return ChemistryFrame(
        tau=tau, phase=phase, orbitals=orbitals,
        energy_convergence=energies, slater=slater,
    )


def _condmat_frame(tau: float, tau_max: float) -> CondmatFrame:
    phase = phase_for_tau("condmat", tau, tau_max)
    L = 8
    sites = [[float(i % L), float(i // L)] for i in range(L * L)]
    bonds = [
        1.0 + 0.1 * math.cos(0.1 * tau + 0.3 * i)
        for i in range(2 * L * (L - 1))
    ]
    otoc = [
        [0.1 * math.tanh(tau / (i + 1) - 0.05 * j) for j in range(L)]
        for i in range(8)
    ]
    spectral = [
        [math.exp(-((kx - 4) ** 2 + (omega - 4) ** 2) / 4.0)
         for omega in range(8)]
        for kx in range(8)
    ]
    return CondmatFrame(
        tau=tau, phase=phase, lattice_sites=sites,
        bond_strengths=bonds, otoc=otoc, spectral=spectral,
    )


def _hep_frame(tau: float, tau_max: float) -> HepFrame:
    phase = phase_for_tau("hep", tau, tau_max)
    L = 6
    plaquettes = [
        0.1 * math.cos(0.1 * tau + 0.3 * p) for p in range(L * (L - 1))
    ]
    cond = 0.05 * math.tanh(tau / 10.0)
    string_t = 0.5 * (1.0 - math.exp(-tau / 10.0))
    particle_obs = {
        "chiral_condensate": ParticleObservableEntry(
            value=cond, unit="dimensionless",
            uncertainty=0.01, status="ok",
            notes="finite-size 1/sqrt(L) heuristic on the ED ground state.",
        ),
        "string_tension": ParticleObservableEntry(
            value=string_t, unit="g_squared_per_lattice_spacing",
            uncertainty=None, status="ok",
            notes="Wilson-loop scaling proxy.",
        ),
        "anomaly_density": ParticleObservableEntry(
            value=0.001 * math.sin(0.2 * tau), unit="dimensionless",
            uncertainty=1.0 / L, status="ok",
            notes="ΔN/L from staggered occupancy minus the half-filled vacuum baseline.",
        ),
    }
    return HepFrame(
        tau=tau, phase=phase, plaquettes=plaquettes,
        chiral_condensate=cond, string_tension=string_t,
        particle_obs=particle_obs,
    )


def _nuclear_frame(
    tau: float, tau_max: float, *, model_domain: str = "1+1D_toy",
) -> NuclearFrame:
    phase = phase_for_tau("nuclear", tau, tau_max)
    n_shell = 8
    occ = [
        2.0 / (1.0 + math.exp(-(3 - i) + 0.1 * tau))
        for i in range(n_shell)
    ]
    return NuclearFrame(
        tau=tau, phase=phase, shell_occupation=occ,
        lnv_tracker=1.0 if tau > tau_max / 2.0 else 0.0,
        model_domain=model_domain,  # type: ignore[arg-type]
    )


def _amo_frame(tau: float, tau_max: float) -> AmoFrame:
    phase = phase_for_tau("amo", tau, tau_max)
    N = 5
    positions = [
        [float(i) * 5.0, 0.0, 0.0] for i in range(N)
    ]
    blockade = [4.0 + 0.1 * math.sin(0.1 * tau + i) for i in range(N)]
    correlations = [
        [math.exp(-abs(i - j) - 0.05 * tau) for j in range(N)]
        for i in range(N)
    ]
    return AmoFrame(
        tau=tau, phase=phase, atom_positions=positions,
        blockade_radii=blockade, correlations=correlations,
    )


# ── Timeline assembly ──────────────────────────────────────────────


_BUILDERS = {
    "cosmology": _cosmology_frame,
    "chemistry": _chemistry_frame,
    "condmat": _condmat_frame,
    "hep": _hep_frame,
    "nuclear": _nuclear_frame,
    "amo": _amo_frame,
}


def build_synthetic_timeline(
    domain: str,
    run_id: str,
    *,
    n_frames: int = 60,
    tau_max: float = 60.0,
    couplings: dict[str, float] | None = None,
    model_domain: str = "1+1D_toy",
) -> VisualizationTimeline:
    """Assemble a v2 timeline for the given domain / run_id.

    Cosmology runs accept a ``couplings`` dict; the
    F1-F7 active-terms list lands on each frame.
    Nuclear runs accept ``model_domain`` so the visualizer renders
    the right caveat banner.
    """
    builder = _BUILDERS.get(domain)
    if builder is None:
        msg = f"Unknown domain: {domain!r}"
        raise KeyError(msg)
    timeline = VisualizationTimeline(run_id=run_id, domain=domain)  # type: ignore[arg-type]
    step = tau_max / max(1, n_frames - 1)
    for i in range(n_frames):
        tau = i * step
        if domain == "cosmology":
            frame = builder(tau, tau_max, couplings=couplings)  # type: ignore[arg-type]
        elif domain == "nuclear":
            frame = builder(tau, tau_max, model_domain=model_domain)  # type: ignore[arg-type]
        else:
            frame = builder(tau, tau_max)
        frame.provenance_ref = run_id
        timeline.append(frame)
    return timeline


def stream_frames(
    timeline: VisualizationTimeline,
) -> Iterable[BaseFrame]:
    """Yield typed frames (useful for WS / SSE generators)."""
    yield from timeline.parsed_frames()
