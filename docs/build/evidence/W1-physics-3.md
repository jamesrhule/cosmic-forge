# W1 physics lane part 3 (Gate 1 fix lane PHYS3): evidence

Branch `build/w1-phys3`, based on `9c6bf4c`. Lane notes: `docs/build/lanes/W1-physics-3.md`. Findings: the round-2 physics review of P1-03 / Decision 11, and the critic's `chiral.py` BLOCKER (the same defect as PH-H2).

## Method

- **"Fails on 9c6bf4c."** `git archive 9c6bf4c` was unpacked into a scratch directory outside the repo. Each new or changed test file was copied in and run with this worktree's venv, with `PYTHONPATH` pointing at the archive's `backend/src` (`ucgle_f1.__file__` was checked to resolve there).
  - Two new tests import names that do not exist on 9c6bf4c (`eta_B_refusal` and friends). For those, a scratch copy of the same assertions with only 9c6bf4c-available imports was run. The copies are listed below.
  - An ImportError was never counted as a failure.
- **Ablation.** `git archive HEAD` with `eta_B_refusal`'s normalisation rule removed shows what the PH-H2 fix would publish without it.
- **Repro scripts.** The reviewer's scripts in the scratch `gate1/scratch-phys/` were run unedited (`fixture_audit.py`, `natural_indep.py`, `gbtest.py`, `parity.py`), together with this lane's own scripts (scratch `phys3/scripts/`).

## Per finding

| Id | Test(s) | Fails on 9c6bf4c for the bug's reason? |
|---|---|---|
| PH-H2 (and critic BLOCKER) | `tests/unit/test_chiral_bogoliubov.py`: 57 cases. Free wave h = e^{−ikτ}/√(2k) for k ∈ {1e-3, 0.1, 0.5, 1, 3.7, 10, 1e3} × τ ∈ {−5, −1, −0.37, −1e-3}: \|β\|² < 1e-12 and \|\|α\|² − \|β\|² − 1\| < 1e-12. Mixed state (r = 0.3, with phases): \|α\|, \|β\| and the e^{∓ikτ} phases recovered at rel 1e-12. `solve_chiral_modes` with A = B = C = 0: F_GB < 1e-12. | **Yes, 57/57.** Example: k = 1e-3 gives \|β\|² = 0.24975006 = ¼(1 − k/2)². |
| PH-H2 | `tests/test_qcompass_adapter.py::test_adapter_matches_direct_pipeline_eta_b`, snapshot F_GB 0.6727340798350541 → 2.806134139836033e-17 | **Yes**: the snapshot diff shows 0.6727340798350541 (the artefact). |
| PH-H2 (η_B refusal) | `test_m4_units_and_refusal.py::test_run_result_refuses_eta_b_on_the_normalisation`, `::test_eta_b_refusal_rule` | n/a on 9c6bf4c, where η_B is NaN because of the artefact (budget 4.0). **Ablation**: with the PH-H2 fix and no normalisation rule, both fail and the adapter snapshot becomes `eta_B: -6.156725847148029`, `eta_B_is_nan: false`. |
| PH-H2 (S8/S14) | `test_m4_units_and_refusal.py::test_s8_s14_do_not_publish_a_refused_eta_b` | **Yes** (scratch copy `test_s8_base_scratch.py`, same assertions): S8 `value=1.3230438380172168e-42`, the raw η_B. |
| PH-H1 | `tests/unit/test_gb_signal.py`: 6 tests on the KK benchmark potential, default pipeline, `fast`. Checks: floor < 1e-28 and signal > 1e3·floor; ΔF > 0 on every mode for ξ = ±1e-2, 2e-2; even and quadratic (rel 1e-2, abs 0); ΔF and each \|β_λ\|² match the first-order Born integral (per-mode rtol 3e-2, mean rel 1e-2). | **Yes, 6/6.** Floor 0.6727 (artefact); ΔF per mode of mixed sign (e.g. −8.2e-12); Born mismatch 1e13×. |
| PH-M (A_END_H_END / M4 invariance) | `test_m4_units_and_refusal.py::test_normalisation_residual_matches_a_full_rescaled_run` | n/a: this is new measurement API that documents the routed gap (it pins c − 1 = 9). |
| PH-M (M4 units) | `test_m4_units_and_refusal.py::test_delta_n_l_divides_by_t_reh_in_reduced_planck_units` | **Yes** (scratch copy `test_m4_units_base_scratch.py`): ΔN_L = 2.628e-41 against the expected 3.795e14, a ratio of M_PL_GEV³. |
| PH-M (M6 placeholder) | `test_m4_units_and_refusal.py::test_m6_frequencies_are_flagged_as_placeholder` | n/a: new flag; the values are asserted unchanged. |
| PH-M (YAML) | `test_natural_benchmark.py::test_backend_baseline_config_carries_the_benchmark_potential` | **Yes**: `{'f_a': 1.0, 'Lambda': 0.001}` against the benchmark. |
| PH-M (tests) | `test_couplings.py::test_gb_to_zero_decoupling_strict[4]`, `::test_xi_flip_preserves_asymmetry_magnitude`, `::test_parity_flip_swaps_helicities_exactly`, plus the `abs=0` tightenings in `test_natural_benchmark.py` and `test_m2.py` | **Yes** for strict[4] (error: floor 0.6727 > 1e-29) and xi_flip (−2.77e-14 against +2.90e-14: no sign flip; the old version passed on 9c6bf4c through abs = 1e-12). Parity-swap and the `abs=0` tightenings pass on 9c6bf4c too (they are tightenings, not bug tests). |
| PH-L (S6) | Documentation and re-measurement (below) | n/a |
| PH-L (schematic) | `tests/unit/test_schematic_smoke.py::test_schematic_path_runs_to_completion` (fast), `::test_schematic_path_completes_on_the_fixture_couplings` (`slow`, ≈ 70 s) | n/a: smoke tests, which pass on both trees. |
| PH-NIT | Docstrings and the corrected test comment; `natural_indep.py` re-run | n/a |

