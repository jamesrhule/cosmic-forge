# W1 — Gate 1 security round 2, worker lane (cluster c3)

Branch `build/w1-sec-worker`, based on `9c6bf4c`. Lane notes: `docs/build/lanes/W1-sec-worker.md`, which also has the finding IDs and every decision.

**Method (LEDGER Decision 14).**
- One regression test per finding. It drives only APIs that existed at `9c6bf4c`: the worker and its handler API, `JobQueue`'s pre-fix signatures, HTTP, WebSocket and SQL.
- Each test fails on `9c6bf4c` for the finding's own reason and passes with the fix.
- The database changes are one new migration, `20261102105000_qcompass_queue_attempt_lease.sql`. Its down migration restores the previous bodies.
- No existing migration was edited.

**How "before" was measured.**
- Tree: `git archive 9c6bf4c` into a scratch directory, with the new test files copied in.
- Python: run with the same venv, with `PYTHONPATH` pointing at that tree's `backend/src`, `workers` and `packages/*/src`, so its sources shadow the editable installs. Its own `supabase/migrations` applied to a fresh Postgres 16 cluster.
- Frontend: the vitest file was run with this branch's three service files stashed back to `9c6bf4c`.

**Every finding was reproduced on `9c6bf4c` before it was fixed.** Verifier repros, run unchanged:
- `scratch-c3/expr_bypass.py`: four cases hang.
- `gil_worker.py`: the handler holds the GIL and no JOB_TIMEOUT fires.
- `timeout_env.py`: `inf`/`1e10` raise OverflowError, and `-1` times out at once.
- `db_repro.py`: DeadlockDetected.
- `inflight_repro.py`: the run ends `completed` after `_fail`.

Two further bypasses of the caps were found while fixing c3-expr-caps, and are in its test:
- a cancelling exponent: `Rational(9)**(phi - phi + 9**9)`;
- sympy's `exp(k*log(x))` → `x**k` rewrite: `exp(9**9*log(9))`.

No finding in this cluster was wrong.

## Per finding

