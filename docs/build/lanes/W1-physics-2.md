# W1 physics lane, part 2 (P1-03 default coupling, D13a badge)

Branch `build/w1-physics`, merged up to `origin/build/w1-foundations` at `9edef41`. It implements LEDGER JAMES DECISION 11 and the badge half of DECISION 13(a). Evidence: `docs/build/evidence/P1-03.md`. Main folds this file into LEDGER.

## Decisions
- **[P1-03] `coupling_model="physical"` is the default.** The option exists only on `RunPipeline` (`m7_infer/pipeline.py`). `RunConfig`, the hydra config loader and the API schema have no coupling-model field, so nothing changes there and the OpenAPI/SDK types stay the same. `"schematic"` stays available as an opt-in.
- **[P1-03] Units.** Everything inside the engine is in reduced-Planck units (M_Pl = `M_PL_GEV` = 2.4352e18 GeV = 1; the LEDGER's 2.44e18 is the same constant to three figures). Two mixed-unit uses in M7 were found and fixed at the API boundary:
  - `reheating.Gamma_phi`: the UI labels it "[GeV]", but it was passed raw to M1, which works in M_Pl. It is now divided by `M_PL_GEV`.
  - The schematic CS term used θ_grav/f_a with f_a in GeV. It now uses f_a/`M_PL_GEV`.
  - M2's potentials were already all in M_Pl units, so no change there. `couplings.py` already converted `couplings.f_a` with `M_PL_GEV`.
  - Outside this lane's scope (M4), recorded for P1-04: `m4_anomaly` divides an M_Pl-unit source by `T_reh_GeV**3`, which mixes units.
- **[P1-03] Mapping to Kawai & Kim.** It is recorded in the `couplings.py` docstring.
  - GB: −½ξ(φ)R²_GB ≡ −(1/16)ξ_KK R²_GB, so ξ = ξ_KK/8. ξ_KK = −δ ln[2e^φ η⁴(ie^φ)] with δ = −1, and ξ_KK′ = −δ[1 − (π/3)e^φ E₂(ie^φ)].
  - CS: (1/16)ϑRR̃, so f = ϑ/2, with ϑ = γφ and γ = 1. That means θ_grav/f̂_a = γ/2.
  - `xi` is UCGLE-F1's linear ξ(φ) = xi·φ. It stands for ξ_KK′/8 over the window, but it has no ξ_KK″ term. This is a model difference, not a fit.
  - `M_star`, `M1` and `S_E2` have no counterpart in the tensor action, and M1–M6 do not read them.
  - Kawai & Kim's equation numbers beyond Eq. 2 are still unverified, because arXiv is unreachable from the sandbox.
- **[P1-03] Natural benchmark.** New module `m2_scalar/natural.py`, with slow-roll closed forms for V = Λ⁴(1 − cos φ/f_a). M2's minus sign is the paper's "±" under φ → φ + πf_a.
  - f_a = 8.7, A_s = 2.207e-9, N_e = 60 give Λ = 7.1154324599829784e-3 M_Pl and m = Λ²/f_a = 5.82e-6 M_Pl. Decision 11 quotes m ≈ 5e-6; at one significant figure the computed value rounds to 6e-6, and it is reported as computed.
  - The test reproduces A_s to 1e-9 through M2's compiled V and V′, with a root-found φ_end and the N integral done by quadrature, independently of the closed form.
- **[P1-03] Initial field for `natural`.** φ₀ = min(φ_*(N_e = 60), πf_a(1 − 10⁻⁶)).
  - For the benchmark's f_a = 8.7, the old hilltop start (≈ 1650 e-folds) never ends inflation within the trajectory's N_max = 80, so φ₀ is now the N_e = 60 pivot.
  - For f_a ≲ 1 (the audit conftest's f_a = 1), φ_*(60) is within 1e-13 of the hilltop. The old hilltop bound still applies, so audit behaviour is unchanged.
- **[P1-03] `A_END_H_END` is derived, and it does not cancel.**
  - Its value is −1/`M3_TAU_END["high"]` = 10³: the end of inflation (ε = 1) is the last point of M3's high-precision τ window, and τ(N_end) = −1/(a_end H_end).
  - The normalisation of a is a gauge freedom. Under a → ca, τ → τ/c and k → ck, the coefficients scale as B → c²B, A·k → c²A·k and C → C, so |β|² depends only on k/(aH). A unit test checks this scaling for c = 0.1 and 10, and another checks the window condition.
  - What it fixes is the unit of M3's comoving k: k_M3 = 1 is k = 10⁻³ a_end H_end.
  - **Assumption (recorded, not derivable here):** M3's τ grid (−5 → {−1, −0.1, −1e-3}) and k grids (10^±1, ±2, ±3) are the pipeline's pre-existing design, not values from the paper. Whether Kawai & Kim's relevant band matches them needs the paper. The τ-grid constants now live in one place (`couplings.M3_TAU_START` and `M3_TAU_END`), which the pipeline imports.
- **[P1-03] Fixture.** `public/fixtures/runs/kawai-kim-natural.json`: potential params `{f: 7e16, Lambda4: 2.5e-7}` → `{f_a: 8.7, Lambda: 0.0071154324599829784}`, and top-level `"synthetic": true` added.
  - The JSON diff touches only those five paths. All result fields are byte-for-byte unchanged (R7).
  - The couplings (`xi` 0.0085, `theta_grav` 0.78, `f_a` 1e16 GeV, `M_star`, `M1`, `S_E2`) are UCGLE-F1's own parameters. Decision 11 keeps them, so they are not changed. The paper's δ and γ are mapped in the docstring rather than turned into new values.
- **[P1-03] CI.** `backend-slow` now runs `pytest -q -m slow` with no `--deselect`. The `known-gap` job is removed.
- **[D13a] Badge placement.** The cosmology run views are the visualizer pages (in the default build, cosmology has no `/domains/.../runs` fixtures; `DOMAIN_FIXTURE_INDEX["cosmology.ucglef1"]` is empty).
  - Run list: on the `/visualizer` card of each run whose bundled run fixture is flagged.
  - Run detail header: the visualizer toolbar lead (`data-testid="cosmology-run-header"`).
  - Home: the F1 summary card header (`data-testid="f1-summary-header"`), which shows the V2 fixture's coupling numbers. It is shown while the form's couplings equal the fixture's, and disappears once the user edits them away.
  - The flag comes from the new `getRunFixtureSummary(id)` in `services/simulator.ts`. It is fixture-mode only, reads the bundled file with no DB backfill, and returns `null` with `VITE_API_URL`. It was appended at the end of the file so it does not touch the API-mode branch.
  - `RunResultShape` declares `synthetic: z.boolean().optional()` (it already passes unknown keys through), and `RunResult.synthetic?` is typed.

## Corrected tests (old → new)
- `backend/tests/test_qcompass_adapter.py::test_adapter_matches_direct_pipeline_eta_b`. The regression snapshot `test_adapter_matches_direct_pipeline_eta_b.yml` changes:
  - `F_GB: 0.6727334345929941` → `0.6727340798350541`;
  - `audit_passed: 9` → `10`;
  - `audit_total: 15`, `eta_B: NaN` and `eta_B_is_nan: true` are unchanged.

  Why the old values no longer apply: they were the schematic placeholder couplings on the old, un-evaluable parameterisation. Under the physical default, S6 (adiabatic residual) goes from FAIL to PASS_P; every other verdict is the same. The test also gains an assertion that the fixture is M2's natural potential with `kawai_kim_natural_params()` and that the pipeline default is `physical` (tightening).
- `…::test_validate_returns_relative_error`. Same added parameterisation assertion. Its old assertions are unchanged (under the physical default it previously failed with "potential parameters missing").
- `…::test_v2_provenance_sidecar_classical_run_fields`. Same as above.
- The module docstring's NaN paragraph no longer says "schematic A/B coupling profile". The parked `xfail` (V2 η_B) is untouched (R4: only P1-08 removes it).
- `src/lib/__tests__/syntheticFixtures.test.ts`: its comment "Cosmology fixtures … are out of scope here (R19)" is replaced by the new cosmology V2 block. No assertion was removed.

## Removals
- The `known-gap` CI job ("known gap: GB→0 decoupling (P1-03, not required)"). Replaced by the `backend (slow audits)` job, which now runs `test_gb_to_zero_decoupling` as a required test (no `--deselect`).
- `tau_span_end` in `pipeline.py`. Replaced by `couplings.M3_TAU_END`, with the same values.

## Follow-ups for the coordinator
- `src/lib/configDefaults.ts`, `public/fixtures/benchmarks.json` (the two natural entries), `public/fixtures/runs/gb-off-control.json`, `public/fixtures/artifacts/*/config.yaml` and `src/lib/potentialEvaluator.ts` still use the frontend's `{f, Lambda4}` natural keys, which M2 does not define.
  - With `physical` as the default, a live API run of the UI's natural default fails with "potential parameters missing: ['f_a', 'Lambda']". The schematic path never evaluated V, so this was latent before.
  - Fixing it touches the home configurator and its R19 screenshot and the API-mode path owned by another lane, so it is left out of this lane.
- The other cosmology run fixtures (`starobinsky-standard`, `gb-off-control`, `failing-run`) carry hand-written results too. Decision 13 names only `kawai-kim-natural`, so they are not flagged here.

## R19 (Decision 13a): visible differences, branch vs control
The committed baselines fail locally even without this change: the control run at `origin/build/w1-foundations` fails all three screenshots too, because the sandbox's Chromium build and fonts differ from CI's. So the badge diff was isolated by comparing this branch's render with a control render of `origin/build/w1-foundations` made in the same sandbox (Chromium, 1440×900). Every differing pixel falls in one region per page:
- **`/` (cosmology-default.png)**, region y183–583 × x329–1119:
  1. The badge "Synthetic fixture — not a computed result" appears under the "F1 — primary mechanism" title.
  2. The F1 equation box, its footnote and the F1 card's bottom edge move down by the badge's height (≈ 28 px).
  3. The "Active context" card moves down by the same amount.
- **`/visualizer` (cosmology-visualizer-index.png)**, region y225–504 × x221–1219:
  1. The badge appears in the `kawai-kim-natural` card.
  2. The first row of cards (all three) grows by the badge's height.
  3. The second row (f2, f3, f5) and the third row (f7) move down by the same amount.
- **`/visualizer/kawai-kim-natural`**, region y60–100 × x199–625:
  1. The badge appears in the toolbar after the run id `kawai-kim-natural`.
  2. The "↔" glyph and the "Compare with…" picker move right by the badge's width.

  The six panels are unchanged.

No other pixel differs. The rebaseline is the coordinator's dispatch of `e2e-baselines.yml` on `build/w1-physics`; `R19.sha256` and the PNGs are not touched here.
