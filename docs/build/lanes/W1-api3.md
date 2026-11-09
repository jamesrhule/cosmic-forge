# W1 round 3B, lane API3 (`build/w1-api3`)

API validation, custom potentials and two small physics follow-ups. The branch
is based on `15e4e3c`. Evidence: `docs/build/evidence/W1-api3.md`.

Item IDs used here and in the evidence:

| ID | Source | Finding |
|---|---|---|
| D17 | LEDGER, JAMES DECISION 17 (backend half) | The canonical custom potential is one sympy expression in φ; `def V(<name>): return <expr>` is also accepted; any other body is a 422 that names the canonical form, with a test per case. |
| c3-expr-caps | round-2 WORKER verifier, `partial` | The caps bound exact digits but not Float magnitudes: `sin(exp(1e30))` hangs; `Add`'s `lo = -digits` does not hold for Floats, so `sin(9**(1/(1.0000001-1.0)))` hides an exponent of ~1e7. |
| API-COMPILE | round-2 WORKER verifier, NEW MEDIUM | `validate_problem` compiles a tenant's custom potential inside the API process with no time or CPU limit (`adapters/qcompass.py:198`, `qcompass_routes.py:337`). |
| CRITIC-SUBMIT | round-2 critic, MEDIUM (fix-verify) | `validate_problem` catches only `ValueError`; `POST /api/runs`, `start_run` and `validate_config` accept incomplete potentials; MCP `validate_config` answers 500 for a config `domain.Potential` refuses. |
| R2-START-ORDER | round-2 DB verifier, residual | `scan_parameters` spends its approval before validating. |
| PHYS3-ZERO | round-3A PHYS3 verifier, LOW (regression) | A θ_grav = 0 run publishes `RunResult.eta_B = 0.0 ± 0.0`: the source is exactly 0, so `normalisation_residual` is 0 and nothing refuses it. |
| PHYS3-NIT | round-3A PHYS3 verifier, NIT | The Born helper reads the pipeline's own coupling splines, so a sign error in B and C would pass every signal test. |
| SF6 | round-2 c7, LOW | The engine parity test compares url, pool size, overflow and pre-ping only; a one-sided `pool_recycle`, `pool_timeout` or `connect_args` diverges silently. |

Every finding was reproduced on `15e4e3c` before it was fixed (evidence). None
was wrong.

## Decisions

