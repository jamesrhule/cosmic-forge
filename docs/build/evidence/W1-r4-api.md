# W1 round 4, lane R4-API: evidence

Branch `build/w1-r4api`, based on `6e0f15d`. The lane notes have the item
IDs, decisions, Decision-by-build proposals and remaining work:
`docs/build/lanes/W1-r4-api.md`.

**Method (LEDGER Decision 14).**
- There is one or more regression tests per finding. Each was run against the base and fails there for the finding's own reason. All of them pass on this branch.
- A test that can only exist after the fix, because it calls an API the fix adds, is marked as a guard. Its base failure is listed but not counted.
- No database policy changed, and no migration was added or edited.

**How "before" was measured.**
- *Items 1 and 2.* `backend/src/ucgle_f1/m2_scalar/potentials.py` was put back to `6e0f15d` in the worktree, the new test file was run, and the fix was restored.
- *Items 3 to 6.* The sources are `git archive 6e0f15d backend/src supabase/migrations`, unpacked under `scratchpad/r4api/base`. They ran with this branch's venv and `PYTHONPATH=<base>/backend/src`, so the base sources shadow the editable install. The test files are this branch's.
- *Database.* The repo's pytest plugin (`ucgle_f1.db.pytest_plugin`) starts a throwaway local PostgreSQL 16 cluster. No `DATABASE_URL` was set.
- *Hangs.* The two tests that hang on the base were run one at a time under `timeout 60`.

**Versions (R17).** Python 3.12.13, sympy 1.14.0, mpmath 1.3.0, numpy 2.2.6, FastAPI 0.162.0, pydantic 2.14.2, SQLAlchemy 2.1.6, psycopg 3.3.6, pytest 9.2.0, PostgreSQL 16.15, bun 1.4.4.

## Reproduced on the base before fixing

- **R4-1.** `scratchpad/r4api/probe.py` on `6e0f15d` calls `_custom_expr` in a subprocess with an 8 s limit.
  - All 22 of the verifier's examples are refused. 17 get "a subexpression may exceed 1.798e+308, the largest float64", for example `1/sin(0.5*phi)`, `log(tanh(0.5*phi))` and `log(1.0 + log(1.0 + phi))`.
  - The other 5 get "exp() of argument up to 10**19" (`V0*exp(-1/(phi**2 + 0.1))`), 10**18 (`V0*exp(-1/(phi - 0.5))`), "cosh() … 10**19", or 10**5 (the all-exact `V0*exp(-1/(phi**2 + 1/10))`).
- **R4-2.** With the same probe, the first four payloads did not finish in 8 s, and `phi*sin(exp((-1)**(-64*sqrt(-1))))` was accepted by the caps.
- **R4-3, R4-4, R4-5 and R4-6.** Each base failure is in the table below.

## Per item

