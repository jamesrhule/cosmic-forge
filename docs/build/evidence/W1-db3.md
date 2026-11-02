# W1 — Gate 1 round 3B, lane DB3: database and authorisation residuals, worker provenance, decision-14 test method

Branch `build/w1-db3`, based on `15e4e3c`. Lane notes: `docs/build/lanes/W1-db3.md` (finding ids, decisions, corrected tests, removals, routing, BLOCKED-ON-JAMES).

Method (LEDGER decision 14):

- One regression test per finding. Each drives HTTP, SQL (as PostgREST's `authenticated` role, via `request.jwt.claims`) or calls that already existed on the tree it is measured against, so on that tree it fails on the bug itself.
- Database changes are three new migrations, `20261102120000` (runs origin marker and alias index), `20261102120100` (report kinds) and `20261102120200` (agent dev guard), each with a down migration under `supabase/migrations/down/` that restores the previous version. No existing migration was edited.
- No new secret name. No file under `backend/audit/physics/`, `golden.lock`, `e2e/__screenshots__/`, `R19.sha256`, `PLAN.md`, `LEDGER.md` or `PROGRESS.md` was touched; the only frontend file changed is the SF5 vitest.

## How "before" was measured

- **Round-3B items (`15e4e3c`).** `git worktree add --detach scratchpad/round3b/base-15e4e3c 15e4e3c`. The new and changed test files were copied into its `backend/tests/` under a `_r3b_` prefix and run from `<base>/backend` with `PYTHONPATH=<base>/backend/src` and this branch's venv (Python dependencies unchanged), so the base tree's own sources, migrations, shim and pytest plugin ran on a fresh Postgres 16 cluster. The scratch worktree was removed afterwards.
- **R3B-D14 (`3d2355a`).** The read-only checkout `scratchpad/gate1/before` was used with its own `.venv`. Nothing was written into it: the test file (as `_r3b_gate1.py`), `gate1_worker_handlers.py`, `data/gate1_run_result.json` and a `conftest.py` that loads `ucgle_f1.db.pytest_plugin` were copied into a scratch directory and run with `gate1/before/.venv/bin/python -m pytest`; `ucgle_f1` resolves to `gate1/before/backend/src`. For the vitest, `gate1/before`'s `src/`, `packages/`, configs and `package.json` were copied to a scratch directory with `node_modules` linked to this branch's (the lockfile is the same), the test copied in as `_r3b_cosmologyLive.test.ts`, and `bunx vitest run` was used. Both scratch directories were deleted afterwards.
- **The verifiers' repros, run unchanged** against both trees: `round2/scratch-verify-DB/probes/{test_author_setnull,test_alias_delete,test_slugsquat}.py`, `gate1/scratch-c1/test_c1_slug.py::test_sf4_backfill_with_preexisting_user_dev_tenant_left_not_valid`, `gate1/scratch-c4-memory/test_c4_after_only.py::test_backfill_into_user_owned_dev_tenant`, `round2/scratch-verify-WORKER/http/test_prov_inflight.py`, `round3/scratch-verify-OPS/{jwks_repro,jwks_stress}.py`.

## Per finding

"Before" is the first failing assertion on the pre-fix tree (`15e4e3c` unless marked `3d2355a`). Every finding was confirmed; none was a false positive.

| Id | Fix | Regression test | Before (reason) | After |
|---|---|---|---|---|
| R3B-API-ORIGIN | `20261102120000`: `runs.origin` (`'api'` / `'client'`), forced `'client'` for non-privileged writers by `runs_origin_guard`; `JobQueue` reads and `plans.enforce_at_enqueue` use `origin = 'api'`; `enqueue_run` sets it | `test_security_gate1_round3b.py::test_r3b_client_runs_stay_client_runs_after_the_authors_account_is_deleted` (member plants a completed run, its result and 25 runs dated 2099; the account is deleted) | `assert 200 == 404`: after the deletion, `GET …/chemistry/runs/qc_planted` served the planted run | pass |
| R3B-API-ORIGIN (guard) | same | `test_r3b_clients_cannot_mark_a_run_as_the_apis` (insert with `origin='api'` stored as `client`; updates of `origin`/`client_run_id` refused; the client's status flow still works; the API's run is `api`) | not counted: `UndefinedColumn "origin"` (new capability) | pass |
| R3B-ALIAS-INDEX | same migration: alias index `where client_run_id is not null and origin = 'api'`; clients' `client_run_id` forced null / immutable | `test_r3b_a_members_account_stays_deletable` | `UniqueViolation … runs_tenant_client_run_id_key … (…, q3) already exists`, raised by the `ON DELETE SET NULL` of `delete from auth.users` | pass |
| R3B-SLUG-SQUAT | `AuthStore._key_tenant` for `issue()`: by slug only a tenant with no creator and no member, else `TENANT_RESERVED`; by UUID an existing tenant | `test_r3b_a_key_is_never_bound_to_a_squatted_slug` | `DID NOT RAISE AuthError`: `issue('newcustomer')` bound the key to mallory's renamed personal tenant | pass |
| R3B-TENANT-RESERVED | `HTTP_STATUS_FOR_CODE["TENANT_RESERVED"] = 409`; `AuthError` handler in `install_error_handlers` | `test_r3b_a_user_owned_dev_tenant_answers_409` (dev mode, anonymous submit, user-owned `dev`) | `assert 500 == 409` (`{"code":"INTERNAL"}`) | pass |
| R3B-AGENT-DEV-GUARD | `20261102120200`: `qcompass_agent_memory_dev_guard` on the six `agent_*` tables | `test_r3b_agent_rows_never_land_in_a_user_owned_dev_tenant[creator,member]` (single-version down/up of `20261031200400`) | `the user-owned 'dev' reads another customer's agent rows: [('victim-convo',)]` (both cases) | pass |
| R3B-REDACT | `redact_secrets`: keys folded (lower case, no `_`/`-`/`.`) containing `token`, `secret`, `password`, `apikey` | `test_r3b_tool_call_log_redacts_every_secret_named_key` (`/v1/chat` tool call with `config.agent.approvalTokenId`, `tokenId`, `apiKey`, `API_KEY`, `client_secret`, `Password`, `refresh-token`; a viewer reads `requestJson`) | `'appr_…' is readable in the tool-call log` (the live approval token id) | pass |
| R3B-TIER-REPORT | `20261102120100`: report kinds `tenant_tier_not_free`, `client_run_without_author` | `test_r3b_forged_row_report_lists_paid_tiers_and_author_less_client_runs` | `a paid tier nobody billed is not listed` | pass |
| R3B-PLAN-PATH | `save_plan` under `agent-sandbox/<tenant UUID>/…` | `test_r3b_a_later_tenant_with_the_same_slug_gets_its_own_plan_sandbox` (acme renamed; a new `acme` saves a plan in the same conversation) | `two tenants share one plan sandbox` (both under `agent-sandbox/acme/c_shared/plans`) | pass |
| R3B-PROV-UPLOAD | per-attempt key `<run>/provenance-<job>-<attempt>.json`; refused row → object deleted; replaced object deleted | `test_security_gate1_worker.py::test_r3b_provenance_upload_in_flight_when_the_lease_is_lost_leaves_no_object` (the Storage POST blocks until the run is canceled) | `an object stayed in run-artifacts for the canceled run: ['/storage/v1/object/run-artifacts/run_prov_late/provenance.json']` | pass |
| R3B-TIMEOUT-PARSE | `_valid_timeout`: [`MIN_JOB_TIMEOUT_SECONDS` = 0.1, `TIMEOUT_MAX`], OverflowError → ValueError | `test_r3b_timeout_parse_huge_ints_and_tiny_limits_are_refused[10**400, 1e-300, 0.05]` | `OverflowError: int too large to convert to float`; `DID NOT RAISE ValueError` (1e-300, 0.05) | pass |
| R3B-TIMEOUT-PARSE (guard) | same | `test_r3b_timeout_parse_minimum_is_the_wait_resolution` (0.1 accepted; env `1e-300` refused) | not counted: `AttributeError: … MIN_JOB_TIMEOUT_SECONDS` | pass |
| R3B-JWKS-4XX | 4xx drops the cached set; stale-if-error on network errors, timeouts, 5xx only | `test_supabase_auth_jwks.py::test_r3b_a_4xx_from_the_jwks_endpoint_ends_stale_if_error[401,403,404]`; `test_r3b_a_4xx_on_a_forced_refetch_drops_a_fresh_set` | `old keys still verify after the JWKS endpoint answered 401` (and 403, 404): `assert 200 == 503`; `the fresh set was dropped with the 404`: `assert 200 == 503` | pass |
| R3B-JWKS-4XX (guard) | same | `test_r3b_5xx_keeps_stale_if_error[500,502,503]` | passes on both (unchanged behaviour) | pass |
| R3B-JWKS-DEADLINE | `_JWKS_FETCH_DEADLINE_S` (5 s): the leader gives up at the deadline; the default fetcher streams and stops reading past it (1 MiB cap) | `test_r3b_the_leaders_fetch_has_an_overall_deadline` (a local HTTP server drips the JWKS body, one byte per 0.05 s; deadline patched to 0.5 s) | `the JWKS fetch ran 9.0s past a 0.5s deadline (answered 200)` | pass (503 in about 0.5 s) |
| R3B-D14 H2 | (test rewrite) | `test_security_gate1.py::test_h2_run_reads_ignore_rows_written_under_another_tenant` | `3d2355a`: `the run shows provenance filed under another tenant` (was `TypeError: JobQueue.events() got an unexpected keyword argument 'tenant_uuid'`) | pass |
| R3B-D14 SF1 | (test rewrite) | `…::test_sf1_dead_letter_fails_the_run_and_writes_a_terminal_event` | `3d2355a`: `the dead-lettered job left its run running` (`'running' == 'failed'`; was `TypeError … 'job_id'`) | pass |
| R3B-D14 SF2 | (test rewrite) | `…::test_sf2_a_stale_worker_cannot_touch_a_reclaimed_job` | `3d2355a`: `a stale worker completed the job another worker holds` (`'succeeded' == 'running'`; was `TypeError … 'job_id'`) | pass |
| R3B-D14 SF5 | (test rewrite) | `cosmologyLive.test.ts` case 3 | `3d2355a`: `getRun` fetched `[ 'http://api.test/api/runs/run_a' ]`, not the platform route (was `cosmologyRunResult is not a function`); a guard, see below | pass |
| (R13 guard) | each new migration's down and up | `test_r3b_migrations_are_reversible[20261102120000, 20261102120100, 20261102120200]` (schema identical after down/up: policies, indexes, constraints, triggers, columns, function bodies; down restores `20261102100300`'s index and `20261102100200`'s report; `origin` data kept under `_deprecated_origin_20261102120000`) | not counted: the migrations don't exist on `15e4e3c` | pass |

Totals on `15e4e3c` for the 26 new tests (13 in `test_security_gate1_round3b.py`, 5 in `test_security_gate1_worker.py`, 8 in `test_supabase_auth_jwks.py`): 23 failed, 3 passed (the 5xx guards). Of the 23, 18 fail on the finding's own bug (the `0.05` timeout case is the same bug as `1e-300`: a limit below the minimum was accepted); 5 are guards of new capabilities (the origin-marker guard, the minimum-constant guard, 3 reversibility cases). After the fix all 26 pass.

### The verifiers' repros, unchanged

| Repro | `15e4e3c` | This branch |
|---|---|---|
| `probes/test_author_setnull.py` (round-2 DB) | after the deletion: `GET` 200 `{"forged": true}`, list `['qc_planted']`, submit 429 "27 used" | `GET` 404, list `[]`, submit 202 |
| `probes/test_alias_delete.py` | `deletion: UniqueViolation … runs_tenant_client_run_id_key` | `deletion: ok` |
| `probes/test_slugsquat.py` | the operator's `issue('newcustomer')` binds the key to mallory's tenant (probe runs through) | `AuthError: tenant slug 'newcustomer' belongs to a tenant a user created or joined …` at `issue()` |
| `scratch-c1/test_c1_slug.py::test_sf4_backfill_with_preexisting_user_dev_tenant_left_not_valid` | `assert [('victim-convo',)] == []` | pass |
| `scratch-c4-memory/test_c4_after_only.py::test_backfill_into_user_owned_dev_tenant` | `assert ([('acme/secre…ACME_SECRET')] == []` | pass |
| `scratch-verify-WORKER/http/test_prov_inflight.py` (prints every Storage request after the cancel; the probe does not tell methods apart) | `['…/run-artifacts/run_prov2/provenance.json']`, run canceled, no row: the object stays | the same per-attempt path twice (the POST, then this branch's DELETE), run canceled, no row |
| `scratch-verify-OPS/jwks_repro.py` cases 1-5 | 200/1, 200/2, 3 fetches, 503/2, 200/2, 401 401 200, 50×200 with 1 fetch | identical |
| `scratch-verify-OPS/jwks_stress.py` | max 1 concurrent fetch, 0 stale violations, 0 hung threads | the same (`calls=26 max_concurrent_fetches=1 alive_threads=0 stale_violations=0 inflight_left=0`) |

Storage's single-object delete was checked against the storage server's source (`supabase/storage`, `src/http/routes/object/deleteObject.ts`: `DELETE /object/:bucketName/*`, 200 "Successfully deleted") before `ArtifactStore.delete` used it (R10).

### Corrected tests: both directions

Each corrected test (old → new in the lane notes) was run in both directions:

| Test | Old version on this branch | New version on `15e4e3c` |
|---|---|---|
| `test_plan_limits.py::test_runs_per_month_at_and_over_the_boundary` (setup) | `DID NOT RAISE PlanLimitExceeded` (author-less seeds no longer count) | `UndefinedColumn "origin"` (schema of this branch) |
| `test_security_gate1_round2.py::test_r2_owner_cannot_raise_their_own_plan` (setup) | `AuthError TENANT_RESERVED` at `issue(<personal slug>)` | pass |
| `…::test_r2_forged_row_report_lists_and_keeps_forged_rows` | set mismatch (the two tier rows) | set mismatch (no tier rows: the residual) |
| `…::test_r2_plans_stay_in_the_tenant_sandbox_and_store_a_relative_path` | path mismatch (UUID vs slug) | path mismatch (slug vs UUID: the finding) |
| `test_worker_queue.py::test_provenance_is_a_row_and_a_run_artifacts_object` | path mismatch (`provenance-<job>-<attempt>.json` vs `provenance.json`) | path mismatch (the finding) |
| `test_security_gate1.py` H2, SF1, SF2 rewrites | old versions pass on this branch | new versions pass on `15e4e3c` (9 passed with `-k "h2 or sf1 or sf2"`) |

## Decision 14 on `3d2355a`: the corrected evidence

`test_security_gate1.py -k "h2 or sf1 or sf2"`, run as described above on `3d2355a`: 9 failed. Reasons:

| Test | `3d2355a` | Counted as the finding's regression test |
|---|---|---|
| `test_h2_member_cannot_insert_jobs_directly` | `DID NOT RAISE InsufficientPrivilege` | yes (SEC-H2, write side) |
| `test_h2_forged_cross_tenant_job_does_not_touch_the_victim_run` | `the handler never ran`: `['run_victim'] == []` | yes (SEC-H2, worker side) |
| `test_h2_run_reads_ignore_rows_written_under_another_tenant` | `the run shows provenance filed under another tenant` | yes (SEC-H2, read side; rewritten) |
| `test_h2_jobs_policy_migration_is_reversible` | `'tenant members enqueue jobs' not in {…}` | no: reversibility guard |
| `test_sf1_dead_letter_fails_the_run_and_writes_a_terminal_event` | `the dead-lettered job left its run running` | yes (REV-SF1; rewritten) |
| `test_sf1_streams_end_with_an_error_event_when_idle` | `the stream never ended` | yes (REV-SF1) |
| `test_sf2_a_stale_worker_cannot_touch_a_reclaimed_job` | `a stale worker completed the job another worker holds` | yes (REV-SF2; rewritten) |
| `test_sf2_cancel_racing_completion_keeps_the_run_canceled` (with `gate1_worker_handlers.py` copied beside it, as the H1 data file is) | `'wrote' == 'JobCancelled'`: the handler's writes after the cancel were accepted | yes (REV-SF2) |
| `test_sf1_sf2_queue_migration_is_reversible` | `'_job_id uuid, _worker_id text, …' in {'_job_id uuid, _result jsonb, _error text'}` | no: reversibility guard |

`cosmologyLive.test.ts` on `3d2355a`: 3 of 4 failed. Case 1 fails with `ServiceError` NOT_FOUND from `GET /api/runs/qc_c1` raised by `getRun` right after the submit (SF5's bug: the platform run was read on the legacy route, without waiting); this is SF5's regression test. Case 2 ("an unfinished run is not passed off as a result") passes on both trees: a guard. Case 3 now fails on the route (`getRun` read `/api/runs/run_a`); for an agent run that legacy route still answered, so it is a guard of the one-route reader, not counted. The "artefacts in API mode" case fails with `NOT_FOUND` instead of `NOT_IMPLEMENTED` (the artefacts nit).

`docs/build/evidence/W1-security-fixes.md` is corrected accordingly (H2, REV-SF1, REV-SF2, REV-SF5 and REV-B2 rows, plus a note on the method).

## Suites

Run on the branch head with every change (4 shared CPUs).

| Check | Result |
|---|---|
| `cd backend && uv run --frozen pytest -q -m "not slow"` | **727 passed**, 3 deselected, 1 xfailed (the parked V2 η_B), exit 0 |
| `cd backend && uv run --frozen pytest -q -m slow` | **3 passed**, 728 deselected, exit 0 |
| `cd backend && uv run --frozen pytest audit -q -m "not slow"` (frozen audit) | **92 passed**, 1 deselected, exit 0 |
| `cd backend && uv run --frozen pytest audit -q -m slow` (frozen audit) | **1 passed** (`test_gb_to_zero_decoupling`), exit 0 |
| Drift-alarm replay (`git archive` of `2f8f6a1` into a clean directory, own `.venv`): `uv sync --package ucgle_f1`, `uv pip install "dirhash>=0.5"`, `PYTHONPATH=src uv run pytest audit -q -m "not slow"`, dirhash | sync rc 0, pip rc 0; 90 passed, 2 skipped (A8: `qcompass_router` is not in the package-only sync, pre-existing), 1 deselected; dirhash `42805c73538df5eb0f9eb109ead9a541253d5371d71eac5ea04be0ffaf8e92dd` = `golden.lock`: **freeze intact** |
| `uv run --frozen pytest packages -q --import-mode=importlib` | **350 passed**, 7 skipped, exit 0 |
| `bun run lint` | 0 errors, 15 warnings (the pre-existing `react-refresh` warnings), exit 0 |
| `bunx prettier --check .` | all files formatted, exit 0 |
| `bunx tsc --noEmit` | exit 0 |
| `bun run test` (vitest) | **22 files, 119 tests passed**, exit 0 |
| `bun run build` | built, exit 0 |
| `scripts/check_r19.sh` | 9 PNGs match `R19.sha256`, exit 0 |
| `scripts/gen_sdk_types.sh --check` | SDK types match the API's OpenAPI document, exit 0 |
| `uv lock --check` | resolved 557 packages, exit 0 |
| Playwright chromium: `e2e/smoke.spec.ts`, `e2e/synthetic-fixture-badge.spec.ts` (production builds on workerd via `scripts/e2e_serve.sh`, ports 4417/4418) | **15 passed**, exit 0 (the first attempt's build was killed by the sandbox's memory pressure, SIGKILL, before any test ran; the rerun passed). No spec was added or changed. |

## R19

None. The branch changes no file that the cosmology pages render (`git diff 15e4e3c --stat -- src public index.html vite.config.ts package.json bun.lock wrangler.jsonc` lists only `src/lib/__tests__/cosmologyLive.test.ts`). Measured anyway: the three pages were rendered in Chromium (1440×900, reduced motion, animations frozen, footer masked, as `e2e/cosmology-byte-identity.spec.ts` does) from production builds served by `wrangler dev`, first from `15e4e3c` (baseline), then compared with `maxDiffPixels: 0, threshold: 0`:

| Render | `/` | `/visualizer` | `/visualizer/kawai-kim-natural` |
|---|---|---|---|
| `15e4e3c` baseline (sha256 prefix) | `c7241c10d5655712` | `c7beb300ad0fdf85` | `51bcfec5ae51e598` |
| this branch, 3 runs | identical ×3 | identical ×3 | identical ×3 |
| `15e4e3c` again, 2 runs (control) | identical ×2 | identical ×2 | 1 run identical, 1 run 1 pixel different |

The one-pixel difference is the base tree's own render-to-render variation on the kawai-kim page (seen before, `W1-security-fixes.md`), not a change. CI's three-browser job remains the authority.

## Versions

Python 3.12.13, uv 0.11.32, pytest 9.2.0, PostgreSQL 16.15, httpx 0.28.1, psycopg 3.3.6, SQLAlchemy 2.1.6, FastAPI 0.162.0, PyJWT 2.15.1; bun 1.4.4, vitest 4.1.5, Playwright 1.59.1 (Chromium from `PW_CHROMIUM_PATH`).
