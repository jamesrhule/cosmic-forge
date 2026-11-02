# W1 — potential-parameter boundary (Gate 1)

Branch `build/w1-platform`, on top of `build/w1-foundations` at `040bc36`. Lane notes: `docs/build/lanes/W1-platform.md`, section "W1 potential-parameter boundary (Gate 1)".

## Root cause

The frontend and M2 named the potential's parameters differently, and the frontend used GeV where M2 uses M_Pl:

| kind | M2 (`m2_scalar/potentials.py`) | Configurator on 040bc36 (`configDefaults.ts`) |
|---|---|---|
| starobinsky | `M` [M_Pl] | `M: 1.3e-5` (same) |
| natural | `f_a`, `Lambda` [M_Pl], V = Λ⁴(1 − cos φ/f_a) | `f: 7e16` [GeV], `Lambda4: 2.5e-7` [M_Pl⁴] |
| hilltop | `V0`, `mu` [M_Pl], V = V0(1 − (φ/μ)⁴) | `mu: 1e16` [GeV], `p: 4`; no `V0` (the preview hard-coded 1e-7) |

Before Decision 11, the schematic coupling model never evaluated V, so the mismatch was latent. With `coupling_model="physical"` the default, `coupling_profile` compiles the potential and binds its parameters, and an API run of the V2 default failed in the worker with `potential parameters missing: ['f_a', 'Lambda']`. The run route did not validate the problem at submit, so it answered 202 and the run then failed.

The same check on every config the frontend can send, run on 040bc36 against 040bc36's own sources (`PYTHONPATH=<040bc36>/backend/src`, through `CosmologyManifest` → `to_run_config` → `compile_potential` → `potential_args`), gives 9 of 15 failing:

```
PASS defaultsForPotential(starobinsky)
FAIL defaultsForPotential(natural): ValueError: potential parameters missing: ['f_a', 'Lambda']
FAIL defaultsForPotential(hilltop): ValueError: potential parameters missing: ['V0']
FAIL kawaiKimDefaults(): ValueError: potential parameters missing: ['f_a', 'Lambda']
FAIL benchmarks.json:bench-kawai-kim: ValueError: potential parameters missing: ['f_a', 'Lambda']
PASS benchmarks.json:bench-starobinsky
FAIL benchmarks.json:bench-gb-off: ValueError: potential parameters missing: ['f_a', 'Lambda']
PASS benchmarks.json:bench-adshead
FAIL runs/failing-run.json: ValueError: potential parameters missing: ['V0', 'mu']
FAIL runs/gb-off-control.json: ValueError: potential parameters missing: ['f_a', 'Lambda']
PASS runs/kawai-kim-natural.json
PASS runs/starobinsky-standard.json
FAIL artifacts/gb-off: ValueError: potential parameters missing: ['f_a', 'Lambda']
FAIL artifacts/kawai-kim: ValueError: potential parameters missing: ['f_a', 'Lambda']
PASS artifacts/starobinsky
9 of 15 fail
```

## Fix

- **Wire shape.** The API carries the parameters in the Configurator's units, with one table of names and units: `ucgle_f1.domain.POTENTIAL_PARAM_FORMS`. Natural also keeps M2's own names, which Decision 11's fixture and the audits use, and a dict must use one of the two. The boundary is the backend request model, and the conversion is `Potential.engine()`, which uses the one `M_PL_GEV`:
  - f_a = f / M_Pl;
  - Λ = Λ⁴^(1/4);
  - μ = mu / M_Pl.

  It runs at the pipeline's M2 step, beside the physics lane's Γ_φ conversion, and is idempotent (`EnginePotential`).
- **Validation.**
  - `domain.Potential` refuses mixed forms, unknown names, non-finite values, non-positive scales and a bad `p`.
  - `CosmologyPotential`, the run route's model and a subclass of `domain.Potential`, requires every parameter of the chosen form.
  - `POST /api/qcompass/domains/{d}/runs` calls the plugin's `validate_problem` before enqueueing, and a failure is 422 `INVALID_INPUT` with a message naming each problem.
  - `POST /api/runs` answers 422, not 500.
- **Hilltop.** V0 is a Configurator field, defaulting to 1e-7 M_Pl⁴ (what the preview always drew). The API never supplies one. M2's hilltop is V0(1 − (φ/μ)^p) for an integer p from 2 to 64, default 4, and p = 4 builds the original expression symbol for symbol.
- **SDK.** `Potential.params`' OpenAPI schema lists each kind's forms with units, and the SDK was regenerated. `simulator.ts` checks its problem with `satisfies sdk.RunConfig`.
- **Frontend.**
  - Defaults moved to `src/lib/configDefaults.json`, which `configDefaults.ts` imports and the backend test reads. The natural default, Starobinsky default and V2 couplings are unchanged.
  - The preview reads V0.
  - `failing-run.json`'s hilltop config gets real hilltop parameters.

