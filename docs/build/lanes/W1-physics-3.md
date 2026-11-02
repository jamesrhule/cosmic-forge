# W1 physics lane, part 3 (Gate 1 fix lane PHYS3: physics review of P1-03 / Decision 11)

Branch `build/w1-phys3`, based on `9c6bf4c`. It handles the round-2 physics-review findings on P1-03 (PH-H1, PH-H2, PH-M ×4, PH-L ×2, PH-NIT) and the critic's `chiral.py` BLOCKER (the same defect as PH-H2). Evidence: `docs/build/evidence/W1-physics-3.md`. Main folds this file into the LEDGER.

Not touched: `docs/build/{PLAN,LEDGER,PROGRESS}.md`, `backend/audit/physics/**`, `backend/audit/golden.lock`, the drift-alarm workflow, `e2e/__screenshots__/**`, `R19.sha256`, `public/fixtures/**`, `worker.py`, `m8_agent/runs.py`, `m8_agent/tools/simulator.py`. The frozen audit (fast and slow) and the drift-alarm dirhash are green with every change below.

## Decisions

- **[PH-H2] The M3 Bogoliubov extraction is fixed and landed.** `m3_modes/chiral.py::_bogoliubov` used `1j/np.sqrt(2.0/k)` = i√(k/2) where i√(2/k) is required. With h = (αe^{−ikτ} + βe^{ikτ})/√(2k) and h′ = −ik(αe^{−ikτ} − βe^{ikτ})/√(2k), you get √(2k)h ± i√(2/k)h′ = 2αe^{−ikτ} and 2βe^{ikτ} respectively.
  - It now returns α e^{−ikτ} = ½(√(2k)h + i√(2/k)h′) and β e^{ikτ} = ½(√(2k)h − i√(2/k)h′). The phases are kept, because no caller passes τ. Every caller uses only |α| and |β| (F_GB, the drift, M4's chirality, M4's V4 indicator, M6, RunResult spectra).
  - On 9c6bf4c a free wave gave |β|² = ¼(1 − k/2)², and its mean over logspace(−1, 1, 8) is 0.6727340798362142. That was the whole default-path F_GB. S1's drift of 4.0 was k_max/2 − 1. The frozen audit stays green with the fix (fast 91 passed; slow `test_gb_to_zero_decoupling` passed), so the fix is landed rather than routed.
- **[PH-H2] η_B stays refused: one refusal rule, `m7_infer/pipeline.py::eta_B_refusal(pr)`.**
  - With the fix, the unitarity drift falls from 4.0 to 1.8e-6. The heuristic budget then falls from 4.0 to 2.45e-3, under the 0.5 % policy, so the budget alone would have published the raw η_B on every `fast` and `standard` run. For the kawai-kim-natural fixture at `fast` that is −4.26e-55 with M4's old GeV T_reh, or −6.157 with T_reh in M_Pl.
  - That number is not physical: ΔN_L scales linearly with the a-normalisation convention (`A_END_H_END`), and M4 has no adiabatic subtraction. LEDGER Decision 13(b) also says η_B becomes computable only with P1-04.
  - So M4 now measures `AnomalyResult.normalisation_residual` = |ΔN_L(a → c·a)/ΔN_L − 1| on every run (c = 10; it is 9.000 today). `eta_B_refusal` refuses η_B while either the budget or this residual exceeds 0.5 %, and also when the unitarity drift is not finite. `_budget_total`'s `max(1e-3, nan)` reads a NaN drift as 1e-3, so without that check it would fail open.
  - `build_run_result` and S8/S14 use the rule. RunResult η_B is therefore NaN on every run, as before, but now for a stated physical reason. The rule lifts by itself once P1-04 makes ΔN_L invariant.
