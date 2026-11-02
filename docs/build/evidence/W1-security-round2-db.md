# W1 — Gate 1 security review, round 2: database, authorisation, tokens, run ids

Branch `build/w1-sec-db`, based on `9c6bf4c`. Lane notes: `docs/build/lanes/W1-sec-db.md` (decisions, corrected tests, removals, BLOCKED-ON-JAMES). Findings: the round-2 verifiers' c1-tenant, c2-rls and c4-memory reports, ids as in the lane notes.

Method (LEDGER decision 14):

- One regression test per finding, in `backend/tests/test_security_gate1_round2.py`. Each drives HTTP or SQL (as PostgREST's `authenticated` role, via `request.jwt.claims`) and uses only APIs that existed before the fix, so on the pre-fix tree it fails on the bug itself, not on an import or a missing fixture.
- Database changes are four new migrations (`20261102100000`–`20261102100300`), each with a down migration under `supabase/migrations/down/`. No existing migration was edited.
- "Before" was measured by running the new test file against `9c6bf4c`'s sources: `git archive 9c6bf4c backend supabase` into a scratch directory, then `PYTHONPATH=<scratch>/backend/src python -m pytest tests/test_security_gate1_round2.py` from `<scratch>/backend` with this branch's venv (dependencies unchanged), so the scratch tree's own migrations, shim and pytest plugin were used on a fresh Postgres 16 cluster. The two rewritten SEC-H1 tests were run the same way against `3d2355a` (the round-1 reviewed head) with that tree's own venv.
- The verifiers' repro scripts under `scratchpad/gate1/scratch-c1`, `scratch-c2` and `scratch-c4-memory` were run unchanged against `9c6bf4c` first: every scenario below reproduced (for example `test_c1_slug.py`: 4 failed, i.e. the bypass and both backfill cases are real; `test_c4_after_only.py::test_tool_call_log_exposes_approval_tokens_to_members`: the token is in `requestJson`).

## Per finding

"9c6bf4c" is the first failing assertion on the pre-fix tree. Every finding is fixed; none was a false positive.

| Id | Fix | Regression test | 9c6bf4c | After |
|---|---|---|---|---|
| R2-DEV-SLUG | `20261102100000`: trigger `tenants_write_guard` (non-service writers cannot set slug `dev` in any case or change `created_by`); `AuthStore` never treats a user-owned `dev` as its dev tenant | `test_r2_owner_cannot_take_the_dev_slug_or_clear_created_by`; `test_r2_dev_api_never_uses_a_user_owned_dev_tenant[creator,member]` | `DID NOT RAISE CheckViolation` (the owner's `slug='dev', created_by=null` update succeeded); `resolve_tenant('dev')` returned the squatter's tenant (both cases) | pass |
| R2-SF4-BACKFILL | `20261102100100`: agent rows of a user-owned `dev` tenant set back to `tenant_id` null (`20261031200400` not edited) | `test_r2_sf4_backfill_never_hands_agent_rows_to_a_user_owned_dev_tenant[creator,member]` | mallory read `{'agent_patches': 1, 'agent_tool_calls': 1, 'agent_hypotheses': 1}` legacy rows (both cases) | pass |
| R2-H1-TESTS | `test_h1_no_dev_tenant_fallback_outside_dev` and `test_h1_resolve_tenant_prefers_the_id_match_and_slug_guard_is_reversible` rewritten to observe behaviour (tightened; old → new in the lane notes) | those two tests | on `3d2355a`: `DID NOT RAISE RuntimeError` (submit with no tenant created and used a shared `dev` tenant); `resolve_tenant(victim)` returned the shadow row's id. Before the rewrite they failed there only with ImportError / FileNotFoundError | pass |
| R2-CHAT-LOOP | `/v1/chat` runs `_dispatch` and `record_tool_call` in `asyncio.to_thread` | `test_r2_chat_tool_calls_do_not_block_the_event_loop` (a row lock holds `cancel_run`; `/healthz` must answer within 5 s on the same event loop) | `the event loop was blocked by the tool call` | pass |
| R2-UUID-SLUG | `20261102100000`: `tenants_slug_not_uuid_check` (castability via `qcompass_text_is_uuid`) | `test_r2_slugs_that_cast_to_uuid_are_refused` (3 cases) | `DID NOT RAISE CheckViolation` for `a0ee-bc99-9c0b-4ef8-bb6d-6bb9-bd38-0a11` and `{a0eebc99-9c0b4ef8-bb6d6bb9-bd380a11}`; the 32-hex uppercase case passed (the old regex covered it; kept as a guard) | pass |
| R2-TIER | `20261102100000`: `subscription_tier` immutable for non-service writers, forced `free` on their inserts | `test_r2_owner_cannot_raise_their_own_plan` (end to end: free tenant 202, 429, upgrade refused, still 429; service upgrade then 202) | `DID NOT RAISE InsufficientPrivilege` (the owner's update to `enterprise` succeeded) | pass |
| R2-M1-USING | `20261102100200`: `qcompass_can_write_run` in USING and WITH CHECK of runs insert/update/delete, results, audits, timelines and storage write/update/delete | `test_r2_writes_hung_off_a_run_need_a_writer_of_its_tenant`; `test_r2_storage_writes_need_a_writer_of_the_runs_tenant` | `assert 1 == 0`: a non-member author moved their run out of globex; `DID NOT RAISE InsufficientPrivilege`: a non-member author planted `run_planted/forged.json` | pass |
| R2-VIEWER-PLANT | `20261102100200` (viewers write nothing hung off a tenant run); the API serves only runs it created (`author_user_id is null`) | `test_r2_api_never_serves_client_written_tenant_runs` | `DID NOT RAISE InsufficientPrivilege` (viewer carol inserted a completed globex run) | pass |
| R2-QUOTA | `plans.enforce_at_enqueue` counts API-created runs only | `test_r2_client_rows_do_not_count_against_the_monthly_quota` | 429 `PLAN_RUNS_PER_MONTH_EXCEEDED` "25 used" after a member's 25 rows dated 2099 | pass |
| R2-STORAGE-SHIM | `supabase_shim.sql` grants on `storage.objects` (and select on buckets) as Supabase does; `storage.objects` truncated per test | `test_r2_storage_grants_match_supabase` (privileges, then a member reads its tenant's artefact) | `has_table_privilege('anon', 'storage.objects', 'select')` false | pass |
| R2-FORGED-REPORT | `20261102100200`: service-only `qcompass_forged_row_report()`; NOTICE with the count | `test_r2_forged_row_report_lists_and_keeps_forged_rows` | n/a: a new capability; on `9c6bf4c` the function does not exist (UndefinedFunction), which is the gap itself | pass |
| R2-TOKEN-LOG | `record_tool_call` redacts `token`, `approval_token`, `*_token` | `test_r2_tool_call_log_never_stores_approval_tokens` | the token id and `s3cret` were in the viewer-readable `requestJson` | pass |
| R2-TOKEN-RACE | one conditional `UPDATE … RETURNING` spends a token (tenant, unspent, unexpired, scope) | `test_r2_an_approval_token_is_spent_once_across_instances` (two store instances with separate locks, both blocked on a row lock, then released) | `one-shot token accepted 2 times` | pass |
| R2-TOKEN-TTL | no `*`; named scopes; `ttl_seconds` in (0, 3600] else 422; every token one-shot | `test_r2_approval_tokens_are_one_shot_scoped_and_short_lived` | `ttl_seconds: 1e9` answered 200 (expiry 2058) | pass |
| R2-RUN-ID | `20261102100300` + API: server-generated ids, `runs.client_run_id` per-tenant alias; SDK regenerated | `test_r2_run_ids_are_per_tenant_aliases` (cross-tenant, PostgREST squat, alias lookup, stream, own-alias 409) | `another tenant's runId does not block this one` (globex got 409 for acme's runId) | pass |
| R2-PLAN-PATH | `save_plan` under `agent-sandbox/<tenant>/<conversation>/` via `safe_component`/`safe_join`; relative path stored | `test_r2_plans_stay_in_the_tenant_sandbox_and_store_a_relative_path` | `DID NOT RAISE ValueError` (`../../escaped` written outside the sandbox) | pass |
| R2-START-ORDER | `start_run`: agent trace, tenant's hypothesis, config, then the token | `test_r2_start_run_validates_before_spending_and_needs_the_tenants_hypothesis`; A6 `test_start_run_rejects_a_hypothesis_the_tenant_never_recorded` | `assert 200 == 409`: acme's run linked globex's hypothesis | pass |
| (R13 guard) | each new migration's down and up | `test_r2_migrations_are_reversible` (4 cases: schema identical after down/up, alias data kept) | n/a: guard for this lane's migrations (they don't exist on `9c6bf4c`) | pass |

Totals for `test_security_gate1_round2.py` on `9c6bf4c`: 25 failed, 1 passed (the uppercase-UUID guard case). Of the 25, 20 fail on the finding's own bug; 1 (`R2-FORGED-REPORT`) and 4 (reversibility) fail because the capability is new. After the fix: 26 passed.

Corrected round-1 tests, run on `9c6bf4c`'s sources: the setup-only corrections (`test_h1_post_api_runs_files_the_run_under_the_callers_tenant`, `test_sf4_agent_memory_is_tenant_scoped`, A6 `test_start_run_links_run_to_conversation`, `test_start_run_rejects_without_approval`), the corrected `test_m1_runs_policy_migration_is_reversible` and both rewritten SEC-H1 tests pass there (8 passed), so the corrections hide nothing. The corrected `test_l2_run_id_collision_does_not_reveal_another_tenants_run` and the new A6 `test_start_run_rejects_a_hypothesis_the_tenant_never_recorded` fail there on the bugs (a foreign runId answered 409; an unrecorded hypothesis was linked).

## Suites (branch head, after all changes)

| Check | Command | Result |
|---|---|---|
| Backend fast | `cd backend && uv run --frozen pytest -q -m "not slow"` | 555 passed, 2 deselected, 1 xfailed (the pre-existing V2 xfail); exit 0 |
| Backend slow | `cd backend && uv run --frozen pytest -q -m slow` | SLOW_RESULT |
| Packages | `uv run --frozen pytest packages -q --import-mode=importlib` | PACKAGES_RESULT |
| ESLint | `bun run lint` | exit 0; 0 errors, 15 warnings (all outside changed files, as on `9c6bf4c`) |
| Prettier | `bunx prettier --check .` | exit 0; all matched files formatted |
| TypeScript | `bunx tsc --noEmit` | exit 0 |
| Vitest | `bun run test` | 21 files, 116 tests passed |
| Build | `bun run build` | exit 0 |
| R19 | `scripts/check_r19.sh` | 9 PNGs match `R19.sha256` |
| SDK types | `scripts/gen_sdk_types.sh --check` | "SDK types match the API's OpenAPI document." |
| uv lock | `uv lock --check` | exit 0 |
| Playwright | PLAYWRIGHT_CMD | PLAYWRIGHT_RESULT |

No PNG, `R19.sha256`, `backend/audit/physics/**`, `backend/audit/golden.lock` or drift-alarm workflow was touched. No frontend source changed (only the SDK's generated types and one doc comment in `packages/ts/qcompass-frontend-sdk/src/types.ts`), so the cosmology fixture pages are unchanged.

## Versions

Python 3.12.13, pytest 9.2.0, pytest-asyncio 1.4.1, FastAPI 0.162.0, Starlette 1.10.0, pydantic 2.14.2, psycopg 3.3.6, SQLAlchemy 2.1.6, sqlmodel 0.0.48, PostgreSQL 16.15, uv 0.11.32, bun 1.4.4, Node 22.22.0, Vitest 4.1.5, Playwright 1.59.1 (Chromium from `/opt/pw-browsers`, `PW_CHROMIUM_PATH`).