## PH-H2 downstream, default (physical) path: 9c6bf4c → this branch

Measured by the scratch `phys3/scripts/measure.py` (run with `-W error`, as pytest runs), `seed=0`.

| Config | F_GB (mean) | max drift | budget total | mpmath escalations | raw η_B | RunResult η_B | audit passed |
|---|---|---|---|---|---|---|---|
| kawai-kim-natural, `fast` | 0.6727340798350541 → **2.806134139836033e-17** | 4.0 → 1.81e-6 | 4.0 → 2.45e-3 | 8/8 → 0/8 | 1.32e-42 → −6.157 | NaN (budget) → NaN (normalisation residual 9.0) | 10 → 10 |
| kawai-kim-natural, `standard` | 52.085 → 2.458e-16 | 49.0 → 1.33e-7 | 49.0 → 2.45e-3 | 16/16 → 0/16 | 1.66e-37 → −2030 | NaN → NaN | 10 → 10 |
| kawai-kim-natural, `high` (M3 only) | not run on 9c6bf4c (drift \|k/2 − 1\| > 1e-12 for every grid k, so all 64 escalate) | → 8.4e-9 (median 7e-12) | n/a | 64/64 → **39/64** (mpmath: 2 s at k = 1, 3 s at k = 10, 30 s at k = 100) | n/a | n/a | n/a |
| audit conftest `kawai_kim_config` (natural f_a = 1), `fast` | 0.672734079836214 → 9.26e-30 | 4.0 → 1.81e-6 | 4.0 → 2.45e-3 | 8/8 → 0/8 | 8.5e-65 → −2.6e-22 | NaN → NaN | 9 → 10 |
| audit conftest `gb_off_config` (Starobinsky ξ = 0), `fast` | 0.6727340798362144 → 7.31e-28 | 4.0 → 1.81e-6 | 4.0 → 2.45e-3 | 8/8 → 0/8 | 8.1e-60 → −7.6e-20 | NaN → NaN | 8 → 10 (S3 FAIL → PASS_P) |
| parity-hypothesis config ξ = 1e-3, `fast` | 0.6727340798362094 → 7.53e-28 | 4.0 → 1.81e-6 | 4.0 → 2.45e-3 | 8/8 → 0/8 | 8.3e-60 → −3.2e-19 | NaN → NaN | 9 → 10 |