- **D17: what the API accepts as `customPython`.**
  - The canonical form is one Python/sympy expression in `phi` (unchanged path: `ast.parse(..., mode="eval")`).
  - If the source is not an expression, it is parsed as a module and must be exactly one top-level `def V(<name>)`:
    - exactly one positional parameter (a positional-only `def V(psi, /)` counts); no default, no `*args`, `**kwargs` or keyword-only parameters;
    - no decorators, no annotations (parameter or return), no type parameters, not `async`;
    - the body is exactly one `return <expression>`. **A docstring first is allowed** and ignored (decided here: it is documentation, and refusing it would refuse a harmless, idiomatic snippet). Comments anywhere are fine (`ast` drops them).
  - The return expression is extracted and every `Name` equal to the parameter is renamed to `phi` (Python scoping: inside `V` the parameter shadows everything, so `def V(sqrt): return sqrt**2` is `phi**2`). A parameter already named `phi` is left as is.
  - If the body also uses a free name `phi` while the parameter is called something else, it is refused: after the rename the two would be one symbol.
  - The extracted expression then goes through exactly the same checks as a canonical expression: `_check_shape` (512 nodes, depth 32), the `_Checker` allow-list and bounds, then `_build`. The whole snippet is still capped at 4096 characters.
  - **Annotations are refused** (the task's "no defaults/annotations…"): D17 names the exact shape `def V(<name>): return <expr>`, and main's backend never accepted any `def` snippet (`ast.parse(source, mode="eval")` on `origin/main`), so no saved config depends on them.
  - Every refusal of the snippet's shape (a statement, a lambda, a second parameter, a bad name…) raises `ValueError("custom potential: customPython must be one expression in phi, the canonical form (e.g. 'm**2*phi**2/2' or 'Lambda**4*(1 - cos(phi/f_a))'); 'def V(<name>): return <expression>' is also accepted; <reason>")`, so the route's 422 names the canonical form. A top-level `lambda` (or `return lambda …`) gets the same message. Errors inside an accepted expression (`'^' is not allowed`, an exponent cap, …) keep their own messages.
  - Note for James (non-blocking): main's own `DEFAULT_CUSTOM_PYTHON` (`def V(psi): M = 1.3e-5; return …`) has an assignment in its body, so under D17's literal rule it is refused, as it was on main's backend. D17's frontend half (FE3) replaces that default with the expression form. If James wants simple constant assignments inlined, that is a small follow-up; nothing here assumes it.
- **c3-expr-caps: Float magnitudes, complex arguments and float64's range.** The verifier's four asks, and how each is implemented:
  - *Bound Float magnitudes as well as exact digits.* `_Bound` gains `prec` (bits of the most precise Float below; sympy evaluates Float arithmetic and functions of Floats eagerly), `cplx` (may be non-real) and `nonneg`. A float literal's bound now comes from the sympy Float that `_build` makes from its text, not from Python's float: `1e-1000` is `0.0` to Python but `1.0e-1000` to sympy, so `exp(1/1e-1000)` used to pass the bounds and build `exp(1e1000)` (found while fixing this; it is in the regression test).
  - *Reject exp/sinh/cosh whose argument's upper bound exceeds log(1.8e308).* `MAX_CUSTOM_EXP_ARGUMENT = math.log(sys.float_info.max)` (709.78). It applies to exact arguments too (`exp(10**29)` overflows float64 at run time anyway).
  - *"and similar"*: `sin`, `cos` and `tanh` of a possibly complex argument grow like `sinh`/`cosh` (`sin(i·y) = i·sinh(y)`; sympy evaluates it), so they get the same argument cap. A value is possibly complex below `sqrt`/`log` of something not known to be ≥ 0, or a non-integer power of such a base. Found while fixing: `sin(cos(1e6*sqrt(-1)))` and `sin(sin(1e3*sqrt(-1.0)*1e3))` passed every bound on `15e4e3c` and spun.
  - *Reject any subtree whose bound exceeds ~1e308.* `MAX_CUSTOM_LOG10_MAGNITUDE = math.log10(sys.float_info.max)` (308.25), checked on every node. Both thresholds are float64's own limits, not tuned values (R6).
  - *Treat a Float Add/Sub as lo = −inf so Div/Pow cannot hide a large exponent.* **Implemented with a sound finite bound instead of −∞.** Literally −∞, together with the new 1e308 subtree cap, refuses ordinary potentials such as `V0*phi**2/(1.0 + phi**2)` and `1/(1.0 + phi**2)` (the division's upper bound becomes +∞). The bound used: in Float arithmetic every term is a multiple of its own ulp, ulp(x) ≥ |x|·2^-prec, so every partial sum is a multiple of the smallest one and a non-zero sum is at least that ulp. Hence `lo = min(term lower bounds, -digits) - prec·log10(2) - 1` for a sum with a Float in it (one flattened `Add`, as sympy builds it). This still does what the verifier asked: `1/(1.0000001 - 1.0)` is now bounded by 10^17.95, not 10^1, so `9**(1/(1.0000001-1.0))` fails the exponent cap. Exact sums keep `lo = -digits`.
  - Division and powers read a subtree's lower bound through `_floor`: a subtree with no Float below only ever builds Integers/Rationals of at most `digits` digits (≥ 10^-digits); everything else in it stays symbolic and is never evaluated. Without this, the new subtree cap would refuse `1/sin(phi)`, `sin(phi)**2`, `tanh(phi)**-2`, `log(tanh(phi))` (their raw lower bound is −∞).
  - A power with a non-negative literal exponent (`2`, `1/2`, `Rational(3, 4)`) is bounded one-sidedly, so `sin(1.0)**2` is not treated as possibly huge.
  - Real potentials are unaffected: the existing `srepr` guard (12 potentials) passes, and a further 24 (including Float sums in denominators, `exp(700*phi)`, `exp(-phi/0.01)`) are a new guard.
- **API-COMPILE: the submit-time compile is bounded.**
  - New `ucgle_f1/m2_scalar/check.py`, `check_potential(pot)`: the potential must compile in M2's units with every parameter bound (`compile_potential` + `potential_args`) and have a starting field value (`initial_field`, the pipeline's own rule: a custom potential needs `params['phi0']`).
  - A built-in kind compiles a fixed expression (hilltop's `p` ≤ 64) in-process. A custom potential compiles in a short-lived `multiprocessing` "spawn" child, killed (terminate, then kill) if it has not answered within `CUSTOM_COMPILE_TIMEOUT_SECONDS = 10` s; the refusal is a `ValueError` ("compiling it did not finish within 10 s, so it was stopped; simplify the expression") and the routes answer 422 INVALID_INPUT. An accepted custom potential takes about 1 s in the child (0.6 s of imports, 0.4 s of compile).
  - The child is confined like the worker's job processes: `RLIMIT_CPU` soft = ceil(limit) + 5 s, hard = soft + 5 s, and `PR_SET_PDEATHSIG` (Linux). One implementation (R20): `_confine_child` and `_cpu_count` moved from `worker.py` to `ucgle_f1/proc_limits.py`; the worker imports them under the same names, with identical behaviour.
  - At most `MAX_CONCURRENT_COMPILES = 4` children at once (each is a Python process with sympy loaded). A request waits for a slot within its own 10 s; if none frees, it is a 422 saying the server is busy, try again.
  - The child is given the compile function by reference (`potentials.compile_potential` as the module sees it at call time); that is also how the regression test swaps in a slow compile.
  - The caps (c3-expr-caps) are what make every accepted expression cheap; the limit holds even if they miss one. No new environment variable (R9): the limits are module constants.
- **CRITIC-SUBMIT: refused at submit, never a 500.**
  - `LeptogenesisSimulation.validate_problem` uses `check_potential` and maps any other exception to `ValueError` (the route's 422). `check_potential` itself maps compile exceptions (`SyntaxError`, `KeyError`, `TypeError`, `RecursionError`, …) to `ValueError` with the exception type in the message.
  - The two non-`ValueError`s that were reachable on `15e4e3c` now have clear messages of their own in `compile_potential`: a custom parameter named `phi` (lambdify's "duplicate argument 'phi'" `SyntaxError`) is refused as "'phi' is the field, not a parameter", and a non-finite V, V′ or V″ (`log(0)`, `1/0`: lambdify's `KeyError('ComplexInfinity')`) as "not finite (zoo, oo or nan)".
  - `validate_config` (the agent tool, MCP) now reports `Potential.missing_params()` as an error at `potential.params`, and a `check_potential` refusal as an error at `potential.customPython` (custom) or `potential`. `start_run` already refuses an invalid config with INVALID_INPUT before spending its approval, so `POST /api/runs` answers 422 for an incomplete potential, and the token survives. `start_run` now runs `validate_config` in a thread (it may compile a potential).
  - MCP `validate_config` (`/mcp/tools/validate_config`) answers a config the models refuse with `{valid: false, diagnostics}` (one per pydantic error, `Value error, ` prefix stripped, path from `loc`) instead of letting the `ValidationError` become a 500.
  - With this, the W1-platform lane's summary sentence ("the API refuses … incomplete parameters at submit with 422") is true for both run routes. That lane's notes are not edited here.
- **R2-START-ORDER: `scan_parameters` validates every cell, then spends, then runs.** New `_scan_cells(spec)`: axes must have `points ≥ 1` and finite bounds, log axes positive bounds; each cell's path is set and its `RunConfig` validated (`KeyError`, `TypeError`, `ValidationError` → INVALID_INPUT); each distinct config goes through `validate_config` once. Only then is the approval consumed and the pipeline run.
- **PHYS3-ZERO: a fourth refusal condition, reported by M4.**
  - `m4_anomaly/anomaly.py`: `ADIABATIC_SUBTRACTION_IMPLEMENTED = False` next to the `_adiabatic_subtraction` hook (identically zero, not V3's subtraction), and `AnomalyResult.adiabatic_subtraction_implemented` (default `False`, fail closed), which `delta_N_L` sets from it on every run. P1-04 sets the constant with the scheme.
  - `pipeline.eta_B_refusal` refuses when `pr.anomaly.adiabatic_subtraction_implemented is not True`: "M4 does not yet apply the adiabatic subtraction to ⟨RR̃⟩ (P1-04)". It is checked after the existing three conditions (non-finite drift, budget > 0.5 %, normalisation residual > 0.5 %), which are unchanged and keep their reasons, so every run with a non-zero source is still refused on the normalisation.
  - Effect: η_B is refused on every run until P1-04, as Decision 13(b) anticipates. A θ_grav = 0 run's S8/S14 were already FAIL (0.0 is outside the band) and stay FAIL, now with value `None` and the reason in the notes; audit pass counts are unchanged.
- **PHYS3-NIT: an independent coefficient test.** `tests/unit/test_coupling_coefficients.py` rebuilds A₊, B, C and a(τ) for the Kawai–Kim benchmark (Decision 11's potential with the fixture's couplings) from M2's φ(N) and H(N) only, using the definitions in `couplings.py`'s docstring with derivatives taken numerically in cosmic and conformal time (not the e-fold identities the code uses) and its own Simpson quadrature for τ(N). At τ = −4, −3, −2, −1, −0.3, −0.1 it requires the same sign and agreement within 1e-4 (measured: A ≤ 3.8e-6, B ≤ 1.2e-5, C ≤ 6.7e-8, a ≤ 7e-7).
- **SF6: one kwargs constant per module, and a parity test of everything.**
  - `ucgle_f1.db.engine.ENGINE_KWARGS` and `qcompass_core.db.ENGINE_KWARGS` (read-only `MappingProxyType`), each module's only source of `create_engine` keywords. The values are unchanged (`pool_pre_ping=True, pool_size=5, max_overflow=10`). The modules stay two (the lane-1 reason holds: unifying them would make `qcompass-core` a hard dependency of the backend).
  - The new test compares the two constants, every keyword each module actually hands `create_engine` (a spy, so a keyword added beside the constant is caught), the full pool configuration (class, size, overflow, timeout, recycle, pre-ping, reset-on-return, LIFO, echo, dialect, execution options) and the arguments the pool hands the driver (`do_connect` event: URL-derived plus `connect_args`).
  - This touches `ucgle_f1/db/engine.py`, a DB module, by one constant only; flagged for the merge with DB3.

## Corrected tests (old → new, proof)

- **PHYS3-ZERO, `backend/tests/unit/test_m4_units_and_refusal.py::test_eta_b_refusal_rule`.**
  - Old: `_fake(drift, resid)` built an `anomaly` with `normalisation_residual` only, and `assert eta_B_refusal(_fake(1e-6, 0.0)) is None` / `assert eta_B_refusal(_fake(1e-6, 1e-3)) is None`.
  - New: `_fake(drift, resid, *, subtracted=True)` also sets `anomaly.adiabatic_subtraction_implemented = subtracted` (`None` leaves it unset). The two `is None` assertions and the four refusal assertions are unchanged; four assertions are added: `subtracted=False` and an unset flag are refused with "adiabatic subtraction", and with `subtracted=False` the normalisation and budget cases keep their own reasons.
  - Why the old fixture is wrong now: the rule has a fourth condition, the item's whole point. An `AnomalyResult` always carries the flag (M4 sets it on every run); a fake without it stands for no real result, and the rule fails closed on it. With the flag set to True the fake again means "every condition met", which is what the two `is None` assertions test. Coverage rises: every old assertion is kept and the new condition is tested both ways.
- No other existing test was changed. The SF6 test is added beside the three existing SF6 tests, which are unchanged.

## Removals with replacement

- `worker.py`: the definitions of `_confine_child` and `_cpu_count` → `ucgle_f1/proc_limits.py` (`confine_child`, `cpu_count`), imported back into `worker.py` under the old names. Same code, also used by the API's compile child (R20).
- `adapters/qcompass.py` `validate_problem`'s inline `potential_args(compile_potential(...))` → `check_potential` (the same check, plus the time limit, the `phi0` rule and exception mapping).
- `tools/simulator.py` `scan_parameters`: the inline cell loop (and a dead `_ = build_run_result`) → `_scan_cells` (validation) plus the run loop. Same cells, same order, same `_scan_cell`.
- `ucgle_f1/db/engine.py` and `qcompass_core/db.py`: the inline `create_engine` keywords → `ENGINE_KWARGS` (same values).

## Routed to later tickets

- **D17 frontend half (FE3):** the Configurator's default snippet and its linter switch to the expression form. When that lands, `backend/tests/test_frontend_potential_configs.py::test_configurator_custom_snippet_is_refused_with_a_clear_422_message` (which reads `DEFAULT_CUSTOM_PYTHON` from `configDefaults.ts` and expects a refusal) has to change with it, as an R4 old → new in that lane or at the merge: the new default is then accepted. Its message assertion (`customPython must be one expression in phi`) still matches this lane's refusal text.
- **P1-04:** set `ADIABATIC_SUBTRACTION_IMPLEMENTED = True` together with the subtraction itself; η_B then stays refused on the normalisation until a is matched to reheating.
- **Pre-existing, noticed, not changed (NIT):** a custom parameter name that `sympy.symbols` splits (`"a b"`, `"x,y"`, `"x:3"`) gives the confusing 422 "potential parameters missing: ['(a, b)']". It is a 422, not a crash.
- **Pre-existing, not changed:** `scan_parameters` has no cap on the number of cells. It is not dispatched over HTTP, MCP or chat (round-2 DB verifier).

## BLOCKED-ON-JAMES

None. No secret is needed and no new environment variable was introduced.
