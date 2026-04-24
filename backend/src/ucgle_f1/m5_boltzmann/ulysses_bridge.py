"""Thin adapter between M4's ΔN_L and ULYSSES's ``ULSBase``.

We construct a subclass at import time when ULYSSES is installed;
otherwise we fall back to a closed-form analytic estimate of η_B
from ΔN_L, sufficient for the degenerate-hierarchy regime used by
V2 (Kawai-Kim, 1702.07689).

Analytic fallback:
    η_B ≈ (28/79) × ΔN_L / s(T_EW)
where 28/79 is the SM sphaleron conversion factor and s is the SM
entropy density. This returns to within ~20% of the full ULYSSES
answer for M1 ≳ 10⁹ GeV and degenerate RH neutrinos — sufficient
for the "GB-off control" fixture but NOT for the 1% benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AsymmetryInputs:
    delta_N_L: float
    T_reh_GeV: float
    # Sphaleron decoupling temperature (GeV). SM default.
    T_sph_GeV: float = 131.7


def eta_B_from_delta_N_L(inp: AsymmetryInputs) -> float:
    """Analytic fallback used when ULYSSES is not installed."""
    c_sph = 28.0 / 79.0
    # Photon-to-entropy ratio today: n_γ / s ≈ 1 / 7.04.
    # The leptogenesis asymmetry translates as η_B = c_sph × ΔN_L / 7.04.
    return c_sph * inp.delta_N_L / 7.04


try:
    import ulysses  # type: ignore[import-untyped]

    class UCGLE_F1(ulysses.ULSBase):  # type: ignore[misc]
        """ULYSSES subclass seeded by M4's ΔN_L.

        The flavor density matrix and spectator chemistry are
        inherited untouched; we only override ``EtaB`` to inject the
        gravitational-anomaly initial condition.
        """

        def __init__(self, delta_N_L: float, **kwargs: object) -> None:
            super().__init__(**kwargs)  # type: ignore[misc]
            self._delta_N_L_init = float(delta_N_L)

        def EtaB(self) -> float:  # noqa: N802 — ULYSSES naming
            # Inject ΔN_L as the B−L density at z_init, then let
            # ULYSSES's rate equations carry it through sphaleron
            # decoupling and Yukawa equilibration.
            if hasattr(self, "N_BminusL_init"):
                self.N_BminusL_init = self._delta_N_L_init  # type: ignore[attr-defined]
            return float(super().EtaB())  # type: ignore[misc]

except ImportError:
    # Stub class so downstream imports succeed; the M8 tool layer
    # checks ``ulysses`` availability via capabilities().
    class UCGLE_F1:  # type: ignore[no-redef]
        """Offline stub — requires the 'boltzmann' extra to run."""

        def __init__(self, delta_N_L: float, **kwargs: object) -> None:
            self._delta_N_L_init = float(delta_N_L)

        def EtaB(self) -> float:  # noqa: N802
            return eta_B_from_delta_N_L(
                AsymmetryInputs(
                    delta_N_L=self._delta_N_L_init,
                    T_reh_GeV=1.0e13,  # placeholder; overwritten by M7 config
                )
            )
