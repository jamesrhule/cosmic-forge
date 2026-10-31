"""Particle-research observable builder (PROMPT 5 v2).

v2 mandates that every HEP run carries a ``particle_obs`` dict
keyed by observable name with ``value`` / ``unit`` / ``uncertainty``
entries — the format the leaderboard + frontend consume so a
downstream lattice-QCD comparison sees identical schema across
fixtures.

Schwinger 1+1D supplies the three canonical observables:
  - chiral_condensate (dimensionless, normalised by L)
  - string_tension (gauge-coupling units, derived from electric-
    field energy density)
  - anomaly_density (dimensionless; derived from the Σ (-1)^n n_n
    deviation from the half-filled vacuum baseline)

z_N / SU(2) toy fixtures emit the same three keys with
``value=None`` + ``status='unavailable'`` so the schema stays
uniform without forging numbers the kernel can't compute.
"""

from __future__ import annotations

import math
from typing import Any, TypedDict

from .manifest import HEPProblem


class ParticleObservable(TypedDict, total=False):
    """One named observable's value + units + uncertainty band."""

    value: float | None
    unit: str
    uncertainty: float | None
    status: str  # "ok" | "unavailable"
    notes: str


_OBSERVABLE_UNITS: dict[str, str] = {
    "chiral_condensate": "dimensionless",
    "string_tension": "g_squared_per_lattice_spacing",
    "anomaly_density": "dimensionless",
}


def build_particle_obs(
    problem: HEPProblem,
    classical_metadata: dict[str, Any],
) -> dict[str, ParticleObservable]:
    """Project the classical kernel's metadata into the v2 schema.

    ``classical_metadata`` is the dict :func:`compute_reference`
    returns under ``metadata`` (containing keys like
    ``chiral_condensate`` and ``total_n_expected``). We never
    fabricate values — keys whose source isn't present in the
    metadata are emitted as ``status='unavailable'`` so the
    frontend renders an empty cell rather than a stale number.
    """
    out: dict[str, ParticleObservable] = {}
    if problem.kind == "schwinger":
        cond = classical_metadata.get("chiral_condensate")
        L = classical_metadata.get("L") or 1
        out["chiral_condensate"] = ParticleObservable(
            value=float(cond) if cond is not None else None,
            unit=_OBSERVABLE_UNITS["chiral_condensate"],
            uncertainty=(1.0 / math.sqrt(max(L, 1))) if cond is not None else None,
            status="ok" if cond is not None else "unavailable",
            notes="Finite-size 1/sqrt(L) heuristic on the ED ground state.",
        )
        # String tension proxy: g^2 / lattice_spacing × theta-energy
        # contribution. Today's classical kernel returns this
        # implicitly as the additive theta-term; we expose it.
        g = classical_metadata.get("g")
        theta = classical_metadata.get("theta")
        if g is not None and theta is not None:
            value = 0.5 * (theta ** 2) * float(g) ** 2
            out["string_tension"] = ParticleObservable(
                value=value,
                unit=_OBSERVABLE_UNITS["string_tension"],
                uncertainty=None,
                status="ok",
                notes=(
                    "Leading-order θ² g² approximation; full Wilson "
                    "loop scaling lands with the SC-ADAPT-VQE path."
                ),
            )
        else:
            out["string_tension"] = _unavailable("string_tension")

        total_n = classical_metadata.get("total_n_expected")
        vacuum = classical_metadata.get("vacuum_q_total")
        if total_n is not None and vacuum is not None:
            density = (float(total_n) - float(vacuum)) / max(L, 1)
            out["anomaly_density"] = ParticleObservable(
                value=density,
                unit=_OBSERVABLE_UNITS["anomaly_density"],
                uncertainty=1.0 / max(L, 1),
                status="ok",
                notes=(
                    "ΔN / L from staggered occupancy minus the "
                    "half-filled vacuum baseline."
                ),
            )
        else:
            out["anomaly_density"] = _unavailable("anomaly_density")
        return out

    # zN / SU(2) toys: keep schema uniform but mark the bands as
    # unavailable until the dedicated kernels land.
    for name in ("chiral_condensate", "string_tension", "anomaly_density"):
        out[name] = _unavailable(name)
    return out


def _unavailable(name: str) -> ParticleObservable:
    return ParticleObservable(
        value=None,
        unit=_OBSERVABLE_UNITS.get(name, "dimensionless"),
        uncertainty=None,
        status="unavailable",
        notes="kernel does not yet emit this observable.",
    )
