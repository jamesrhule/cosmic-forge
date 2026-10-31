"""Particle-research observable builder (PROMPT 5 v2 — nuclear domain).

Mirrors :mod:`qfull_hep.particle_obs`. Every nuclear run carries a
``particle_obs`` dict so the leaderboard + frontend treat HEP and
nuclear results with the same schema.

Per-kind observables:
  - ``zero_nu_bb_toy``  → ``lnv_signature``, ``occupancy_imbalance``
  - ``ncsm_matrix_element`` → ``antisymmetry_residual`` (operator-
    valued sanity); ``e0`` energy band
  - ``effective_hamiltonian`` → ``mixing_amplitude``, ``energy_gap``
    (drives the heavy-neutrino / sterile-oscillation hypothesis
    audit)

Each observable carries a ``unit`` tag the visualizer uses to
render the right axis label.
"""

from __future__ import annotations

import math
from typing import Any, TypedDict

from .manifest import NuclearProblem


class ParticleObservable(TypedDict, total=False):
    value: float | None
    unit: str
    uncertainty: float | None
    status: str
    notes: str


_OBSERVABLE_UNITS: dict[str, str] = {
    "lnv_signature": "dimensionless",
    "occupancy_imbalance": "dimensionless",
    "antisymmetry_residual": "matrix_element",
    "mixing_amplitude": "probability",
    "energy_gap": "natural_units",
}


def build_particle_obs(
    problem: NuclearProblem,
    classical_metadata: dict[str, Any],
) -> dict[str, ParticleObservable]:
    out: dict[str, ParticleObservable] = {}

    if problem.kind == "zero_nu_bb_toy":
        occ = classical_metadata.get("occupancy")
        L = classical_metadata.get("L") or 1
        if occ is not None:
            imbalance = abs(float(occ) - 0.5)
            out["occupancy_imbalance"] = ParticleObservable(
                value=imbalance,
                unit=_OBSERVABLE_UNITS["occupancy_imbalance"],
                uncertainty=1.0 / math.sqrt(max(L, 1)),
                status="ok",
                notes="|⟨n⟩/L − 1/2| from ED ground state.",
            )
            # Toy LNV signature: nonzero imbalance after ED → signal
            # the lepton-number-violation toy is qualitatively present.
            out["lnv_signature"] = ParticleObservable(
                value=1.0 if imbalance > 1e-3 else 0.0,
                unit=_OBSERVABLE_UNITS["lnv_signature"],
                uncertainty=None,
                status="ok",
                notes=(
                    "Qualitative LNV indicator: 1 if ground-state "
                    "occupancy deviates from half-filling."
                ),
            )
        else:
            for k in ("lnv_signature", "occupancy_imbalance"):
                out[k] = _unavailable(k)
        return out

    if problem.kind == "ncsm_matrix_element":
        residual = classical_metadata.get("antisymmetry_residual")
        out["antisymmetry_residual"] = ParticleObservable(
            value=float(residual) if residual is not None else None,
            unit=_OBSERVABLE_UNITS["antisymmetry_residual"],
            uncertainty=None,
            status="ok" if residual is not None else "unavailable",
            notes="max|M + Mᵀ| of the synthetic 2-body operator.",
        )
        return out

    if problem.kind == "effective_hamiltonian":
        amp = classical_metadata.get("mixing_amplitude")
        gap = classical_metadata.get("energy_gap")
        out["mixing_amplitude"] = ParticleObservable(
            value=float(amp) if amp is not None else None,
            unit=_OBSERVABLE_UNITS["mixing_amplitude"],
            uncertainty=None,
            status="ok" if amp is not None else "unavailable",
            notes="|⟨active|ψ₀⟩|² for the two-state effective model.",
        )
        out["energy_gap"] = ParticleObservable(
            value=float(gap) if gap is not None else None,
            unit=_OBSERVABLE_UNITS["energy_gap"],
            uncertainty=None,
            status="ok" if gap is not None else "unavailable",
            notes="E₁ − E₀ in natural units of the toy Hamiltonian.",
        )
        return out

    return out


def _unavailable(name: str) -> ParticleObservable:
    return ParticleObservable(
        value=None,
        unit=_OBSERVABLE_UNITS.get(name, "dimensionless"),
        uncertainty=None,
        status="unavailable",
        notes="kernel did not emit this observable.",
    )
