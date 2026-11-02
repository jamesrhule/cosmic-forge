"""Active-term rules for visualization frames.

Two complementary views of the UCGLE F1–F7 formula family:

* ``active_terms_for_variant`` — the Lagrangian term IDs of a given
  formula variant that are active in a given phase (formula overlay).
* ``active_formulas_for_couplings`` / ``formulas_at_phase`` — which
  F-variants are switched on by a coupling set (from a run manifest).

Other domains get a default Hamiltonian-term list from the registry.
"""

from __future__ import annotations

from collections.abc import Iterable

# ── Term IDs per cosmology variant ────────────────────────────────

_COSMOLOGY_TERMS: dict[str, tuple[str, ...]] = {
    "F1": ("kinetic", "potential", "GB_window", "anomaly", "gravitino"),
    "F2": ("kinetic", "potential", "nieh_yan", "anomaly"),
    "F3": ("kinetic", "potential", "GB_window", "anomaly", "kk_tower"),
    "F4": ("kinetic", "potential", "GB_window", "anomaly", "axionic_coupling"),
    "F5": ("kinetic", "potential", "GB_window", "anomaly", "resonance"),
    "F6": ("kinetic", "potential", "GB_window", "anomaly", "phantom_branch"),
    "F7": (
        "kinetic",
        "potential",
        "GB_window",
        "anomaly",
        "kk_tower",
        "resonance",
        "phantom_branch",
    ),
}


def active_terms_for_variant(
    variant: str,
    *,
    phase: str | None = None,
    in_tachyonic_window: bool = False,
) -> list[str]:
    """Active term IDs for a cosmology frame of formula ``variant``."""
    base = list(_COSMOLOGY_TERMS.get(variant, _COSMOLOGY_TERMS["F1"]))
    if phase == "inflation" and not in_tachyonic_window:
        base = [t for t in base if t != "GB_window"]
    if phase == "radiation":
        base = [t for t in base if t not in {"GB_window", "anomaly"}]
    if phase == "sphaleron":
        base = [t for t in base if t in {"kinetic", "anomaly"}]
    return base


# ── F-variants switched on by a coupling set ──────────────────────

FormulaId = str


def active_formulas_for_couplings(
    couplings: dict[str, float] | None,
) -> list[FormulaId]:
    """F-ids active for a couplings dict (``alpha_GB``, ``beta_CS``, ``nieh_yan``)."""
    c = couplings or {}
    a_gb = float(c.get("alpha_GB", 0.0))
    b_cs = float(c.get("beta_CS", 0.0))
    nieh_yan = float(c.get("nieh_yan", 0.0))
    out: list[str] = []
    if a_gb != 0.0:
        out.append("F1")
    if b_cs != 0.0:
        out.append("F2")
    if a_gb != 0.0 and b_cs != 0.0:
        out.append("F3")
    if nieh_yan != 0.0:
        out.append("F4")
    if a_gb != 0.0 and abs(b_cs) > 1.0:
        out.append("F5")
    if a_gb != 0.0 and b_cs != 0.0 and nieh_yan != 0.0:
        out.append("F6")
    if a_gb != 0.0 and b_cs != 0.0 and abs(a_gb * b_cs) > 1e-3:
        out.append("F7")
    return out


# The leptogenesis epoch of the original phase vocabulary corresponds to
# the sphaleron phase of the frontend vocabulary.
_PHASE_ALIASES = {"sphaleron": "leptogenesis"}


def formulas_at_phase(
    phase: str,
    couplings: dict[str, float] | None,
) -> list[FormulaId]:
    """Subset of :func:`active_formulas_for_couplings` active in ``phase``."""
    phase = _PHASE_ALIASES.get(phase, phase)
    base = active_formulas_for_couplings(couplings)
    if phase == "inflation":
        return [f for f in base if f not in {"F2", "F4", "F6"}]
    if phase == "reheating":
        return base
    if phase == "leptogenesis":
        return [f for f in base if f != "F1"]
    return base


def all_known_formula_ids() -> Iterable[str]:
    return ("F1", "F2", "F3", "F4", "F5", "F6", "F7")


# ── Cross-domain registry ─────────────────────────────────────────

_DOMAIN_DEFAULT_TERMS: dict[str, tuple[str, ...]] = {
    "chemistry": ("one_body", "two_body"),
    "condmat": ("hopping", "interaction", "field"),
    "hep": ("kinetic", "plaquette", "fermion_mass"),
    "nuclear": ("pairing", "spin_orbit"),
    "amo": ("rabi", "vdw_blockade"),
    "gravity": ("syk_coupling",),
    "statmech": ("estimator",),
}


def default_active_terms(domain: str) -> list[str]:
    return list(_DOMAIN_DEFAULT_TERMS.get(domain, ()))


def all_known_terms() -> set[str]:
    """Union of every term ID the registry references (incl. F-ids)."""
    out: set[str] = set(all_known_formula_ids())
    for terms in _COSMOLOGY_TERMS.values():
        out.update(terms)
    for terms in _DOMAIN_DEFAULT_TERMS.values():
        out.update(terms)
    return out


def assert_terms_known(terms: Iterable[str]) -> None:
    known = all_known_terms()
    bad = [t for t in terms if t not in known]
    if bad:
        raise ValueError(f"unknown term IDs: {bad}; known: {sorted(known)}")
