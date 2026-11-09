# W1 round 3B, lane API3: evidence

Branch `build/w1-api3`, based on `15e4e3c`. Lane notes (item IDs, decisions,
corrected tests, routing): `docs/build/lanes/W1-api3.md`.

**Method (LEDGER Decision 14).**
- One regression test per finding, driving HTTP or functions that existed on `15e4e3c` (`_custom_expr`, `compile_potential`, `RunPipeline`/`build_run_result`/`eta_B_refusal`, `scan_parameters`, the approval store). Each was run against `15e4e3c` and fails there for the finding's own reason; all pass on this branch.
- Where a test can only exist after the fix (a new module), it is marked as a post-fix guard, and the base-tree failure is listed but not counted.
- No database policy changed; no migration was added or edited.

**How "before" was measured.**
- Tree: `git worktree add --detach … 15e4e3c` under `scratchpad/round3b/api3-before` (removed afterwards).
- Python: this branch's venv, with `PYTHONPATH` set to that tree's `backend/src` and `packages/qcompass-core/src`, so its sources shadow the editable installs; the test files copied in under a `_r3b_` prefix (plus `api3_compile_helpers.py`), then deleted.
- The two tests whose request never answers on `15e4e3c` leave a spinning API thread behind, so they were run one at a time with a scratch plugin that prints the call-phase report and exits.

**Versions (R17).** Python 3.12.13, sympy 1.14.0, mpmath 1.3.0, numpy 2.2.6, scipy 1.18.1, SQLAlchemy 2.1.6, psycopg 3.3.6, pydantic 2.14.2, FastAPI 0.162.0, pytest 9.2.0, PostgreSQL 16.15, bun 1.4.4, Playwright 1.59.1 (Chromium at `PW_CHROMIUM_PATH=/opt/pw-browsers/chromium`).

## Reproduced on 15e4e3c before fixing

- **c3-expr-caps / API-COMPILE.** The verifier's `scratch-verify-WORKER/expr_probe.py` with its `cases1-3.txt` (4 s limit per case) on `15e4e3c`: `sin(exp(1e30))`, `sin(exp(1e6))`, `sin(exp(exp(30.0)))`, `sin(9**(1/(1.0000001-1.0)))`, `phi**2 + cos(exp(exp(30.0)))`, `sin(exp(1e7))`, `sin(sinh(1e30))`, `cos(cosh(1e3*1e3))`, `sin(exp(2e6))`, `tanh(sin(exp(1e30)))` hung; `exp(1e30)`, `sinh(1e30)`, `sqrt(exp(1e30))`, `exp(1e30)*phi**2` and `sin(1e30*…*1e30)` (30 factors) were accepted. Two further classes of bypass were found the same way (`scratchpad/api3/cases_cplx.txt`): an imaginary argument makes sin/cos into sinh/cosh, so `sin(cos(1e6*sqrt(-1)))`, `sin(sin(1e6*sqrt(-1.0)))` and `sin(sin(1e3*sqrt(-1.0)*1e3))` hung; and Python reads `1e-1000` as 0.0 while sympy reads 1.0e-1000, so `exp(1/1e-1000)` and `sin(1/1e-100000)` were accepted. Five of them are in the regression test.
- **CRITIC-SUBMIT.** `scratchpad/api3/probe_exc.py` ran `validate_problem` on 27 odd custom potentials in spawned children on `15e4e3c`: a parameter named `phi` raised `SyntaxError: duplicate argument 'phi' in function definition` (lambdify); `log(0)*phi`, `0**-1` and `phi**2/0` raised `KeyError: 'ComplexInfinity'`. Both escape the route's `except ValueError` (500).
- **PHYS3-ZERO.** On `15e4e3c`, the Kawai–Kim benchmark with ξ = 1e-2, θ_grav = 0, precision fast publishes `RunResult.eta_B = 0.0 ± 0.0` with `eta_B_refusal` returning None (the regression test's own failure message, below).
- **PHYS3-NIT.** Negating B and C in `coupling_profile` on `15e4e3c`: `test_gb_signal.py` and every `test_couplings.py` test except one still pass; the one that fails, `test_parity_flip_swaps_helicities_exactly`, fails on an exact-equality detail (1 of 8 modes differs by 1.2e-29 between the θ and −θ runs), not on the sign. So the verifier's point holds: nothing pins the sign of B or C.
- **SF6.** The verifier's mutation (`scratch-c7/sf6_mutation.py`: `pool_recycle=300, pool_timeout=5, connect_args={'prepare_threshold': None}` on `qcompass_core`'s engine only) leaves the three existing SF6 tests green (see SF6 below).
- **R2-START-ORDER.** On `15e4e3c`, `scan_parameters` consumes its approval in its first statement, before building any cell.

