"""Natural inflation: slow-roll closed forms and the Kawai–Kim benchmark.

Units: reduced Planck units throughout (M_Pl = 2.4352e18 GeV = 1; the
LEDGER's "2.44e18" is the same constant to three figures). GeV appears
only at the API/UI boundary.

Potential (M2 kind ``natural``, keys ``f_a`` and ``Lambda``)::

    V(φ) = Λ⁴ (1 − cos(φ/f_a)).

Kawai & Kim (arXiv:1702.07689) write V = Λ⁴(1 ± cos φ/f_a). The two signs
are the same potential under φ → φ + π f_a, so M2's minus sign loses
nothing: inflation runs on 0 < φ < π f_a and the field rolls towards the
minimum at φ = 0.

Published benchmark (LEDGER, JAMES DECISION 11, following the paper):
f_a = 8.7 M_Pl, Λ fixed by A_s = 2.207 × 10⁻⁹ at N_e = 60 e-folds before
the end of inflation, giving m = Λ²/f_a ≈ 5 × 10⁻⁶ M_Pl.

Slow-roll derivation (x ≡ φ/f_a)
---------------------------------
    ε(φ) = ½ (V′/V)² = cot²(x/2) / (2 f_a²),
    end of inflation, ε(φ_end) = 1:   φ_end = 2 f_a arctan(1/(√2 f_a)),
    N(φ) = ∫_{φ_end}^{φ} (V/V′) dφ = 2 f_a² ln[cos(φ_end/2f_a) / cos(φ/2f_a)],
    so  φ_*(N_e) = 2 f_a arccos[cos(φ_end/2f_a) · exp(−N_e / (2 f_a²))],
    A_s = V(φ_*) / (24 π² ε(φ_*))
        ⇒  Λ⁴ = 24 π² A_s ε(φ_*) / (1 − cos(φ_*/f_a)).

``tests/unit/test_natural_benchmark.py`` checks this closed form against
an independent numerical evaluation through M2's compiled potential
(root-found φ_end, quadrature for N, A_s re-evaluated from V and V′).
"""

from __future__ import annotations

import math

# Kawai & Kim (arXiv:1702.07689) natural-inflation benchmark, as recorded
# in docs/build/LEDGER.md (JAMES DECISION 11).
KK_F_A: float = 8.7          # axion decay constant, M_Pl
KK_A_S: float = 2.207e-9     # scalar amplitude at the pivot
KK_N_E: float = 60.0         # e-folds between pivot exit and end of inflation


def natural_epsilon(phi: float, f_a: float) -> float:
    """Potential slow-roll parameter ε_V = ½(V′/V)² for V = Λ⁴(1 − cos φ/f_a)."""
    return 1.0 / (2.0 * f_a**2 * math.tan(phi / (2.0 * f_a)) ** 2)


def natural_phi_end(f_a: float) -> float:
    """φ at which ε_V = 1 (end of slow-roll inflation)."""
    return 2.0 * f_a * math.atan(1.0 / (math.sqrt(2.0) * f_a))


def natural_phi_star(f_a: float, N_e: float) -> float:
    """φ that is ``N_e`` slow-roll e-folds before the end of inflation."""
    c_end = math.cos(natural_phi_end(f_a) / (2.0 * f_a))
    return 2.0 * f_a * math.acos(c_end * math.exp(-N_e / (2.0 * f_a**2)))


def natural_lambda_from_As(f_a: float, A_s: float, N_e: float) -> float:
    """Λ (M_Pl) such that the slow-roll A_s at ``N_e`` e-folds equals ``A_s``."""
    phi = natural_phi_star(f_a, N_e)
    lam4 = 24.0 * math.pi**2 * A_s * natural_epsilon(phi, f_a) / (1.0 - math.cos(phi / f_a))
    return float(lam4**0.25)


def natural_mass(f_a: float, Lambda: float) -> float:
    """Inflaton mass at the minimum, m = Λ²/f_a (M_Pl)."""
    return Lambda**2 / f_a


def kawai_kim_natural_params() -> dict[str, float]:
    """M2 ``natural`` parameters of the Kawai–Kim benchmark (M_Pl units)."""
    return {"f_a": KK_F_A, "Lambda": natural_lambda_from_As(KK_F_A, KK_A_S, KK_N_E)}


__all__ = [
    "KK_A_S",
    "KK_F_A",
    "KK_N_E",
    "kawai_kim_natural_params",
    "natural_epsilon",
    "natural_lambda_from_As",
    "natural_mass",
    "natural_phi_end",
    "natural_phi_star",
]
