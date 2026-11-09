# W1 round 4, lane R4-API (`build/w1-r4api`)

The custom-potential caps, compile capacity and limits, the scan's order and
caps, and SSE event ids. The branch is cut from `6e0f15d`. Evidence:
`docs/build/evidence/W1-r4-api.md`.

Item IDs used here, in the evidence and in the test names:

| ID | Source | Finding |
|---|---|---|
| R4-1 | round-3B API3 verifier, regression, MEDIUM | The `0c4848f` caps refuse ordinary potentials that `15e4e3c` accepted. The message is a misleading float64 overflow. A Float sin/cos/tanh/log/sinh subtree has lower bound -inf, and a Float sum's cancellation bound feeds `exp`'s argument cap. |
| R4-2 | round-3B API3 verifier, new finding, MEDIUM | Two bypasses. `_power` ignores `e**(-arg(a)*Im b)` for a complex power of a non-positive base. `tanh` of an exact imaginary argument has no pole bound. |
| R4-3 | round-3B API3 verifier, new finding, LOW | The 4 compile slots are global. The wait for a slot comes out of the 10 s compile limit. A capacity refusal is a 422 that says "simplify the expression". |
| R4-4 | round-3B API3 verifier, new finding, LOW | The compile child has no `RLIMIT_AS` and normal priority. Custom parameter names reach `sympy.symbols` unvalidated, and `'a:9999999'` becomes ten million Symbols. |
| R4-5 | round-3B API3 verifier, new finding, LOW (latent) | `scan_parameters` validates every cell before it checks the approval, and `ScanSpec` has no caps. |
| R4-6 | round-3B FE3 verifier, WORKER NIT, partial | The SSE run streams send no `id:`, so the client's replay by id never applies in production. |

I reproduced every finding on the base before fixing it (evidence). None was
wrong.

## Decisions

These are mostly implementation choices inside the items. The choices the plan
does not make are listed separately under Decision-by-build (proposed).

