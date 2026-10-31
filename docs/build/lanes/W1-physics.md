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