## Tests (every new test file fails on 040bc36 and passes after)

"Before" = the new test files copied into a detached worktree at 040bc36 and run there against its sources (same venv, `PYTHONPATH=<040bc36>/backend/src`; the vitest file likewise).

| Test | 040bc36 | After |
|---|---|---|
| `backend/tests/test_frontend_potential_configs.py` (30): 15 frontend configs accepted + compiled with all parameters bound (`defaultsForPotential` × 3 kinds, `kawaiKimDefaults()`, `benchmarks.json` × 4, `runs/*.json` × 4, artifact YAML × 3), 3 YAMLs through `hydra_cfg.load_config`, defaults-from-JSON guard, source-coverage guard, HTTP: V2 default 202, bad natural params 422 × 6, hilltop without V0 422, agent route 422, custom snippet refused | collection error (`configDefaults.json` absent, no `validate_problem`); the equivalent probe above: 9 of 15 configs fail | 30 passed |
| `backend/tests/unit/test_potential_params.py` (23): f = 7e16 GeV → f_a = 7e16 / M_PL_GEV (= 0.028745072273324573), Λ⁴ = 2.5e-7 → Λ = 2.5e-7^(1/4) (= 0.022360679774997897, Λ⁴ recovered to 1e-15), hilltop μ / M_PL_GEV, M_Pl-unit parameters pass through as the same objects, idempotence, 11 refusals with their messages, missing-parameter names, hilltop p = 4 symbol-for-symbol and bit-identical V/V′/V″, p = 6 | collection error (`EnginePotential` absent) | 23 passed |
| `src/lib/__tests__/configDefaults.test.ts` (4) | 2 failed (hilltop V0; preview reads V0), 2 passed (R19 natural default; fresh objects) | 4 passed |
| The 6 corrected route-contract tests (L2, L4, A7 × 2, A8 × 2; lane notes): an empty cosmology problem replaced by a complete one, assertions unchanged | pass with the old bodies; the new bodies also pass (6 passed) | pass |

## Suites

All run in this sandbox on the final tree.

| Check | Result |
|---|---|
| Backend fast: `cd backend && uv run --frozen pytest -q -m "not slow"` | 528 passed, 2 deselected, 1 xfailed (the pre-existing V2 η_B xfail) |
| Backend slow: `-m slow` | 2 passed: `audit/physics/test_parity_hypothesis.py::test_gb_to_zero_decoupling` and `tests/test_qcompass_adapter.py::test_adapter_standard_precision_runs` |
| `bun run test` (vitest) | 21 files, 116 tests passed |
| `bunx tsc --noEmit` | exit 0 |
| `bun run lint` | exit 0 (0 errors; the same 15 pre-existing warnings, none in changed files) |
| `bunx prettier --check .` | all files formatted |
| `bun run build` (default flags, and with all domain flags, via `scripts/e2e_serve.sh`; with `VITE_API_URL`, via `scripts/e2e_live_serve.sh`) | built, and served on workerd |
| `scripts/check_r19.sh` | 9 PNGs match `R19.sha256` |
| `scripts/gen_sdk_types.sh --check` | "SDK types match the API's OpenAPI document." |
| `uv lock --check` | lock is current |
| Playwright Chromium: `e2e/smoke.spec.ts`, `e2e/synthetic-fixture-badge.spec.ts` (`PW_CHROMIUM_PATH=/opt/pw-browsers/chromium`) | 15 passed |

The existing engine-form results are unchanged. The adapter's `data_regression` snapshot (`test_adapter_matches_direct_pipeline_eta_b`) passes as committed, and so do the audits, which use M2's natural names and Starobinsky, and `test_gb_to_zero_decoupling`.

## e2e-live

Run: `bunx playwright test -c playwright.live.config.ts` with `PW_CHROMIUM_PATH=/opt/pw-browsers/chromium`. The stack was `scripts/live_stack.py`, with the harness's own Postgres 16, and the web was `scripts/e2e_live_serve.sh`, built with `VITE_API_URL`.

| Tree | API, worker up | cosmology (V2 defaults, "fast") | chemistry H2 | Worker log for the cosmology job |
|---|---|---|---|---|
| 040bc36 backend (`PYTHONPATH=<040bc36>/backend/src`), same web build; the request is identical, because the natural default is unchanged | — (cosmology only, `-g cosmology`) | **fails**: status `failed` | — | `ValueError: potential parameters missing: ['f_a', 'Lambda']` |
| this branch | passed | **fails**: status `failed` (queued → running → failed; 202 at submit) | passed | `ValueError: trajectory covers τ ≥ -0.0013 only; M3 needs τ ≥ -5.0` |