S1–S15 verdicts. On 9c6bf4c the fixture at `fast` gave S1 FAIL, S5 FAIL, S6 PASS_P, S8 FAIL, S9 FAIL and S14 FAIL; everything else passed. On this branch it gives S1 FAIL (drift 1.8e-6 > 1e-8, i.e. rtol 1e-6), S5 FAIL, **S6 FAIL** (1.48e-3), S8 FAIL (refused, value None), **S9 PASS_P** (2.45e-3) and S14 FAIL (refused); everything else passes. On this branch every audit config gives these same verdicts. On 9c6bf4c the audit conftest's configs already failed S6, and the gb-off config also failed S3, because F_GB was 0.67 at ξ = 0.
- **RunResult η_B is still NaN on every run**, now for the stated reason "ΔN_L depends on the scale-factor normalisation (residual 9)".
- Without that rule (the ablation), it would be −6.157 on the fixture at `fast`. With M4's old GeV T_reh it would be −4.26e-55.
- No fixture or R19 page was changed (Decision 13(b) is later).
- Wall time on the fixture: `fast` 12.4 s → 0.7 s, `standard` 75.8 s → 2.4 s (no mpmath escalation).

Normalisation (gauge) check, fixture at `fast`, M3 at rtol 1e-10. An end-to-end a → 10a, k → 10k, τ → τ/10 run gives F_GB 2.805981e-17 → 2.805941e-17 (× 0.99999, invariant). ΔN_L goes −122.45 → −1224.75 (× 10.0023). M4's in-run `normalisation_residual` is 9.000000000000002.

## PH-H1: GB signal and the frozen condition

- **Frozen test, literally.** On the config of `audit/physics/test_parity_hypothesis.py::test_gb_to_zero_decoupling` (Starobinsky, θ_grav = 1e-3, `fast`), f0 = 7.3078e-28. Over ξ ∈ logspace(−6, −2, 9), f − f0 ∈ [−5.18e-30, +2.505e-27]:
  - 1e-6: −1.65e-31;
  - 1e-5: −8.8e-31;
  - 1e-4: +2.7e-30;
  - 3.2e-4: −1.7e-30;
  - 1e-3: +2.22e-29;
  - 3.2e-3: +2.31e-28;
  - 1e-2: +2.505e-27.

  f0 ≤ f + 1e-9 holds at every point. Above ξ ≈ 1e-3 it holds by physics: Born gives 2.53e-23·ξ², and the mean ratio is 0.99 to 1.02. Below that, the signal is under the ≈ 1e-29 integrator floor and the 1e-9 slack carries it.
  - On 9c6bf4c, F(1e-2) − F(0) = −4.99e-14: the wrong sign, hidden by the slack. This is the reviewer's `gbtest.py` result.
- **Resolvable test** (`test_gb_signal.py`: KK benchmark potential, θ_grav = 1e-3, f_a = 1e17 GeV, `fast`):
  - The free-wave floor is 8.785e-30.
  - ΔF(1e-2) = 7.6185e-25 (Born 7.6131e-25, mean ratio 1.0007, per mode ≤ 1.0 %). ΔF(−1e-2) = 7.6361e-25 (ratio 1.0023). ΔF(2e-2) = 3.0450e-24 (3.997×).
  - The minimum per-mode ΔF is 9.9e-26 > 0.
  - Per-helicity \|β_λ\|² against Born is within ≤ 0.7 %.
- **High-precision window is not usable.** Starobinsky, θ = 0, window [−5, −1e-3], 8 modes: per-mode F/ξ² at rtol 1e-10 differs from rtol 1e-12 by up to 2e6×. It is also not ∝ ξ² (F(1e-3) = 1.48e-17 > F(1e-2) = 4.2e-18). That is solver non-convergence near the end of inflation (Routed, P1-07).

## PH-M tests (parity / ξ-flip), measured on this branch

