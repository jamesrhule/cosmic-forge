# W1 physics lane (P1-01 … P1-04)

Branch `build/w1-physics` from `5687964`. Folded into LEDGER by main.

## Decisions
- **[P1-01] M1 integrates ln ρ.** The linear-ρ solve with `atol=1e-12` lost all accuracy once ρ ≪ 1e-12: ρ_r was 25 % off a⁻⁴ after 5 e-folds. Same equations, now in log variables (uniform relative accuracy). Same public API.
- **[P1-01] τ origin.** τ = 0 at N = 0 (start of the M1 window), a(0) = 1. Only τ differences are physical.

## Drift-alarm coverage (evidence/P0-07.md)
The two physics drifts that passed every fast audit are now caught by non-frozen unit tests in `tests/unit/test_m1_conformal.py`:
- `dphi` −3 → −4 fails `test_matter_dilutes_as_a_minus_3_without_decay` and `test_matter_domination_conformal_time_is_analytic`.
- `M_PL_GEV` → 3.4352e18 fails `test_reduced_planck_mass_constant`.
These tests run in CI's `backend` job. The drift alarm itself only runs `audit/`, which is frozen.

## P1-02
- **[P1-02] Cosmic-time KG integration.** The e-fold form is singular during oscillations (H² = V/(3 − x²/2) with x²/2 → 3 when V → 0). The integration therefore runs in t with state (φ, φ̇, ρ_r, N) and reports on an N grid. Stage methods are as the ticket asks: DOP853 for inflation, Radau for the reheating stage.
- **[P1-02] Defect found and fixed.** Custom potentials had V′ ≡ V″ ≡ 0 (sympify Symbol-assumption mismatch). There is a regression test.
- **[P1-02] PyTransport.** Soft-import only. The adapter raises until P1-06 pins the package and its API can be verified (no API guessing).

## P1-03 (OPEN-WITH-GAP; evidence/P1-03.md)
- **[P1-03] Couplings from the general GB/CS tensor action.** G_T = 1 − 4Hξ̇, F_T = 1 − 4ξ̈ (Horndeski mapping) and CS z_λ² ∝ a²(1 − λkf′/a²), first order. arXiv:1702.07689 is unreachable here, so the equation numbers are unverified.
- **[P1-03] Substitution: M3 mode equation.** k² + Ak + B → k²(1 + C) + Ak + B with optional C = c_T² − 1. The default C = None leaves behaviour unchanged.
- **[P1-03] Default stays `schematic`.** The published V2 fixture (natural, f = 7e16 GeV, Λ⁴ = 2.5e-7) cannot be an inflaton, and switching breaks 3 adapter tests. `RunPipeline(coupling_model="physical")` is opt-in, and under it the frozen GB→0 audit passes.

## P1-04 (OPEN-WITH-GAP; evidence/P1-04.md)
- **[P1-04] Quadrature cross-check done.** mpmath.quad at dps 30 vs scipy quad on the same interpolant, flagged above 1e-8, reported on every `AnomalyResult`.
- **[P1-04] Gap.** The 4th-order adiabatic subtraction (Kamada et al.) and the V4 normalisation need the papers, which are unreachable, plus a M3/M4 basis change (|h|² representation with −a″/a). The subtraction hook is unchanged, with no fabricated counterterm.

## Lane summary
| Ticket | Status |
|---|---|
| P1-01 | DONE |
| P1-02 | DONE (PyTransport adapter pending P1-06) |
| P1-03 | OPEN-WITH-GAP: physical couplings opt-in; frozen GB→0 audit passes under them; the default is blocked by the V2 fixture's parameterisation and paper access |
| P1-04 | OPEN-WITH-GAP: quad cross-check done; adiabatic subtraction and V4 normalisation need the papers and the basis change |