So the parameter blocker is fixed: the request is accepted, converted (f_a = 0.028745 M_Pl, Λ = 0.022361 M_Pl) and run. **The spec still fails**, because the Configurator's V2 default does not inflate under the physical coupling model. With f_a ≈ 0.029 M_Pl, |η| ≈ 1/f_a² ≈ 1200, so inflation ends within about one e-fold of the start, and M3's τ window (τ from −5) needs about 8.5. That is `BLOCKED-ON-JAMES:ui-v2-defaults-vs-paper-benchmark` (lane notes). Changing the displayed defaults needs an R19 rebaseline that Decision 13 does not authorise, and changing the spec's input would be a test change. Neither was done.

The same live API, with the configs submitted one at a time (the free plan allows one concurrent job):

```
V2 default (Configurator): HTTP 202 qc_cosmology_2060d35f392b -> failed
option (a): paper benchmark in Configurator units: HTTP 202 qc_cosmology_84a8e3de09b7 -> completed, eta_B=NaN
option (b): Configurator Starobinsky default: HTTP 202 qc_cosmology_4bc2fd3bf994 -> completed, eta_B=NaN
ambiguous: both natural forms: HTTP 422 INVALID_INPUT: invalid cosmology problem: potential: natural potential: ambiguous parameters ['Lambda', 'Lambda4', 'f', 'f_a'] mix the configurator form (f, Lambda4) with the M2 form (f_a, Lambda); send one form
hilltop without V0: HTTP 422 INVALID_INPUT: invalid cosmology problem: potential: hilltop potential: missing V0 [M_Pl^4]; hilltop takes V0 [M_Pl^4], mu [GeV], p [1] (configurator form), plus optional phi0 [M_Pl]
```

So the two options in the lane notes both complete through the platform path. Option (a) is the paper benchmark in the Configurator's units, which converts back to f_a = 8.7 and Λ = 0.0071154324599829784 exactly. Option (b) is the Starobinsky default. Both give η_B "NaN" from the 0.5 % budget gate at "fast", which the spec accepts as a stored non-finite marker. The 422s carry clear messages.

In-process (the same pipeline, `RunPipeline().run`, precision "fast"):

```
FAILS      UI V2 default natural {f: 7e16 GeV, Lambda4: 2.5e-7}: ValueError: trajectory covers τ ≥ -0.0013 only; M3 needs τ ≥ -5.0 engine={'f_a': 0.02874507227332457, 'Lambda': 0.022360679774997897}
COMPLETES  paper benchmark, configurator units {f: 8.7*M_Pl GeV, Lambda4: Lambda^4}: eta_B=nan (12.0s) engine={'f_a': 8.7, 'Lambda': 0.0071154324599829784}
COMPLETES  UI starobinsky default {M: 1.3e-5}: eta_B=nan (10.8s) engine={'M': 1.3e-05}
FAILS      UI hilltop default {V0: 1e-7, mu: 1e16 GeV, p: 4}: ValueError: trajectory covers τ ≥ -0.0247 only; M3 needs τ ≥ -5.0 engine={'V0': 1e-07, 'mu': 0.004106438896189225, 'p': 4.0}
```

## R19 pixel comparison

The question: does this change add any pixel difference on the three R19 pages relative to 040bc36? The committed baselines can't answer it locally, because sandbox fonts differ and the D13a badge rebaseline is pending.

- **040bc36.** A detached worktree at 040bc36 (sharing `node_modules`; `package.json` and `bun.lock` are identical) was built with `bun run build` (default flags) and served on workerd (`wrangler dev`, port 4410).
- **This branch.** `scripts/e2e_serve.sh` built and served the branch's default build on port 4310.
- **The comparison.** A scratch Playwright spec (never committed, in the session scratchpad) used the same routes, readiness checks, motion freeze and footer mask as `e2e/cosmology-byte-identity.spec.ts`, but `maxDiffPixels: 0, threshold: 0`. Chromium was `/opt/pw-browsers/chromium`. It first wrote the 040bc36 renders as baselines (`--update-snapshots`), then re-rendered 040bc36 against them, then rendered the branch against them.

| Page | 040bc36 render sha256 | 040bc36 vs itself | branch vs 040bc36 |
|---|---|---|---|
| `/` (`cosmology-default.png`) | `c7241c10d5655712fba80905314fb61a2736d2b84281fd4ddddf451f0b796265` | identical | **identical (0 pixels)** |
| `/visualizer` (`cosmology-visualizer-index.png`) | `c7beb300ad0fdf8515919533ecc16c475f7b6cd14f38e1b4d243d1666311d4b3` | identical | **identical (0 pixels)** |
| `/visualizer/kawai-kim-natural` | `2f3c3daa23b692379932d6b2c869162815eea81db0b49ff4e8e93df42e2e88b0` | identical | **identical (0 pixels)** |

The configurator on `/` renders the natural default's labels `f` and `Lambda4`, its values 7e16 and 2.5e-7, the V(ψ) preview, and the kind hints (hilltop's "μ, p" unchanged). All of them are unchanged. `scripts/check_r19.sh` passes: 9 PNGs match `R19.sha256`, and no PNG or `R19.sha256` was touched.
