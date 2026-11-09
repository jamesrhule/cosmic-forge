# W1 security round 2, worker lane (`build/w1-sec-worker`)

Gate 1 fix lane for the worker: job execution, the queue, run streams and
custom potentials. These are cluster c3 of the round-2 verification, plus the
SF1, SF2 and SEC-L3 residuals. The branch is based on `9c6bf4c`.
Evidence: `docs/build/evidence/W1-security-round2-worker.md`.

Finding IDs used here and in the evidence:

| ID | Verifier's finding |
|---|---|
| c3-expr-caps | `m2_scalar/potentials.py:132`: the caps can be bypassed (`^`, constants wrapped in calls, nested power towers). L3 residual. |
| c3-gil-timeout | `worker.py:448`: the thread-based JOB_TIMEOUT cannot stop a handler that holds the GIL. |
| c3-timeout-parse | `worker.py:51`: inf, nan and values above TIMEOUT_MAX are accepted, the CLI value is not checked, and an error in `join` leaves the job unfailed. |
| c3-lock-order | `20261031200300:49`: the dead-letter branch and `cancel_run` take their locks in opposite orders. |
| c3-attempt-lease | `worker.py:82`: an abandoned attempt's in-flight write lands after `_fail`. SF2 residuals (1) and (2): the lease is the worker id alone, terminal runs can change, and the lease check takes no row lock. |
| c3-guarded-queue | SF2 residual (3): `_GuardedQueue` passes `complete`, `heartbeat`, `cancel_run`, `enqueue_run`, `_emit` and `engine` through. |
| c3-stream-bounds | `m8_agent/settings.py:73`: healthy long runs are aborted as idle and the client doesn't reconnect. SF1 residuals (1), (2) and (3): a terminal run with no terminal event, and the max bound checked only on empty polls. |
| c3-claim-after-abandon | `worker.py:350`: the worker keeps claiming after an abandonment, and a lost lease does not end the wait. |
| c3-provenance-upload | `worker.py:134`: provenance is uploaded with no lease check. |
| c3-healthy-race | `worker.py:335`: `healthy()` rebinds the abandoned list while the loop appends to it. |

## Decisions

- **c3-gil-timeout: each job runs in its own child process.**
  - The child is started with `multiprocessing` "spawn" and is never reused for another job.
  - The parent keeps the heartbeat thread, `/healthz` and the wall-clock limit.
  - At the limit, on a lost lease, or on any error while waiting, the parent terminates the child, waits 2 s, kills it, and waits 2 s more.
  - A child that survives the kill goes into `Worker.abandoned` (see c3-claim-after-abandon).
  - The time limit counts the child's start-up (about 0.4 s).
  - Defence in depth:
    - `RLIMIT_CPU` soft limit = ceil(timeout × usable CPUs) + 30 s; hard limit = soft + 5 s.
    - `PR_SET_PDEATHSIG = SIGKILL` (Linux), so a child dies if its worker dies.
- **c3-gil-timeout / c3-attempt-lease: the child has no write path of its own.**
  - The handler's `ctx.queue` exposes only `set_run_status`, `save_result`, `record_provenance`, `emit` and `job_status`.
  - Each call is a request over a pipe to the worker process. The worker applies it under the attempt's lease, for the job's own run and tenant only, or refuses it. A refusal raises `JobCancelled` in the handler.
  - The worker serves requests on the same thread that enforces the limit, so once it abandons an attempt, nothing of that attempt is applied.
  - The child still builds its own DB engine from the same environment (`DATABASE_URL`) when handler code reads the database, for example the P3-05 budget hook.
  - Why requests to the parent rather than the child writing through its own engine: a killed child's last statement could still commit after the parent's failure. With requests, writes land strictly before the abandonment.
  - After a refused write, the child gets 2 s to report its own outcome before it is stopped.
  - Handlers are pickled by reference, so they must be module-level functions. `_owned_elsewhere` handlers are now `functools.partial` of a module-level function.
  - The child installs the router budget hook only when the parent has it installed, and sets the job's tenant as before.
- **c3-gil-timeout: `ucgle_f1.m8_agent/__init__.py` now loads `build_app`/`run` on first use (PEP 562).**
  - Before, `import ucgle_f1.m8_agent.auth` loaded the whole API server, about 1.9 s in every job process.
  - It now takes about 0.4 s for the child's whole start-up.
  - `from ucgle_f1.m8_agent import build_app` works as before.