- ξ-flip (Starobinsky, ξ = ±1e-3, θ_grav = 1e-3): asym = −3.6454e-27 and +3.7075e-27, |sum|/|asym| = 1.7 %. On the KK benchmark it is −5.6109e-25 and +5.6350e-25 (0.43 %).
- On 9c6bf4c the reviewer's `parity.py` gives −2.9046e-14 and −2.7690e-14: no sign flip, 4.7 % apart.
- The frozen `test_parity_flip_inverts_asymmetry` (rel 1e-6, abs 1e-12) passes on both trees only through abs.

## PH-NIT, re-run

`natural_indep.py` (mpmath, no repo imports) at N_e = 60 gives:
- Λ = 7.1154324599829791e-3 and m = 5.81947e-6;
- n_s = 0.9652 and r = 0.0864;
- m = 5e-6 at N_e = 69.30, or at f_a = 5.3606;
- non-reduced m = 1.16e-6, quadratic limit 5.975e-6.

M2's exact trajectory from φ_*(60) reaches ε_H = 1 after 61.12 e-folds. On M3's window, e-folds before the end at τ = −5 / −1 / −0.1 are 10.06 / 8.35 / 5.84 for KK, 9.17 / 7.54 / 5.19 for Starobinsky, and 9.19 / 7.58 / 5.26 for natural f_a = 1.

## Frozen audit and drift alarm (with every change)

- `cd backend && uv run --frozen pytest audit -q -m "not slow"`: **91 passed**, 1 deselected.
- `cd backend && uv run --frozen pytest audit -q -m slow`: **1 passed** (`test_gb_to_zero_decoupling`).
- Drift-alarm workflow steps, replayed verbatim on `git archive` of the branch in a clean scratch directory with its own `.venv`: freeze intact at `ee21643` and again at `99903c6` (Suites table).
- `git diff 9c6bf4c -- backend/audit .github/workflows/ucglef1-drift-alarm.yml e2e public` is empty.

## Suites

Run on the branch head (backend code as of `99903c6`; the commits after it touch only docs). There were 4 shared CPUs.

| Check | Result |
|---|---|
| `cd backend && uv run --frozen pytest -q -m "not slow"` | **599 passed**, 3 deselected, 1 xfailed (the parked V2 η_B, untouched), exit 0 |
| `cd backend && uv run --frozen pytest -q -m slow` | **3 passed**: `test_gb_to_zero_decoupling`, `test_adapter_standard_precision_runs`, and the new `test_schematic_path_completes_on_the_fixture_couplings`. Exit 0. |
| `cd backend && uv run --frozen pytest audit -q -m "not slow"` (frozen) | **91 passed**, 1 deselected |
| `cd backend && uv run --frozen pytest audit -q -m slow` (frozen) | **1 passed** (`test_gb_to_zero_decoupling`) |
| Drift-alarm replay (`git archive` of `99903c6`, own `.venv`): `uv sync --package ucgle_f1`, `uv pip install "dirhash>=0.5"`, `PYTHONPATH=src uv run pytest audit -q -m "not slow"`, dirhash | sync rc 0, pip rc 0. 89 passed, 2 skipped (A8 ×2: `qcompass_router` is not installed by the package-only sync, which is pre-existing), 1 deselected. dirhash `42805c73538df5eb0f9eb109ead9a541253d5371d71eac5ea04be0ffaf8e92dd` = `golden.lock`: **freeze intact** |
| `uv run --frozen pytest packages -q --import-mode=importlib` | 350 passed, 7 skipped, exit 0 |
| `bun run lint` | 0 errors, 15 warnings (pre-existing `react-refresh`), exit 0 |
| `bunx prettier --check .` | All matched files use Prettier code style, exit 0 |
| `bunx tsc --noEmit` | exit 0 |
| `bun run test` | 21 files, 116 passed, exit 0 |
| `bun run build` | built, exit 0 |
| `scripts/check_r19.sh` | R19 baselines locked: 9 PNGs match `R19.sha256`, exit 0 |
| `scripts/gen_sdk_types.sh --check` | SDK types match the API's OpenAPI document, exit 0 |
| `uv lock --check` | Resolved 557 packages, exit 0 |

No frontend, fixture, OpenAPI or SDK file changed. `git diff 9c6bf4c -- backend/audit .github e2e public src packages` is empty.