- **R4-1, how the bounds were fixed.** I kept the checker's model: a symbol counts as 0 or ±1, which covers what a cancelling symbol leaves behind. I tightened two places.
  - *Finite floors for functions of a real argument* (`_Checker._call`). Each floor is a lower bound on |f(x)| for a non-zero result.
    - `tanh`: `min(|x|, 1)·tanh(1)`. This is exact.
    - `sinh`: `|x|`. This is exact.
    - `log` of a real p-bit Float: `2**-(p+1)`. The Floats next to 1 are `1 ± 2**-p`, and `|log x| ≥ π` for x < 0.
    - `sin`/`cos` of a real p-bit Float: `2**-(2p+16)`, or `(2/π)|x|` for small x. The proven worst case over every double is about 2**-61, the known worst case for argument reduction. Doubling p leaves a margin of 2**-55 or more.
    - Where the Floats cancel and leave an exact value, each floor also takes the exact `digits` bound. Exact arguments keep the existing digits floor.
  - *Sums that cannot cancel* (`_sum_floor`). Sympy can sum any subset of an Add's terms, including the parts of child Adds that flatten into it. The bound therefore covers every subset sum.
    - Terms of one sign (all known ≥ 0, or all subtracted and ≥ 0) cannot cancel. A subset sum is at least its smallest floor (`phi**2 + 0.1`).
    - A dominant term is one whose floor exceeds the summed upper bounds of all the others by more than 0.05 decades. It is peeled off with the floor `log10(10**f − 10**R)`, and the rest is bounded the same way (`phi - 0.5`). If the dominant term is itself 0, the sum is a sum of the rest, which the recursion already covers.
    - Otherwise the existing ulp/`digits` bound applies unchanged. The result is the larger of the two lower bounds, both of which are valid.
  - Nothing else changed: the caps (float64's limits, exponent ≤ 64, 1000 digits, 512 nodes, depth 32) and `_build`. An accepted expression is the same sympy object as before.
- **R4-2: widen the bounds, do not refuse.** A complex exponent of a symbol is legitimate (`phi**sqrt(phi)`; `sqrt(phi)` is "possibly complex" because φ is not known to be ≥ 0), so I did not refuse complex exponents or imaginary arguments outright.
  - *Complex power.* When `b` may be complex and `a` may be negative or complex, `hi`/`lo` widen by `π·|b|max·log10(e)`, because `|arg a| ≤ π`. With |b| ≤ 64 that is at most 87.3 decades. `(-1)**(-64*sqrt(-1))` (e**64π ≈ 1.9e87) is now bounded at 10**87.3, so `exp` of it is refused at once.
  - *tanh of a complex argument* always gets a pole term.
    - For an exact argument it is `8·(digits + log10|y| + 1)`. π's irrationality exponent is below 8 (Salikhov 2008: 7.6063), so a number with d digits is at least about 10**-(8d) from a pole of tan.
    - For a Float the existing `prec·log10(2)` term is kept.
    - The verifier's `tanh(sqrt(-1)*Rational(5920787228742393, 3769290217798865))` is now bounded at 10**296. The `sin` around it is refused.
  - All 11 bypass payloads (the verifier's 5 plus 6 variants) are refused in under a second.
- **R4-3: capacity is separate from the compile.**
  - A request waits at most `CUSTOM_COMPILE_WAIT_SECONDS` = 5 s for a slot. The 10 s compile limit starts when it has one.
  - Each tenant may have at most `MAX_COMPILES_PER_TENANT` = 2 checks running or waiting. A third is refused at once.
  - A capacity refusal is `CompileCapacityError`, a `ValueError` subclass, so a caller that does not know it still answers 422, never 500. It has a code and a Retry-After of 5 s. The app's error handler (`api_errors`) answers it as follows:
    - **503 UNAVAILABLE** when every slot stayed busy;
    - **429 RATE_LIMITED** when the tenant has its share.

    The message says the server was busy and to retry. It never says "simplify".
  - The tenant comes from:
    - the principal on `POST …/runs` (`compile_tenant` ContextVar, which reaches the plugin's `validate_problem` through `asyncio.to_thread`);
    - `start_run`, MCP `validate_config` and `scan_parameters` (`tenant=` all the way down);
    - otherwise a shared in-process bucket.
  - `validate_config` passes a capacity refusal up, so it is not reported as an invalid config.
  - A genuine compile timeout keeps its old message.
- **R4-4: the child's limits, and parameter names.**
  - The compile child gets `os.nice(10)`, so it yields the API's single vCPU to the API process. It also gets `RLIMIT_AS`, set after it has loaded its imports (`proc_limits.cap_address_space`), at its size then plus a headroom (sizes below).
  - Custom parameter names must be Python identifiers in NFKC normal form (the form the expression's parser produces), at most 64 characters, not a keyword and not `phi`. A potential has at most 64 parameters. This is checked in `domain.potential_param_errors`, so it is a 422 before any compile.
  - Below the model, `compile_potential` makes one `sp.Symbol` per name instead of calling `sp.symbols`. For an identifier this is the same Symbol, so built-in kinds and every accepted custom potential compile exactly as before.
  - `confine_child` gained `niceness` (default 0), and `cap_address_space` is new. The worker's job children are unchanged.
- **R4-5: the scan's caps and approval order.**
  - The caps are in the schema: `ScanAxis.points` from 1 to 64, `ScanSpec.axes` at most 4, at most 256 cells.
  - `scan_parameters` now checks that the token could be spent (`MemoryStore.approval_is_valid`, one SELECT with `consume_approval`'s predicate, spending nothing). Then it validates every cell, and only then does `consume_approval` spend the token, conditionally. A token that is valid but refused is still not spent, as in round 3B.
  - Each distinct potential is now checked once per scan (`validate_config(potential_checks=…)`), not once per distinct config, so a couplings axis no longer recompiles the potential.
- **R4-6: SSE ids, server side.**
  - Both routes that stream run events send each event's `public.job_events` row id as `id:`:
    - `GET /api/qcompass/domains/{d}/runs/{id}/stream`;
    - `GET /api/runs/{id}/stream`, through the new `RunRegistry.stream_with_ids`. `stream` is now a wrapper over it, so there is one implementation (R20).
  - Events a route makes up carry no id: `history`, `end`, the `STREAM_ABORTED` error, and a status or result for a run that ended without a terminal event. The client's count-based fallback covers them unchanged.
  - The frontend's `runEventStream` already prefers ids (FE3, `73429ff`; this was verified client-side in round 3B). No change was needed. I added a vitest with the API's exact shape: row ids, plus an id-less status for a run that ended.
  - **No `Last-Event-ID` resume.** Event ids come from a sequence, not from commit order, so "after id N" can skip an event that commits late. A full replay with deduplication by id on the client is what recovers it.

## Decision-by-build (proposed)

The coordinator numbers and ledgers these. Each has its reason and the test
that pins it.

1. **Float trig/log zero distance = 2**-(2p+16).** I chose this instead of a proven bound because the rigorous one, from π's irrationality measure, is about 2**-(7.6p) ≈ 10**-121 per `sin`. That would refuse `sin(0.5*phi)**-3`, whose exact twin `sin(phi/2)**-3` is accepted. The proven worst case over all doubles is 2**-61, so 2p+16 bits leaves at least 55 bits of margin. The security property (no hang) needs magnitudes around 10**(10**5), which leaves a far wider margin. Pinned by `backend/tests/test_r4_api_potential_caps.py::test_r4_1_ordinary_potentials_are_accepted_and_compile_to_their_formula` (22 verifier examples + 40 corpus potentials) and the unchanged `test_api3_submit_checks.py::test_c3_float_bombs_are_refused_quickly` (20 bombs).
2. **Complex exponents and imaginary tanh arguments are bounded, not refused.** π's irrationality exponent is rounded up to 8 for the exact pole term. One consequence: a complex-argument tanh such as `tanh(sqrt(phi))` now has a large upper bound (about 10**22 for a simple argument). `exp(tanh(sqrt(phi)))`, accepted on `0c4848f`, is now refused. No realistic potential takes `tanh` of a possibly complex argument. Pinned by `test_r4_api_potential_caps.py::test_r4_2_*`.
3. **Compile capacity numbers:**
   - a slot wait of 5 s;
   - 2 concurrent checks per tenant, half the 4 slots, so no tenant can hold every slot;
   - Retry-After 5 s;
   - 503 UNAVAILABLE for a full server, 429 RATE_LIMITED for a tenant over its share.

   Pinned by `backend/tests/test_r4_api_capacity_and_scan.py::test_r4_3_*`.
4. **The compile child's memory headroom.**
   - `RLIMIT_AS` is set to the child's size after its imports plus 256 MiB.
   - Measured on this image:
     - after imports the child is 0.54 GiB of address space and 0.12 GiB resident;
     - the largest accepted compiles tried (a 29-factor `tanh` product and a 39-term trig sum) peak at 0.59 GiB;
     - 256 MiB is about five times that growth;
     - four children stay at about 1.6 GiB resident at most, inside the API container's 2 GiB.
   - The cap is measured after the imports so that an image with JAX, which has a larger import, is not refused for it.
   - Niceness is 10.

   Pinned by `test_r4_4_compile_child_has_an_address_space_cap_and_a_lower_priority` and `test_r4_4_a_memory_bomb_in_the_child_is_refused_quickly`.
5. **Custom parameter names:** Python identifiers in NFKC normal form, at most 64 characters, not a keyword, not `phi`, and at most 64 parameters. Unicode is allowed because the expression may use any identifier Python accepts (`α`). Pinned by `test_r4_4_custom_parameter_names_must_be_identifiers` and `test_r4_4_identifier_parameter_names_are_accepted`.
6. **Scan caps:** 4 axes, 64 points per axis, 256 cells. The agent's own `suggest_next_parameter_scan` makes 2 × 9 = 81 cells, and each cell is a full pipeline run. Pinned by `test_r4_5_scan_spec_caps_axes_points_and_cells`.
7. **SSE ids are the job_events row ids, and there is no Last-Event-ID resume** (the reason is under R4-6). Pinned by `backend/tests/test_r4_api_sse_ids.py` and `src/lib/__tests__/streamReconnect.test.ts` ("the API's shape … is delivered once").

## Corrected tests (old → new)

None. No existing test was changed, and every existing assertion still holds.
`test_submit_compile_waits_for_a_free_slot_within_its_limit` still expects a
`ValueError` matching "server is compiling other custom potentials".
`CompileCapacityError` is a `ValueError` and its message keeps that phrase. The
test is slower, because the wait is now 5 s rather than its 0.5 s `timeout`;
the wait is a separate budget from `timeout`. `api3_compile_helpers.py` gained
three helper functions and `streamReconnect.test.ts` one test; neither changes
an existing test.

## Removals with replacement

- `check._compile_in_child(pot, remaining, limit)` → `_compile_in_child(pot, limit)`. The limit now starts when the slot is acquired.
- `compile_potential`: `sp.symbols(sorted(names))` → one `sp.Symbol(name, real=True)` per name. The Symbols are identical for every name `Potential` admits.
- `RunRegistry.stream` → a wrapper over `stream_with_ids` (same events, same order).

## Remaining

- Not fixed here (pre-existing, noted): the exact-argument floor of `sin`/`cos` (`-(digits+1)`) follows π's continued fraction, not its irrationality measure. A rational approximation of π with an unusually large partial quotient could sit a few decades below it. Exploiting that needs more than 300 digits, which the float64 and `exp`-argument caps already refuse. A follow-up could use the same `8·digits` term as `tanh`'s pole bound.
- Not fixed here (pre-existing, noted): `log` of an exact negative or complex argument is bounded without its `iπ` term (`|log(-1)| = π`, bounded as 1). Only Float arguments add π. The effect is a factor of π inside `exp`'s argument. That is far from the 10**(10**5) a hang needs, and `sin`/`cos`/`tanh` of anything possibly complex are already capped at an argument of 709. Adding the term would refuse `exp(64*log(phi))` (factor 64 × 4.14 > 64), so I left it for a ticket that decides that.
- `scan_parameters` is still not dispatched by any route (`/mcp/tools`, `/v1/chat`). The caps hold for when it is.
- Pre-existing at `6e0f15d`, outside this lane: the packages suite's `test_security_floors.py::test_published_group_declares_the_floor[ucgle-f1[<dependencies>]->cryptography]` fails. `backend/pyproject.toml` does not declare `cryptography>=50.0.0`, although its `pyjwt` dependency pulls it. This lane changed no `pyproject.toml` and not `uv.lock`. The fix is one floor in the backend's dependencies plus `uv lock`, for the dependency owner (evidence, Suites).

## BLOCKED-ON-JAMES

None. No secret, paid resource or setting is involved, and no new environment
variable was introduced (R9).
