"""UCGLE F1–F7 active-terms rules + a small registry for other domains.

Each cosmology variant exposes a *family* of Hamiltonian / Lagrangian
terms. The visualizer panel surface highlights the terms that are
"active" at a given frame: the formula registry encodes that mapping
once and is consumed by both the bake step (which stamps each frame's
`active_terms` list) and the formula overlay (which annotates the
LaTeX with phase-aware highlights).
"""

from __future__ import annotations

from typing import Iterable

# ---------------------------------------------------------------------------
# UCGLE F1–F7
# ---------------------------------------------------------------------------

# The full union of cosmology term IDs the formula overlay knows how to
# render. New variants must use IDs from this set or extend it
# atomically alongside the frontend's `formulaTermIds` map.
_COSMOLOGY_TERMS = {
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
    """Return the active term IDs for a cosmology frame.

    Phase / window context is used to suppress terms that are
    structurally present in the variant but inactive at this frame
    (e.g. `GB_window` only applies during the GB window itself).
    """
    base = list(_COSMOLOGY_TERMS.get(variant, _COSMOLOGY_TERMS["F1"]))
    if phase == "inflation" and not in_tachyonic_window:
        base = [t for t in base if t != "GB_window"]
    if phase == "radiation":
        base = [t for t in base if t not in {"GB_window", "anomaly"}]
    if phase == "sphaleron":
        # Anomaly + kinetic dominate; GB window has closed.
        base = [t for t in base if t in {"kinetic", "anomaly"}]
    return base


# ---------------------------------------------------------------------------
# Cross-domain registry
# ---------------------------------------------------------------------------

# Defaults the bake step uses when a domain doesn't supply its own
# `active_terms` list. Other domains' frames typically pass a richer,
# per-frame term list driven by their own Hamiltonian registry.
_DOMAIN_DEFAULT_TERMS: dict[str, tuple[str, ...]] = {
    "chemistry": ("one_body", "two_body"),
    "condmat": ("hopping", "interaction", "field"),
    "hep": ("kinetic", "plaquette", "fermion_mass"),
    "nuclear": ("pairing", "spin_orbit"),
    "amo": ("rabi", "vdw_blockade"),
}


def default_active_terms(domain: str) -> list[str]:
    """Domain-specific default term list when nothing else is known."""
    return list(_DOMAIN_DEFAULT_TERMS.get(domain, ()))


def all_known_terms() -> set[str]:
    """Union of every term ID the registry references."""
    out: set[str] = set()
    for terms in _COSMOLOGY_TERMS.values():
        out.update(terms)
    for terms in _DOMAIN_DEFAULT_TERMS.values():
        out.update(terms)
    return out


def assert_terms_known(terms: Iterable[str]) -> None:
    """Sanity check used by tests when validating fixtures."""
    known = all_known_terms()
    bad = [t for t in terms if t not in known]
    if bad:
        raise ValueError(f"unknown term IDs: {bad}; known: {sorted(known)}")