| ID | Severity | Fix | Regression test(s), `backend/tests/test_security_gate1_worker.py` unless named | 9c6bf4c (reason) | After |
|---|---|---|---|---|---|
| c3-expr-caps | MEDIUM | `_custom_expr`: one `ast` parse, an allow-list, and bounds on every node (exponent ≤ 64, digits ≤ 1000, `exp`-of-`log` factor ≤ 64, nesting ≤ 32, 512 nodes, literal ≤ 1e30) before sympy evaluates the same tree; `^` refused | `test_c3_expr_caps_bypasses_are_rejected_quickly` (6 cases, subprocess with a 20 s limit) | 6 failed: each parse hung past 20 s ("did not finish: sympy evaluated an unbounded constant") | pass, each rejected in < 5 ms |
| (guard) | | Accepted input compiles to exactly what `sympify` built | `test_c3_expr_caps_real_potentials_compile_as_before` (12 potentials, `srepr` equality) | passed (no-change guard) | pass |
| c3-gil-timeout | MEDIUM | One spawned child process per job, which the worker kills at the limit; the child writes only through the worker; `RLIMIT_CPU`; `PR_SET_PDEATHSIG` | `test_c3_gil_holding_handler_is_stopped_at_its_time_limit` | failed: "the worker process stalled 9.0s while the handler held a GIL" (the job then succeeded instead of JOB_TIMEOUT) | pass (killed at 1 s, longest stall < 0.1 s) |
| | | Defence in depth | `test_c3_gil_job_process_has_a_cpu_limit` | failed: `assert 0 < -1` (no CPU limit on a handler) | pass |
| c3-timeout-parse | LOW | Finite, > 0, ≤ `threading.TIMEOUT_MAX`, or `ValueError` (the CLI exits 2); any error while waiting abandons the attempt and fails the job | `test_c3_timeout_parse_env_values_that_break_the_wait_are_refused` (inf, nan, 1e10); `…_constructor_values_are_refused` (-1, 0, inf, nan, 1e10); `…_cli_refuses_to_start` | 9 failed: "DID NOT RAISE ValueError" / "DID NOT RAISE SystemExit" | pass |
| | | Post-fix guard (the pre-fix failure, OverflowError in `join`, can no longer be reached) | `test_c3_timeout_parse_an_error_while_waiting_fails_the_job` | failed for a different reason: `wait_for` doesn't exist there (expected; it is a guard, not the regression test) | pass |
| c3-lock-order | LOW | `cancel_run` locks the run's job rows, then the run row: the janitor's order | `test_c3_lock_order_cancel_racing_a_dead_letter_does_not_deadlock` (a test trigger holds the janitor between its two locks) | failed: `{'reap': 'DeadlockDetected', 'cancel': True}` | pass: `{'reap': 1, 'cancel': False}` |
| c3-attempt-lease | LOW | Lease = (job, worker id, attempt, run) in SQL; `FOR SHARE` on the job row; sticky terminal states (trigger + predicates); the worker serves child writes on the thread that abandons | `test_c3_attempt_lease_a_stale_attempt_with_the_same_worker_id_cannot_write` | failed: "attempt 1 stored a result while attempt 2 holds the job" (`{'from': 'attempt-1'}`) | pass |
| | | | `test_c3_attempt_lease_a_terminal_run_never_changes_status` | failed: "failed -> completed" | pass |
| | | | `test_c3_attempt_lease_an_in_flight_write_never_lands_after_the_failure` (the verifier's `inflight_repro` delays) | failed: "a terminal run was overwritten: [('failed', True), ('completed', True)]" | pass |
| | | SF2 residual (2) | `test_c3_attempt_lease_no_worker_event_lands_after_a_cancel` (a test trigger delays the worker's insert) | failed: events `['status', 'status', 'log']`, the worker's log after `canceled` | pass |
| | | R13 | `test_c3_attempt_lease_migration_is_reversible` | failed (the migration doesn't exist there; reversibility guard) | pass |
| c3-guarded-queue | LOW | `_GuardedQueue` has explicit methods only | `test_c3_guarded_queue_handlers_cannot_reach_queue_internals` | failed: exposed `complete,heartbeat,cancel_run,enqueue_run,_emit,engine`, and the handler canceled another run | pass |
| c3-stream-bounds | LOW | A `heartbeat` job event on every lease renewal (never sent to clients) | `test_c3_stream_idle_a_long_quiet_run_is_not_aborted` | failed: "a healthy run's stream was aborted as idle" | pass |
| | | Max bound checked on every poll (SSE, WS, legacy) | `test_c3_stream_max_bound_holds_while_events_keep_arriving` | failed: "did not finish within 8s" | pass |
| | | A run terminal for 2 s without a terminal event ends its streams | `test_c3_stream_a_run_that_ended_without_a_terminal_event_ends_its_streams` | failed: "did not finish within 15s" | pass |
| | | Frontend reconnects on `STREAM_ABORTED` while the run is not over (`runEventStream`) | vitest `src/lib/__tests__/streamReconnect.test.ts` (3 cases) | 2 failed: no reconnect (domain: "Run … running", cosmology: stream stopped after 2 events); 1 passed (no reconnect once the run is over: guard) | pass |
| c3-claim-after-abandon | LOW | A lost lease ends the wait within 0.1 s and stops the child | `test_c3_claim_a_lost_lease_ends_the_wait_at_once` | failed: "the worker kept waiting on a job whose lease it lost" | pass |
| | | No claim while an abandoned job process lives | `test_c3_claim_no_new_job_runs_beside_an_abandoned_one` | failed: "the abandoned handler still runs beside the next job" | pass |
| | | | `test_c3_claim_nothing_while_an_abandoned_job_is_alive` | failed: "claimed a job while an abandoned one is alive" | pass |
| c3-provenance-upload | NIT | The worker process renews the lease immediately before the Storage put | `test_c3_provenance_upload_needs_the_lease` | failed: "provenance.json was uploaded for a canceled run" | pass |
| c3-healthy-race | NIT | `healthy()` read-only under a lock | `test_c3_healthy_race_never_drops_an_abandoned_entry` (a list subclass opens the window deterministically) | failed: "an abandoned entry appended while /healthz ran was dropped" | pass |

Totals on `9c6bf4c`:
- New backend tests: 33 of 35 failed, 32 of them for the finding's reason. The one failure for another reason is the post-fix guard `…an_error_while_waiting…`. The 2 passes are the no-change guard and, after it was made deterministic, none.
- Vitest: 2 of 3 failed.

Measured by `before_run.txt`: 32 failed, 2 passed. The second pass was the first version of the healthy-race test. With the GIL, CPython 3.12 can't switch threads inside its window, so that test was rewritten to open the window deterministically, and it now fails on `9c6bf4c` (re-run: "an abandoned entry appended while /healthz ran was dropped").

### Corrected existing tests

The full old → new text is in the lane notes. In short:
- `test_l3_hung_handler_…` and `test_sf2_cancel_racing_…` use module-level handlers, because a child process can't receive a closure.
- `test_l3_job_timeout_is_configurable` expects `ValueError` for 0, -5 and "soon".
- `test_sf1_sf2_queue_migration_is_reversible` rolls back `20261102105000` first and checks the exact signature set.
- Four tests pass the lease's `attempt`.

No assertion was loosened.

## Suites on the final tree

SUITES_PLACEHOLDER

## Versions (R17)

- Python 3.12.13; sympy 1.14.0; SQLAlchemy 2.1.6; psycopg 3.3.6; pytest 9.2.0; fastapi 0.162.0; httpx 0.28.1; sse-starlette 3.6.0.
- PostgreSQL 16.15.
- bun 1.4.4; node 22.22.0; vitest 4.1.5.