- **c3-attempt-lease: a lease is (job, worker id, attempt, run).**
  - `attempt` is `jobs.attempts` as the claim returned it. The next claim increments it, so an abandoned attempt, or a stale worker that reuses the same worker id, never matches again.
  - Migration `20261102105000_qcompass_queue_attempt_lease.sql` adds:
    - `heartbeat_job(job, worker, attempt, lease)`;
    - `complete_job(job, worker, attempt, result, error)`.
    - The forms without an attempt now raise, as `20261031200300` did for the 3-argument `complete_job`.
  - The down migration restores the `20261031180000` heartbeat body and the `20261031200300` complete body.
  - In Python:
    - `JobQueue.heartbeat` and `complete` take a keyword-only `attempt`.
    - The run, result, provenance and event writes take `job_id`, `worker_id` and `attempt` together, or none of them. A partial lease raises `ValueError`.
- **c3-attempt-lease: lease check and write are one locked step.**
  - The lease subquery locks the job row `FOR SHARE` until the write commits.
  - A cancel or completion therefore lands wholly before or after the write.
- **c3-attempt-lease: terminal run states are sticky in SQL.**
  - Trigger `runs_status_transition` allows only these status changes, for every writer (service, worker, janitor, client):
    - queued → running / failed / canceled;
    - running → completed / failed / canceled.
  - Any other status change raises `check_violation`.
  - `set_run_status` carries the same rule as a predicate, so a refused write returns False instead of raising.
  - `save_result` and `save_provenance` write only while the run is queued or running, so a terminal run's result never changes.
  - If a write is refused because the run already ended while the lease is still held (a re-run of a job whose `complete()` failed), the attempt fails the job. It no longer leaves the job to be retried until it dead-letters.
- **c3-lock-order: one lock order, the job rows before the run row, everywhere.**
  - `JobQueue.cancel_run` now takes `select … from jobs where run_id = … order by id for update` before the run.
  - That is the janitor's order, and the lease-checked writes' order through `FOR SHARE`.
  - `reap_expired_jobs` is unchanged, so no migration was needed for this item.
- **c3-stream-bounds: a running job is never idle.**
  - Every lease renewal (every lease/3, 20 s by default) also appends a lease-checked `heartbeat` row to `job_events`, until the attempt sets its run terminal. A 1-hour job adds about 180 rows.
  - The SSE, WS and legacy streams count these rows as activity but never send them to clients. The idle default stays 900 s.
  - The max bound is checked on every poll.
  - The stream checks the run itself after every 1 s of silence. A run that has been terminal for 2 s (database clock, `completed_at`) without a terminal event gets a synthesized terminal `status` event, then `end`. The legacy stream yields the stored result for a completed run.
  - Frontend:
    - One resumable stream (`runEventStream` in `src/lib/sdk.ts`) serves both `services/qcompass/runs.ts` and `services/simulator.ts`.
    - On `STREAM_ABORTED` it asks whether the run ended. If not, it reconnects (at most 20 times) and skips the events it already delivered; the server replays a run's events in id order.
    - A cosmology stream that ends before its run did is now a `STREAM_ABORTED` error instead of a silent end.
- **c3-expr-caps: sympy never sees the raw string.**
  - Python's `ast` parses the snippet once. No sympy parser, so `^` stays XOR and is refused with "write powers with '**'".
  - The unevaluated tree is allow-listed: numbers, names, `+ - * / **`, unary ±, and calls to `sqrt log exp sin cos tanh cosh sinh` with one argument, or `Rational` with integer literals.
  - Then every node is bounded before any evaluation:
    - literals |x| ≤ 1e30;
    - every exponent |x| ≤ 64, whether or not it looks constant;
    - digits of any exact number ≤ 1000;
    - the factor of an `exp` of a `log` ≤ 64;
    - ≤ 512 nodes, and ≤ 32 levels of real nesting (the left spine of a sum or product counts as one level, as sympy flattens it).
  - A symbol counts as a number of magnitude 1. This keeps the bounds sound when symbols cancel (`phi - phi + 9**9`).
  - Only then is the same tree evaluated with sympy's operators. For every accepted input the result is the expression `sympify` built before, compared with `srepr` (`test_c3_expr_caps_real_potentials_compile_as_before`).
  - Behaviour changes:
    - `^` is refused.
    - A name that is not a declared symbol is a parameter symbol, never a sympy global (`E`, `I`, `oo`, `gamma`…).
    - A function name that isn't called is refused.
  - Measured: a 31-deep `exp(exp(…))` compiles in 0.9 s. A Horner form 50 levels deep took 15 s, which is why nesting is capped.
