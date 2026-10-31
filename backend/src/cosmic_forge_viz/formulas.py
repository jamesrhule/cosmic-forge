"""Cosmology F1-F7 active-terms classifier (PROMPT 7 v2 §PART B).

The UCGLE-F1 visualisation panels colour each frame by the
formulas (F1-F7) that are 'active' at that instant. Each formula
encodes a coupling between scalar / Gauss-Bonnet / Chern-Simons
terms; the rule lives here so the baker tags every cosmology frame
with the matching ``active_terms`` list.

Other domains (chemistry / condmat / etc.) leave ``active_terms``
empty unless they implement their own classifier (none required by
the v2 spec).
"""

from __future__ import annotations

from typing import Iterable


# Each rule keys an F-id to a predicate that fires when the named
# coupling is non-trivial. Couplings come from the run config
# (``run["config"]["couplings"]``).
FormulaId = str


def active_formulas_for_couplings(
    couplings: dict[str, float] | None,
) -> list[FormulaId]:
    """Return the F-ids active for a given couplings dict.

    Cosmology runs ship a ``couplings`` block with at least
    ``alpha_GB`` (Gauss-Bonnet) and ``beta_CS`` (Chern-Simons).
    Subsequent F-ids fire on derived combinations.
    """
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


def formulas_at_phase(
    phase: str,
    couplings: dict[str, float] | None,
) -> list[FormulaId]:
    """Subset of :func:`active_formulas_for_couplings` keyed on phase.

    During pure inflation (no anomaly drive) F2 / F4 are dormant.
    Reheating activates the full coupling stack.
    """
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