- **[PH-H2] S8/S14 no longer publish a refused η_B.** They returned `value = pr.eta_B` raw: 1.32e-42 on 9c6bf4c, and −6.157 now. A refused η_B now gives FAIL (as before), `value = None`, `notes = "η_B refused: <reason>"`, with the same references. The frozen `test_check_is_well_formed` and `test_references_resolvable` pass.
- **[PH-M M4 units] T_reh is converted at the API boundary.** `AnomalyInputs.T_reh_GeV` becomes `T_reh` (M_Pl), and the pipeline passes `cfg.reheating.T_reh_GeV / M_PL_GEV`, as it does for Γ_φ.
  - On 9c6bf4c ΔN_L divided an M_Pl-unit source by GeV³, which is off by M_PL_GEV³ ≈ 1.44e55. This is honest as a units fix (Decision 11: GeV only at the API/UI boundary).
  - It does not make ΔN_L physical. That still needs the reheating matching (Routed, P1-04), and `eta_B_refusal` covers it.
  - No other GeV quantity reaches M1–M6 on the default path:
    - Γ_φ, `couplings.f_a` and the potential's `f`/`mu` are already converted;
    - `M_star`, `M1` and `S_E2` are not read;
    - M5's `AsymmetryInputs.T_reh_GeV` and `T_sph_GeV` are not used by its formula.
- **[PH-M M4 units] M6 f_Hz is marked as a placeholder.** `SGWBResult` gains `f_Hz_is_placeholder = True` and a `note`, and `sgwb.py`'s and `m6_gw/__init__.py`'s docstrings say why. f_Hz = 1e-19·k uses k in A_END_H_END units, and Ω_gw is unnormalised; only χ is convention-free.
  - `m6_gw/__init__.py` used to claim the placeholder is "flagged as `degraded` in the validation report"; nothing did that, and the claim is removed.
  - The values and the API's `RunSpectra.sgwb` are unchanged (no SDK, OpenAPI or R19 change).
- **[PH-M A_END_H_END] The docstring is corrected; the invariance fix is routed.** `couplings.py` now calls `A_END_H_END` a normalisation convention set by the code's own τ grid, not a derivation, and lists what does not cancel:
  - M4's ΔN_L and raw η_B (∝ c);
  - M6's placeholder f_Hz;
  - which modes are sub- or super-horizon on the fixed grids.

  The physical-a / a·T matching is P1-04 work (Routed). This lane adds what P1-04 needs to prove it: the in-run residual, and a test that the residual equals an end-to-end rescaled M3 + M4 run (ΔN_L × 10.0023 at c = 10, F_GB × 0.99999).