- **c3-timeout-parse: an invalid limit refuses to start.**
  - `QCOMPASS_JOB_TIMEOUT_SECONDS` and the constructor/CLI value must be finite, > 0 and ≤ `threading.TIMEOUT_MAX` (`MAX_JOB_TIMEOUT_SECONDS`).
  - Otherwise `Worker(...)` raises `ValueError`, and `python -m qcompass_worker` exits 2 with the message.
  - Any exception while the worker waits on a job (`JOB_ABANDONED`) stops the child and fails the job.
- **c3-claim-after-abandon:**
  - `run_once` claims nothing while a job process in `abandoned` is alive. It still runs the janitor.
  - A lost lease (the heartbeat returns False) ends the wait within one 0.1 s poll, and the child is stopped.
- **c3-provenance-upload:**
  - The worker process does the upload. It renews the lease (`heartbeat_job`) immediately before the Storage put, and uploads nothing if the lease is gone; the row is lease-checked again.
  - The object path stays `run-artifacts/<run>/provenance.json`, which `test_provenance_is_a_row_and_a_run_artifacts_object` pins.
  - An upload already in flight when a cancel commits can still land. Every earlier window is closed.
- **c3-healthy-race:**
  - `healthy()` only reads `abandoned`, under `Worker._lock`.
  - Dead entries are pruned on the loop thread.

## Corrected tests (old → new)

- **c3-gil-timeout:** `backend/tests/test_security_gate1.py::test_l3_hung_handler_is_abandoned_and_the_job_fails_with_job_timeout`.
  - Old:
    - a closure handler `hang` that waits on a `threading.Event`, then tries `save_result` and appends the exception name to a list;
    - `assert worker.healthy() is False, "a wedged handler thread makes /healthz fail"`;
    - after release, `assert late == ["JobCancelled"]` and `assert worker.healthy() is True`.
  - New:
    - the module-level `gate1_worker_handlers.ignore_cancel_and_sleep`, which sleeps 2 s, then tries `save_result` and `completed`;
    - `assert worker.abandoned == [] and worker.healthy() is True`;
    - after 3 s, `assert (tmp_path / "started").exists() and not (tmp_path / "finished").exists()`, `assert q.result("run_hang") is None`, and the run is still `failed`.
  - The JOB_TIMEOUT, run-failed and wall-clock assertions are unchanged.
  - Why:
    - A handler now runs in a spawned process. A closure can't be sent there, and a `threading.Event` or list in the test process can't be shared with it.
    - The old `healthy() is False` described the thread design's limit: a thread can't be killed, so `/healthz` had to fail until the container was replaced.
    - Now the job process is killed at the limit, so nothing wedged remains.
    - "Unhealthy while a job survives the kill" is still tested, by `test_c3_claim_nothing_while_an_abandoned_job_is_alive`.
    - The new test also proves the handler was stopped, not only that its write raised.
- **c3-attempt-lease:** `test_security_gate1.py::test_sf2_cancel_racing_completion_keeps_the_run_canceled`.
  - Old: a closure handler `finish_after_cancel` coordinated with two `threading.Event`s, and `assert outcome == ["JobCancelled"]`.
  - New: the module-level `gate1_worker_handlers.attempt_gated`, coordinated through files (`started-1`, `go-1`), and `assert (tmp_path / "outcome-1").read_text() == "JobCancelled"`.
  - The other assertions are unchanged. Why: same reason as above (the handler runs in a child process).
- **c3-timeout-parse:** `test_security_gate1.py::test_l3_job_timeout_is_configurable`.
  - Old: `for raw in ("0", "-5", "soon"): assert job_timeout_seconds_default() == 3600, "no way to disable the limit"`.
  - New: the same values give `pytest.raises(ValueError, match="no way to disable the job time limit")`.
  - Why: the finding requires invalid values to refuse to start. Falling back to 3600 silently hid a misconfigured worker. The test's intent, that the limit can't be disabled, is kept.