| ID | Fix (lane notes have the detail) | Regression test(s) | Base (reason) | After |
|---|---|---|---|---|
| R4-1 | Finite floors for `sin`/`cos`/`tanh`/`log`/`sinh` of a real argument. A sum that cannot cancel (one sign, or a dominant term, `_sum_floor`) keeps its terms' floor. | `test_r4_api_potential_caps.py::test_r4_1_ordinary_potentials_are_accepted_and_compile_to_their_formula`: 62 cases, the verifier's 22 plus a 40-potential corpus covering polynomials, Starobinsky (three spellings plus main's Float form), natural, hilltop, log (including Coleman–Weinberg), tanh/T-model, sqrt, rational functions with positive denominators and sums of exponentials. Each compiles through `compile_potential(Potential(kind="custom"))`. V at φ = 0.6, 1.3 and 2.7 must equal the formula evaluated with Python's `math` (rel 1e-12), and V′ must equal a central difference (rel 1e-5). | 22 failed, the verifier's examples, each "custom potential: a subexpression may exceed 1.798e+308" or "exp() of argument up to 10**…". The 40 corpus potentials passed (a no-change guard). | 62 pass |
| (guard) | The bombs stay refused | Unchanged `test_api3_submit_checks.py::test_c3_float_bombs_are_refused_quickly` (20), `::test_c3_float_caps_keep_real_potentials` (24), `test_security_gate1_worker.py` `srepr` guard (12) | pass | pass |
| R4-2 | A complex power of a negative or complex base is widened by `π·\|b\|·log10 e`. `tanh` of any complex argument gets a pole term (exact: `8·(digits + log10\|y\| + 1)`). | `::test_r4_2_complex_power_and_tanh_pole_bypasses_are_refused_quickly`: the verifier's 5 plus 6 variants, each in a subprocess with a 20 s limit. `::test_r4_2_exp_of_the_complex_power_is_refused_with_its_true_size`. `::test_r4_2_the_complex_power_bound_holds_its_value` (a guard, which also checks that `phi**sqrt(phi)` stays accepted). | 7 failed: the verifier's 4 hangs ("did not finish within 20 s"), its accepted `phi*sin(exp(...))`, the variant `sin(exp((-1.0)**(-64*sqrt(-1))))` and `sin(sin(tanh(sqrt(-1)*Rational(355, 226))))`. The other 4 variants were already refused on the base. `exp((-1)**(-64*sqrt(-1)))` was accepted. | 13 pass, each refused in about 1 s (child start-up included), e.g. "exp() of argument up to 10**87.3" and "sin() of a complex argument up to 10**296" |
| R4-3 | The slot wait is a separate 5 s budget. Each tenant has a share of 2. `CompileCapacityError` is answered with 503 UNAVAILABLE or 429 RATE_LIMITED plus Retry-After. | `test_r4_api_capacity_and_scan.py::test_r4_3_waiting_for_a_slot_does_not_eat_the_compile_limit` | failed: "custom potential: compiling it did not finish within 5 s, so it was stopped; simplify the expression" for `m**2*phi**2/2` after a 4.5 s slot wait | pass |
| | | `::test_r4_3_a_full_server_is_a_503_with_retry_after_not_a_422` (HTTP) | failed: 422 INVALID_INPUT "invalid cosmology problem: custom potential: it could not be checked within 10 s because the server is compiling …" | pass: 503 UNAVAILABLE, `Retry-After: 5`, no "simplify"; then 202 |
| | | `::test_r4_3_one_tenant_cannot_hold_every_slot` (two of acme's checks hold slots; acme's third goes over HTTP) | failed: "a tenant over its share is refused at once" (acme's third waited 9.0 s and took a third slot) | pass: 429 RATE_LIMITED in < 1 s, `Retry-After: 5`; another tenant still compiles |
| | | `::test_r4_3_capacity_refusals_are_not_config_diagnostics` | failed: "a capacity refusal was reported as an invalid config" (a `potential.customPython` diagnostic) | pass |
| R4-4 | The compile child gets `os.nice(10)` and `RLIMIT_AS` = its size after imports + 256 MiB. Custom parameter names must be identifiers (`domain.custom_param_name_ok`, at most 64 of them). `compile_potential` makes one `Symbol` per name. | `::test_r4_4_compile_child_has_an_address_space_cap_and_a_lower_priority` | failed: "limits as=(-1, -1) vmsize=552513536 nice=0" (no cap, normal priority) | pass |
| | | `::test_r4_4_a_memory_bomb_in_the_child_is_refused_quickly` (a compile that allocates 2 GiB) | failed: the allocation succeeded (the refusal was "'int' object has no attribute 'param_names'", not MemoryError) | pass: "MemoryError", in < 8 s |
| | | `::test_r4_4_custom_parameter_names_must_be_identifiers` (11: `a:9999999`, `x:3`, `a b`, `x,y`, `1a`, `lambda`, `a-b`, empty, `phi`, fullwidth `ｍ`, 65 characters) | 11 failed: "DID NOT RAISE ValidationError" | 11 pass, each refused in < 0.5 s by the model |
| | | `::test_r4_4_compile_never_parses_a_parameter_name_as_a_range` (`EnginePotential.model_construct` with `a:9999999`, below the model) | failed: did not finish within 60 s (`timeout 60`, exit 124): `sympy.symbols('a:9999999')` | pass in < 2 s: one Symbol named `a:9999999` |
| | Guards | `::test_r4_4_identifier_parameter_names_are_accepted` (8, including `α` and 64 characters) and `::test_r4_4_too_many_custom_parameters_are_refused` | 8 passed (a no-change guard); the 64-parameter cap is new (failed: did not raise) | pass |
| R4-5 | `ScanSpec` caps (4 axes, 64 points, 256 cells). `scan_parameters` checks `approval_is_valid` (spends nothing), then validates, then spends. Each distinct potential is compiled once per scan. | `::test_r4_5_a_bogus_token_is_refused_before_any_cell_is_validated` (256 cells, 16 distinct custom potentials, token `appr_not-a-token`) | failed: did not finish within 60 s (`timeout 60`, exit 124): every cell validated first, one compile per distinct config | pass: APPROVAL_REQUIRED in < 1 s, zero compiles |
| | | `::test_r4_5_scan_spec_caps_axes_points_and_cells` | failed: `ScanAxis(points=10**6)` "DID NOT RAISE" | pass |
| | | `::test_r4_5_a_couplings_axis_compiles_the_potential_once` | failed: `['custom', 'custom', 'custom'] == ['custom']` (one compile per ξ value) | pass |
| | Guard (new store method) | `::test_r4_5_a_valid_token_survives_a_refused_scan_and_is_spent_by_one_that_runs` | failed: AttributeError `approval_is_valid` (expected for a guard) | pass |
| R4-6 | Both run SSE routes send the `job_events` row id as `id:`. Made-up events carry none. `RunRegistry.stream_with_ids` is new. | `test_r4_api_sse_ids.py::test_r4_6_domain_run_stream_sends_each_events_row_id` (`/api/qcompass/domains/chemistry/runs/{id}/stream`) and `::test_r4_6_cosmology_run_stream_sends_each_events_row_id` (`/api/runs/{id}/stream`) | 2 failed: `KeyError: 'id'` (no `id:` line) | pass: ids equal the rows' ids in order; `history`/`end` carry none |
| | Frontend (already prefers ids since FE3 `73429ff`) | `src/lib/__tests__/streamReconnect.test.ts` "the API's shape (row ids, an id-less status for a run that ended) is delivered once" (new) and the existing "an event that committed late is delivered once, and nothing is repeated" | — (pins the server shape) | 8 / 8 pass |

## Adversarial probe of the new bounds

`scratchpad/r4api/probe2.py` ran 20 constructions aimed at the new rules
through `_custom_expr`. All finished within 2 s.

- Refused:
  - `sin(exp(700.0)/(phi - phi + 1.0))` (no dominance, so the ulp bound applies);
  - `exp(1/sin(3.141592653589793))` (10**38.6 > 709);
  - `sin(1/(phi - phi + 1e-300))`;
  - `exp(1/(phi**2 + 1e-300))`;
  - `sin(sin(tanh(sqrt(-1)*3.14159…/2)))` (10**90.6);
  - `sin(exp(700*(phi - 0.5)/(phi - 0.5)))`.
- Accepted, and cheap and within float64 by their bounds: `sin(1/(1.0 - cos(1e-8*phi)))`, `sin(1/log(1.0000000000000002))`, `sin((phi - 0.5)**-64)`.

## Suites (this branch, final head)

Commands are as in CI (`.github/workflows/ci.yml`). The results are filled in
below as each finished.