## Per item

| ID | Fix (lane notes have the detail) | Regression test(s) | 15e4e3c (reason) | After |
|---|---|---|---|---|
| D17 | `_custom_expr` accepts one expression in φ or `def V(<name>): return <expr>` (`_function_return`: shape checks, docstring allowed, parameter renamed to φ, colliding free `phi` refused); every other shape is a ValueError naming the canonical form; the extracted expression goes through the same `_check_shape`/`_Checker`/`_build` | `test_api3_submit_checks.py::test_d17_accepted_snippets_compile_to_the_canonical_expression` (5: canonical, `def V(psi)`, `def V(phi)`, docstring first, comments; `srepr` equal to the canonical expression); `::test_d17_any_other_snippet_is_refused_naming_the_canonical_form` (21: multiple statements, assignment (main's default snippet), if, loop, lambda assignment, lambda expression, `return lambda`, two params, default arg, decorator, nested def, no return, bare return, wrong name, `phi` collision, annotations, `*args`, keyword-only, `async def`, def + a call, syntax error); `::test_d17_the_route_takes_def_v_and_answers_any_other_body_with_a_422_naming_the_canonical_form` (HTTP 202 / 422 INVALID_INPUT, and MCP `validate_config` on `potential.customPython`) | 26 failed, 1 passed (the canonical case): every `def` snippet was refused as "customPython must be one expression in phi (invalid syntax, line 1)", without the reason or the `def V` form. A decision, not a bug: not counted as a regression test | 27 pass |
| c3-expr-caps | Float bounds (`prec`, precision-derived cancellation bound, literal magnitude from sympy's Float), `cplx`/`nonneg` tracking, exp/sinh/cosh (and sin/cos/tanh of a complex argument) argument ≤ ln(float64 max), every subexpression ≤ float64 max | `::test_c3_float_bombs_are_refused_quickly` (20 payloads, each in a subprocess with a 20 s limit: the verifier's 15 and this lane's 5) | 20 failed: 7 "did not finish: sympy evaluated an unbounded Float" (20 s), 13 accepted (`exp(1e30)`, `sinh(1e30)`, `sqrt(exp(1e30))`, `exp(1e30)*phi**2`, `sin(exp(1e6))`, `sin(exp(2e6))`, `cos(cosh(1e3*1e3))`, the 30-factor product, `sin(cos(1e6*sqrt(-1)))`, `sin(sin(1e3*sqrt(-1.0)*1e3))`, `sin(1e30*sqrt(-1.0))`, `exp(1/1e-1000)`, `sin(1/1e-100000)`: each builds a number beyond float64, most of them seconds of mpmath work) | 20 pass, each rejected in < 0.4 s |
| | | `::test_c3_a_float_bomb_at_submit_is_a_quick_422_and_the_api_stays_responsive` (HTTP, the verifier's `phi**2 + sin(exp(1e30))`) | failed: "no answer within 30 s: the API evaluated an unbounded Float" (call phase 41.1 s: the 30 s wait plus ~10 s for `/healthz` on the same process) | pass: 422 "exp() of argument up to 10**30: it must satisfy \|x\| <= 709.783 (float64 overflows beyond it)" |
| (guard) | Real potentials keep compiling | `::test_c3_float_caps_keep_real_potentials` (24 potentials, incl. Float sums in denominators); the existing `test_security_gate1_worker.py::test_c3_expr_caps_real_potentials_compile_as_before` (`srepr` equality, 12) | 24 passed (no-change guard) | pass |
| API-COMPILE | `m2_scalar/check.py::check_potential`: custom potentials compile in a spawned child, killed at 10 s, `RLIMIT_CPU`, `PR_SET_PDEATHSIG`, ≤ 4 at once; confinement shared with the worker (`proc_limits.py`) | `::test_submit_compile_of_a_custom_potential_is_stopped_at_its_time_limit` (HTTP; the compile step replaced by `api3_compile_helpers.spin_compile`, a 120 s busy loop, at its home `potentials.compile_potential` and at the base tree's import in `adapters.qcompass`; limit set to 2 s) | failed: "no answer within 30 s: the compile ran in the API process without a limit" | pass: 422 "compiling it did not finish within 2 s, so it was stopped", answered in < 15 s, `/healthz` < 1 s meanwhile, no child left |
| | Post-fix guards (the module is new) | `::test_submit_compile_child_is_cpu_limited_and_dies_with_the_api` (child reports `RLIMIT_CPU` = (15, 20) and ppid = the API process); `::test_submit_compile_waits_for_a_free_slot_within_its_limit` | failed: ImportError (`ucgle_f1.m2_scalar.check`), expected for a guard | pass |
| CRITIC-SUBMIT | `validate_problem` maps any exception to ValueError; `compile_potential` refuses `phi` as a custom parameter and non-finite V/V′/V″ by name; `validate_config` reports missing parameters and `check_potential` refusals; MCP `validate_config` answers `ValidationError` with diagnostics | `::test_critic_compile_errors_are_422_not_500` (HTTP: `phi` as a parameter, `log(0)*phi`, `phi**2/0`) | 3 failed: `SyntaxError: duplicate argument 'phi' in function definition`, `KeyError: 'ComplexInfinity'` ×2 raised out of the route (a 500) | pass: 422 INVALID_INPUT with the reason |
| | | `::test_critic_api_runs_refuses_an_incomplete_potential_before_spending_the_token` (HTTP `POST /api/runs`: hilltop without V0, custom without phi0, a float bomb; then the same token starts a complete run) | failed: hilltop `{mu, p}` answered 200 with a run id | pass: three 422s, no run row, then 200 |
| | | `::test_critic_validate_config_reports_missing_parameters_and_compile_failures` (HTTP MCP: hilltop without V0, an unbound custom parameter, custom without phi0) | failed: `valid: True, diagnostics: []` | pass: valid False, one error each at `potential.params` / `potential.customPython` |
| | | `::test_critic_mcp_validate_config_answers_a_refused_config_with_diagnostics` (HTTP MCP: natural with both parameter forms) | failed: pydantic `ValidationError` out of the route (a 500) | pass: 200, valid False, "ambiguous" diagnostic |
| R2-START-ORDER | `scan_parameters` builds and validates every cell (`_scan_cells`) before consuming the approval | `::test_r2_scan_parameters_validates_before_spending_the_token` (incomplete hilltop base, unknown axis path, log axis through 0; each must keep its token; then a one-cell KK scan spends it) | failed: "the refused scan spent the token (ValueError: potential parameters missing: ['V0'])" | pass |
| PHYS3-ZERO | `AnomalyResult.adiabatic_subtraction_implemented` (M4 reports `ADIABATIC_SUBTRACTION_IMPLEMENTED = False`); `eta_B_refusal` refuses on it after its three existing conditions | `tests/unit/test_m4_units_and_refusal.py::test_a_zero_source_run_does_not_publish_eta_b_zero` (real pipeline: KK benchmark, ξ = 1e-2, θ_grav = 0, fast) | failed: "published eta_B = 0.0 ± 0.0 for a zero source" | pass: NaN ± NaN, reason "M4 does not yet apply the adiabatic subtraction to ⟨RR̃⟩ (P1-04)", S8/S14 FAIL with value None |
| | Rule and flag | `::test_eta_b_refusal_rule` (corrected, lane notes: four new assertions), `::test_m4_reports_that_it_has_not_applied_the_adiabatic_subtraction` (post-fix guard) | failed on the new assertions (`'adiabatic subtraction' in None`) and AttributeError, expected | pass |
| PHYS3-NIT | Independent coefficient test | `tests/unit/test_coupling_coefficients.py` (A, B, C at six τ: same sign, rel 1e-4; a(τ) rel 1e-5; benchmark guard) | 5 passed: not a bug, a missing test. Mutation (B and C negated in `coupling_profile` on `15e4e3c`): `[B]` and `[C]` fail with "B(τ=-4.0): sign -9.524486e-15 vs +9.524530e-15" | 5 pass (measured agreement: A ≤ 3.8e-6, B ≤ 1.2e-5, C ≤ 6.7e-8, a ≤ 7e-7) |
| SF6 | `ENGINE_KWARGS` once per module (`ucgle_f1.db.engine`, `qcompass_core.db`) | `tests/test_security_gate1.py::test_sf6_engines_share_their_create_engine_kwargs_pool_and_connect_args` | not applicable (a test-strength finding; on `15e4e3c` it fails with AttributeError, no constant). Mutation on this branch (the verifier's one-sided `pool_recycle=300, pool_timeout=5, connect_args={'prepare_threshold': None}` in `qcompass_core.db`): the 7 existing SF6 tests pass, the new one fails on the kwargs comparison | pass |

## The verifiers' repros against this branch

- `expr_probe.py` on `cases1-3.txt` plus this lane's complex/tiny-literal cases (47 cases, 4 s each): every bomb is rejected in under 0.4 s, including the process start-up; the accepted ones are `phi*sin(1e30*…)` (10 factors, 1e300 < float64 max), `cos(pi*Rational(1,257))` and `cos(pi*Rational(9…9, 9…7))`, all cheap. Output: `scratchpad/api3/probe_after.out`.
- `http/test_api_expr_dos.py` (HTTP, 4 payloads): every request answers within 1.7 s and `/healthz` within 0.01 s. `phi**2 + sin(exp(1e30))` and `phi**2 + cos(exp(exp(30.0)))` are 422 (float64 exponent range), `phi^(9^9^9)` is 422 (`^`). The verifier's control `phi**2 + sin(1.0)` (no `phi0`) is now 422 "custom potentials need params['phi0']": CRITIC-SUBMIT refusing a potential the worker cannot start, as intended.

## Suites

Run once at the end, on `1ecec3c` (code) with this evidence file uncommitted. Raw outputs are under `scratchpad/api3/` (`suite_*.out`, `fe_*.out`, `pw_smoke.out`).

| Check | Result |
|---|---|
| backend fast: `cd backend && uv run --frozen pytest -q -m "not slow"` | 791 passed, 3 deselected, 1 xfailed (the pre-existing V2 xfail), 354 s, exit 0 |
| backend slow: `-m slow` | 3 passed, 792 deselected, exit 0 |
| frozen audit fast (the drift-alarm step): `cd backend && PYTHONPATH=src uv run pytest audit -q -m "not slow"` | 92 passed, 1 deselected, exit 0 |
| frozen audit slow: `… pytest audit -q -m slow` | 1 passed (`test_gb_to_zero_decoupling`), exit 0 |
| drift-alarm dirhash of `backend/audit/physics` | `42805c73538df5eb0f9eb109ead9a541253d5371d71eac5ea04be0ffaf8e92dd`, equal to `golden.lock`; `backend/audit/physics` and `golden.lock` untouched |
| `uv run --frozen pytest packages -q --import-mode=importlib` | 350 passed, 7 skipped, exit 0 |
| `bun run lint` | 0 errors, 15 warnings (pre-existing react-refresh warnings) |
| `bunx prettier --check .` | all files formatted |
| `bunx tsc --noEmit` | clean |
| `bun run test` (vitest) | 22 files, 119 tests passed |
| `bun run build` | built |
| `scripts/check_r19.sh` | 9 PNGs match `R19.sha256` |
| `scripts/gen_sdk_types.sh --check` | SDK types match the API's OpenAPI document (no API schema change) |
| `uv lock --check` | 557 packages, lock up to date |
| Playwright chromium `e2e/smoke.spec.ts` + `e2e/synthetic-fixture-badge.spec.ts` (`PW_CHROMIUM_PATH=/opt/pw-browsers/chromium`, own ports 4731/4732 so no other lane's server is reused) | 15 passed, exit 0. No spec was added or changed. |
| Targeted, after the last code change: worker suites (`test_security_gate1_worker.py`, `test_worker_queue.py`, after the `proc_limits` move) | 45 passed |

## R19

**None.** No file under `src/`, `public/`, `e2e/`, `packages/ts/`, `index.html`, `package.json`, `bun.lock`, `vite.config.ts` or `wrangler.jsonc` changed (`git diff --stat 15e4e3c HEAD` on those paths is empty), and the measurement agrees:

- Builds: `15e4e3c`'s default build (`bun run build` in a scratch worktree of it) and this branch's default build (`dist-e2e/default` from `scripts/e2e_serve.sh`), each served by `wrangler dev` (workerd) on its own port.
- Render: Chromium (`/opt/pw-browsers/chromium`), 1440×900, reduced motion, the R19 spec's own steps for `/`, `/visualizer` and `/visualizer/kawai-kim-natural` (wait for the page's ready text, `networkidle`, `freezeMotion`, no error text, full-page screenshot with the build-stamped footer masked).
- Compare: the `15e4e3c` renders written as snapshots, then this branch's renders compared to them with `toHaveScreenshot(..., { maxDiffPixels: 0 })`: 3 of 3 pass, so 0 differing pixels on each page. A control run (`15e4e3c` against itself) also passes.
- `e2e/__screenshots__/**` and `R19.sha256` were not touched; `scripts/check_r19.sh` passes.