- **c3-attempt-lease:** `test_security_gate1.py::test_sf1_sf2_queue_migration_is_reversible`.
  - Old:
    - `rollback("20261031200300")` only;
    - re-apply expected `["20261031200300"]`;
    - final `assert len(procs()) == 2`.
  - New:
    - `rollback("20261102105000")` first, then `rollback("20261031200300")`;
    - re-apply expects `["20261031200300", "20261102105000"]`;
    - final `assert procs() ==` the exact set of three `complete_job` signatures.
  - Why:
    - `20261102105000` replaces the bodies that `20261031200300` created. Rolling `200300` back alone, with the later migration still applied, would restore a lease-checked 4-argument `complete_job` over the refusing one.
    - The new overload makes the count 3. The exact-set check is stricter than a count.
- **c3-attempt-lease:** `backend/tests/test_postgres_stores.py::test_worker_queue_migration_is_reversible_without_data_loss`.
  - Old:
    - `rollback("20261031180000")` only;
    - in `finally`, `assert apply_migrations(url) == ["20261031180000"]`, then `rollback("20261031200300")` and `apply_migrations(url)`.
  - New:
    - `rollback("20261102105000")`, `rollback("20261031200300")`, `rollback("20261031180000")`, newest first;
    - in `finally`, `assert apply_migrations(url) == ["20261031180000", "20261031200300", "20261102105000"]`.
  - The data-loss and dropped-object assertions are unchanged.
  - Why: `20261102105000` adds a 4-argument `heartbeat_job`, which `20261031180000`'s down doesn't know about. Rolled back out of order, `to_regproc('public.heartbeat_job')` still found that overload. Rolling back newest first is the order the migrations depend on, and it leaves the schema exactly as it was.
- **c3-attempt-lease (API: a lease now names its attempt).** Assertions are unchanged; each lease-carrying call gained the attempt of its claim:
  - `test_worker_queue.py::test_heartbeat_janitor_requeue_and_dead_letter`: `q.heartbeat(…, attempt=job.attempts)` ×2 and `q.complete(…, attempt=again.attempts, …)`.
  - `test_worker_queue.py::test_cancel_stops_the_lease`: `q.heartbeat(…, attempt=job.attempts)`.
  - `test_security_gate1.py::test_sf1_dead_letter_fails_the_run_and_writes_a_terminal_event`: `set_run_status(…, attempt=job.attempts)`.
  - `test_security_gate1.py::test_sf2_a_stale_worker_cannot_touch_a_reclaimed_job`: every call of worker A or B passes `attempt=a.attempts` or `attempt=b.attempts`.

## Removals with replacement

- **c3-gil-timeout:**
  - The handler thread (`threading.Thread` + `join(timeout)`) → a child process per job (`_run_child`, `_wait_child`, `_stop_child`).
  - `JobContext(job, queue, lost, worker_id)` → `JobContext(job, queue)`, where `queue` is the child-side `_GuardedQueue`.
- **c3-guarded-queue:** `_GuardedQueue.__getattr__` pass-through → explicit methods: `set_run_status`, `save_result`, `record_provenance`, `emit`, `job_status`. Nothing else of `JobQueue` is reachable.
- **c3-provenance-upload:** the handler's `ArtifactStore().put` + `ctx.queue.save_provenance` → `ctx.queue.record_provenance(run_id, record)`. The worker process does the lease check, the upload and the row.
- **c3-attempt-lease:** SQL `heartbeat_job(job, worker, lease)` and `complete_job(job, worker, result, error)` → refuse. They are replaced by the attempt forms, and the down migration restores them.
- **c3-expr-caps:**
  - `sympy.sympify(source)` → `_check_shape` + `_Checker` + `_build`, evaluated from the checked `ast`.
  - `_check_custom_size` and `_constant_digits` → `_Checker`.
- **c3-stream-bounds:** `apiStream(sdk.streamRun(…))` in `services/qcompass/runs.ts` and `services/simulator.ts` → `runEventStream`.

## BLOCKED-ON-JAMES

None. No fix in this lane needs a secret.