- **[PH-M grids] k_min|τ_start| ≫ 1 is not met and is routed.** It fails for 2 of 8 `fast` modes and 25 of 64 `high` modes. This is recorded in the `couplings.py` docstring. Changing the grids changes every M3 output, the adapter snapshot and the precision-ladder runtime, so it is not small and safe (Routed).
- **[PH-M fixture couplings / YAML] Decision 11 stands.** UCGLE-F1's coupling parameters stay. The fixture's couplings (θ_grav/f̂_a = 189.9 versus KK's γ/2 = 0.5; xi = +0.0085 versus ξ_KK′/8 ∈ [−63, −0.2] over the window) are UCGLE-F1's, not the paper's. The paper-valued configuration is P1-08's `kawai_kim_v2.yaml` (Routed).
  - `backend/configs/kawai_kim_baseline.yaml` was labelled "V2 (Kawai-Kim 1702.07689) baseline — target η_B ≈ 6.1e-10" with natural f_a = 1.0, Λ = 1e-3. Its potential is now Decision 11's benchmark, f_a = 8.7 and Λ = 0.0071154324599829784 (= `kawai_kim_natural_params()`, the fixture's values). Its couplings are unchanged (UCGLE-F1's).
  - Its header now says what it is: the benchmark potential with UCGLE-F1 couplings, not P1-08's V2 config; η_B not computable yet; the fixture's 6.1e-10 synthetic.
  - No test loaded the file. One new test now checks its potential equals `kawai_kim_natural_params()`.
  - Its `Gamma_phi: 1.0e-6` (and the frozen conftest's) is now read as GeV, i.e. 4.1e-25 M_Pl. Only M1 (S4/S7) reads it; recorded, not changed.
- **[PH-H1] The frozen Gate 1 condition is met literally.** With the fix, `test_gb_to_zero_decoupling` passes on the default path. Over ξ ∈ logspace(−6, −2, 9) on its config, f − f0 runs from −5.2e-30 to +2.5e-27.
  - For ξ ≥ 1e-3 it holds by physics: f − f0 = +2.2e-29 at 1e-3 and +2.5e-27 at 1e-2, matching the first-order prediction 2.53e-23·ξ².
  - For ξ ≲ 3e-4 the GB signal (≤ 2.3e-30) is below the integrator floor (≈ 1e-29), and the inequality holds there by its 1e-9 slack.
  - The discriminating test is the new non-frozen `tests/unit/test_gb_signal.py`.
- **[PH-H1] The resolvable configuration is the Kawai–Kim benchmark potential.** It uses f_a = 8.7 and Λ from A_s (Decision 11), with the frozen test's UCGLE-F1 couplings (θ_grav = 1e-3, f_a = 1e17 GeV) and ξ = ±1e-2, 2e-2, on the default pipeline at `fast`.
  - Results: ΔF = 7.62e-25, 8.7e4 × the free-wave floor (8.8e-30); positive on every mode; ΔF(−ξ)/ΔF(ξ) = 1.0023; ΔF(2ξ)/ΔF(ξ) = 3.997.
  - Per mode, ΔF and each helicity's |β_λ|² match an independent first-order (Born) integral of the coupling profile within 1.0 % (test: 3 %). The mean matches within 0.07 % (test: 1 %).
  - The sign is definite because, at first order, β_λ = β_GB + λβ_CS, and the helicity average cancels the GB–CS interference: ΔF = |β_GB|² ≥ 0.
  - |ΔF| ≫ the frozen 1e-9 slack is not reachable honestly: F/ξ² ≈ 1e-20 here, so it would need ξ ~ 3e5. The high-precision window (to τ = −1e-3) is not converged with the current solver (per-mode |β|²/ξ² changes by up to six orders of magnitude between rtol 1e-10 and 1e-12, and is not ∝ ξ² at fixed rtol), so it is not used (Routed, P1-07).
- **[PH-L S6] The 9→10 flip was a numerical artefact.**
  - S6 compares a trapezoid with `scipy.quad` of the same 8-point linear interpolant (`_adiabatic_subtraction` ≡ 0). On 3d2355a (schematic) the per-mode integrand was ≲ 5e-19, below `quad`'s `epsabs` 1e-12, giving residual 1.047e-3 and FAIL. On 9c6bf4c the extraction artefact raised it to ≳ 1e-13, giving 7.94e-9 and PASS_P. Both were re-measured here with the reviewer's `fixture_audit.py`.
  - Re-measured after PH-H2, fixture `fast`: 1.48e-3, FAIL. Standard 1.05e-2, FAIL. Audit conftest 9.2e-3, FAIL.
  - The adapter's `audit_passed` stays 10 only because S9 goes FAIL → PASS_P at the same time (budget 4.0 → 2.45e-3). Neither flip is physics progress.
- **[PH-L schematic] The schematic model is diagnostic only.** The docstrings in `pipeline.py` (`coupling_model`) and `couplings.py` say so: since the f_a/M_PL_GEV fix its CS term is the constant ±θ_grav/f̂_a. For the fixture that is ±189.9, so one helicity has ω² < 0, F_GB ≈ 1.9e146, raw η_B ≈ −8e173, and it takes 71 s through mpmath.
  - No run path selects it. The option is kept (R2).
  - `tests/unit/test_schematic_smoke.py` checks it runs to completion with η_B refused: the frozen-test config is fast (0.4 s); the fixture couplings are `slow` (≈ 70 s).
- **[PH-NIT] m = 5.82e-6 versus Decision 11's "≈ 5e-6" is rounding.**
  - Independent mpmath: m = 5.81947e-6 at N_e = 60. m = 5e-6 needs N_e = 69.30 or f_a = 5.361. The non-reduced M_Pl gives 1.16e-6.
  - `natural.py`'s docstring now states the computed value and these numbers, plus the exact-trajectory pivot (61.12 e-folds before ε_H = 1).
  - The e-fold estimates are corrected in `couplings.py` (where they were) and `natural.py`. For the benchmark, τ = −5 / −1 / −0.1 are 10.06 / 8.35 / 5.84 e-folds before the end, not "≈ 8.5 / 6.9" (the de Sitter estimate). Starobinsky gives 9.17 / 7.54 / 5.19.
  - `test_natural_benchmark`'s comment is corrected.
- **[PH-M tests] The frozen `test_parity_flip_inverts_asymmetry` is non-discriminating on both trees.** On 9c6bf4c, |asym| is 2.9046e-14 versus 2.7690e-14 (4.7 % apart). On this branch it is 3.645e-27 versus 3.707e-27 (1.7 % apart). Its rel = 1e-6 fails both; it passes only through abs = 1e-12.
  - Likewise the frozen `test_s3_gb_decoupling_limit` compares two different potentials (Starobinsky ξ = 0: 7.3e-28; natural f_a = 1: 9.3e-30) under a 1e-2 slack.
  - Neither can be edited (R5). The non-frozen tests below discriminate.

## Corrected tests (old → new, with proof)

- **[PH-H2] `backend/tests/test_qcompass_adapter/test_adapter_matches_direct_pipeline_eta_b.yml`:** `F_GB: 0.6727340798350541` → `F_GB: 2.806134139836033e-17`. `audit_passed: 10`, `audit_total: 15`, `eta_B: NaN` and `eta_B_is_nan: true` are unchanged.
  - Proof that the old value was the artefact:
    - ¼(1 − k/2)² is what the shipped extraction returns for a free wave. Its mean over logspace(−1, 1, 8), the fixture's `fast` k-grid, is 0.6727340798362142.
    - The ξ = θ = 0 pipeline F_GB on 9c6bf4c is 0.6727340798362141.
    - The old snapshot is that artefact minus 1.2e-12.
    - With the corrected extraction the free-wave value is < 1e-12 (`test_chiral_bogoliubov.py`, 57 cases, all failing on 9c6bf4c). The fixture gives 2.806134139836033e-17, which agrees with an independent first-order (Born) integral of its coupling profile.
  - `audit_passed` is still 10, but S6 PASS_P → FAIL and S9 FAIL → PASS_P (PH-L S6 above).
  - The V2 η_B `xfail` is untouched.
- **[PH-M] `tests/unit/test_couplings.py::test_gb_to_zero_decoupling_strict[ξ]` (ξ ∈ {1e-6, 1e-4, 7.8125e-3, 1e-2}):**
  - Old: `abs(f − f0) <= 1e-12` and `f0 <= f + 1e-9`.
  - New: `abs((f − f0) − born) <= max(0.05·born, NOISE)` and `f0 <= f + NOISE`.
    - `born` is the first-order ⟨|β_GB|²⟩ from the profile's B and C: 2.53e-23·ξ².
    - NOISE = 1e-28, ≈ 10 × the free-wave integrator floor 8.8e-30. A module fixture pins the floor below NOISE/10.
  - This is strictly tighter. The old bound was 1e-12 against a signal of at most 2.5e-27, so it passed with GB ≡ 0. The new bound is ≤ 1.3e-28, about 5 % of the 1e-2 signal: GB ≡ 0 fails, and so does a wrong magnitude.
  - Measured mean ratio ΔF/born: 0.992 (1e-2), 1.019 (7.8125e-3).
  - On 9c6bf4c all four error out on the floor (0.6727 > 1e-29).
- **[PH-M] `tests/unit/test_couplings.py::test_xi_flip_preserves_asymmetry_magnitude`:**
  - Old: `abs(asym(1e-3)) == approx(abs(asym(-1e-3)), rel=1e-6, abs=1e-12)`.
  - New: `abs(a_pos) > 10·NOISE` and `a_neg == approx(-a_pos, rel=5e-2, abs=0)`.
  - Its comment was wrong ("GB is parity-even, so flipping ξ leaves |Σ| unchanged to first order", as a property of a parity-even GB alone). It now says why: at first order β_λ = β_GB + λβ_CS, so Σ(|β₊|² − |β₋|²) = 4ΣRe(β_GB β_CS*) is odd in ξ. The flip changes its sign and keeps its magnitude.
  - Proof the old test could not fail: the asymmetry is 3.6e-27 here and 2.9e-14 on 9c6bf4c, both ≪ abs = 1e-12, so the old test passed on both trees.
  - Measured now: a_pos = −3.645e-27, a_neg = +3.707e-27 (1.7 %). On 9c6bf4c the new test fails: −2.77e-14 versus −2.90e-14 have the same sign.
- **[PH-M] `tests/unit/test_couplings.py::test_parity_flip_swaps_helicities_exactly`:** the exact swap assertions are unchanged, plus `abs(asym) > 10·NOISE`, so the swap is not satisfied trivially by β₊ = β₋ (tightening).
- **[PH-M] `pytest.approx` defaults to `abs=1e-12` even when only `rel` is given.** Every affected comparison of a small quantity now has `abs=0` (tightening):
  - `tests/unit/test_natural_benchmark.py::test_lambda_reproduces_As_at_60_efolds`: `approx(KK_A_S, rel=1e-9)` → `rel=1e-9, abs=0`. A_s = 2.2e-9, so the old effective tolerance was 4.5e-4 relative, not 1e-9. It passes at 1e-9.
  - `…::test_inflaton_mass_is_about_5e_minus_6`: `approx(5.819468861216026e-06, rel=1e-12)` → `…, abs=0`. The old effective tolerance was 1.7e-7 relative. Its comment is corrected: "one significant figure" was wrong, since 5.82e-6 rounds to 6e-6; the rel = 0.2 line accepts N_e ≈ 58.3–85.2. That line is unchanged.
  - `tests/unit/test_m2.py::test_custom_potential_derivatives_are_symbolic_in_phi`: the four `approx(…e-12, rel=1e-12)` → `…, abs=0`. With values of 1e-12 to 8e-12, the old tolerance of 1e-12 accepted any result in [0, 9e-12]. They pass at rel = 1e-12.

## Removals with replacement

- **[PH-H2] `AnomalyInputs.T_reh_GeV` → `AnomalyInputs.T_reh` (M_Pl).** Its only caller, `pipeline.py`, converts at the boundary. `RunConfig.reheating.T_reh_GeV` (API) is unchanged.
- **[PH-H2] The inline `if budget.total > 5e-3` in `build_run_result` → `eta_B_refusal(pr)`.** It keeps the same budget rule, adds the normalisation and non-finite-drift rules, and uses the constant `ETA_B_MAX_REL_UNCERTAINTY = 5e-3`.
- **[PH-M M6] The `m6_gw/__init__.py` sentence claiming the placeholder is "flagged as `degraded` in the validation report"** → the real `SGWBResult.f_Hz_is_placeholder` and `note`.

## Routed to later tickets

- **P1-04 (M4).**
  1. Make ΔN_L normalisation-invariant: physical a or a·T matching at reheating, from M1's background (a_reh, g_*) instead of `A_END_H_END`. `AnomalyResult.normalisation_residual` must drop to ≤ 5e-3, and `eta_B_refusal` then stops refusing on it.
     - `tests/unit/test_m4_units_and_refusal.py::test_normalisation_residual_matches_a_full_rescaled_run` pins it at c − 1 = 9 today. P1-04 corrects it to ≈ 0, with this lane's end-to-end rescale as proof.
     - `test_run_result_refuses_eta_b_on_the_normalisation` and `test_s8_s14_do_not_publish_a_refused_eta_b` change the same way.
  2. ΔN_L → n_L/s: M4 divides by T_reh³, not s = (2π²/45)g_*T³, and M5 divides by 7.04. Units are consistent now; the normalisation is not.
  3. The adiabatic subtraction is still ≡ 0 (`evidence/P1-04.md` gap 1).
  4. Grids with k_min|τ_start| ≫ 1 (now 2/8 `fast` and 25/64 `high` modes start with k|τ| < 1).
  5. When η_B becomes computable, Decision 13(b): the fixture's result fields and the R19 rebaseline. This lane changed no fixture.
- **P1-07 (uncertainty budget and solver).**
  - The budget is heuristic: fixed stat 1e-4, grid 2e-3 and inputs 1e-3, and `scheme = max(1e-3, drift)`, which reads a NaN drift as 1e-3 (guarded in `eta_B_refusal`, not in `_budget_total`).
  - The high-precision window (to τ = −1e-3) is not converged: DOP853 steps over the end-of-inflation coupling growth (needs max_step or dense control).
  - At `high`, 39 of 64 fixture modes still escalate to mpmath (drift 1e-12 to 8.4e-9 > 1e-12; 2 s at k = 1, 30 s at k = 100). Before the fix it was 64/64.
  - S1 FAILs at `fast` and `standard` because rtol 1e-6 / 1e-8 gives drift 1.8e-6 / 1.3e-7 > 1e-8. That is integrator tolerance now, not the extraction.
  - S6 measures quadrature agreement, not an adiabatic residual.
- **P1-08 (V2 recovery).**
  - The paper-valued `kawai_kim_v2.yaml`: θ_grav/f̂_a = γ/2 = 0.5, and an ξ that represents ξ_KK′/8 (−0.2 → −63 over the window, with ξ_KK″ ≠ 0, which the linear model cannot carry).
  - The V2 η_B `xfail`.
  - Any change to the frozen suite (the non-discriminating parity and S3 tests above) goes through P1-08/P1-12 with James's `physics-reviewed` label.
- **Other lane (worker / agent η_B gating; files not touched here).** Every place a pipeline η_B reaches a user must apply `ucgle_f1.m7_infer.pipeline.eta_B_refusal(pr)`, the one rule:
  - `m8_agent/runs.py:157–171` `validation_benchmarks_for(pr)` sets `observed = pr.eta_B` unrefused and derives `relativeError` and `status` from it. When `eta_B_refusal(pr)` is not None, `observed` and `relativeError` must be NaN (as `RunResult.eta_B`), and `status` must not be computed from the raw value. `ValidationStatus` has no "refused" value, so either omit the V2 row or add one through the API schema (SDK types regenerate).
  - `worker.py:168–171` passes `validation_benchmarks_for(pr)` into `build_run_result`, so the fix above covers it. `MetricEvent("eta_B")` already uses `result.eta_B.value` (gated).
  - `m8_agent/tools/simulator.py:207–214` (MCP scan) sets `ScanCell.eta_B=float(pr.eta_B)`. It must be NaN when `eta_B_refusal(pr)` is not None (or use `build_run_result(...).eta_B.value`).
  - Already gated, no change needed: `cli.py:37`, `adapters/qcompass.py:145,253`, `simulator.py:175` (`r.eta_B.value`), and S8/S14 (this lane).
  - Without that gating, after this branch merges, `validation.observed` and scan cells show the raw M_Pl-unit value (fixture `fast`: −6.157; `standard`: −2030) instead of 9c6bf4c's 1.3e-42. Both are equally unphysical, but the new one is more visibly wrong. The gating must land with or before this branch.

## BLOCKED-ON-JAMES

None. No new secret or environment variable name was introduced. One optional, non-blocking question for James (PH-NIT): whether Decision 11's "m ≈ 5e-6" came from a different N_e (≈ 69.3) or f_a (≈ 5.36). The code reports the computed 5.82e-6 either way.
