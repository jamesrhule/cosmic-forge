# W1 security lane DB: Gate 1 round 2 (`build/w1-sec-db`)

Scope: the round-2 verifier findings on the database, authorisation, approval tokens and run ids (c1-tenant, c2-rls, c4-memory). Base `9c6bf4c`. Evidence: `docs/build/evidence/W1-security-round2-db.md`. Regression tests: `backend/tests/test_security_gate1_round2.py`, plus the two rewritten SEC-H1 tests in `backend/tests/test_security_gate1.py`.

Finding ids used below:

| Id | Verifier finding |
|---|---|
| R2-DEV-SLUG | c1 MEDIUM and c2 MEDIUM: the `dev` slug reservation is bypassed by nulling `created_by` in the same UPDATE; `AuthStore.ensure_tenant('dev')` then returns the user's tenant |
| R2-SF4-BACKFILL | c1 MEDIUM, c2 HIGH, c4 MEDIUM: `20261031200400` backfills every legacy agent row into a user-owned `dev` tenant |
| R2-H1-TESTS | c1 LOW: two SEC-H1 regression tests failed on `3d2355a` only through ImportError / FileNotFoundError |
| R2-CHAT-LOOP | c1 LOW: `_run_coroutine` blocks the `/v1/chat` event loop while `cancel_run` runs |
| R2-UUID-SLUG | c1 NIT: the UUID-shaped-slug regex misses forms Postgres casts to uuid |
| R2-TIER | c2 HIGH: an owner raises their own `subscription_tier` and escapes every plan limit |
| R2-M1-USING | c2 M1 partial: USING clauses of runs update/delete and "authors write results"; `audit_reports`, `viz_timelines` and the storage write/update/delete policies had no tenant test |
| R2-VIEWER-PLANT | c2 MEDIUM: a viewer plants completed tenant runs that the API serves |
| R2-QUOTA | c2 MEDIUM: the runs-per-month quota counts client-written rows (permanent lockout) |
| R2-STORAGE-SHIM | c2 LOW: the test shim grants nothing on `storage.objects`, so storage RLS tests were vacuous |
| R2-FORGED-REPORT | c2 residual: nothing detects rows forged before the fixes |
| R2-TOKEN-LOG | c4 LOW: approval token ids in `agent_tool_calls.requestJson`, readable by every member |
| R2-TOKEN-RACE | c4 LOW: `consume_approval` read-then-write; one-shot tokens spent twice across instances |
| R2-TOKEN-TTL | c4 LOW: `*` tokens never consumed, unbounded TTL, 500 on a huge TTL |
| R2-RUN-ID | c4 L2 open + LOW: run ids are one global client-chosen namespace (existence oracle and squatting) |
| R2-PLAN-PATH | c4 NIT: `agent_plans.path` is an absolute server path built from an unsanitised conversation id |
| R2-START-ORDER | c4 NIT: `start_run` spends the token before validating and never checks the hypothesis |

Every finding was reproduced on `9c6bf4c` before it was fixed; none was a false positive. Migrations use the versions `20261102100000`–`20261102100300` (this lane's range is `…100000`–`…104959`).

## Decisions

- **[R2-DEV-SLUG][R2-TIER] One trigger for column rules on `public.tenants`** (`20261102100000_qcompass_tenant_write_guard.sql`). `tenants_write_guard` (BEFORE INSERT OR UPDATE) applies to every caller that is neither `service_role` nor the table owner, judged by `public.qcompass_privileged_writer(regclass)`: `pg_has_role(current_user, <owner>, 'MEMBER') or pg_has_role(current_user, 'service_role', 'MEMBER')`. It keys on the database role, not on a JWT claim, so a PostgREST user (`authenticated`) is always restricted, while the API and worker (owner connection), `ensure_personal_tenant` (SECURITY DEFINER, owner) and migrations are not.
  - INSERT: `subscription_tier` is forced to `free`.
  - UPDATE: `subscription_tier` and `created_by` are immutable (`insufficient_privilege`).
  - INSERT or a slug change: `lower(btrim(slug)) = 'dev'` is refused (`check_violation`, the same SQLSTATE as `tenants_slug_reserved_check`, so round-1 assertions hold).
  - A trigger rather than a column REVOKE: main's "owners update tenants" policy and the table-level grants stay as they are, the rule does not depend on a user-writable column, and service writes need no special role.
- **[R2-DEV-SLUG] The API never uses a user-owned `dev`.** A `dev` tenant is the service's only when `created_by is null` and it has no `tenant_members` row (that is what `AuthStore.ensure_tenant('dev')` creates). `AuthStore.resolve_tenant('dev')` returns None for any other `dev`; `ensure_tenant('dev')` raises `AuthError` (`TENANT_RESERVED`, message `BLOCKED-ON-JAMES:rename-user-owned-dev-tenant`) instead of returning it. The owner still reaches their tenant by its UUID. The same rule (`auth._USER_OWNED_DEV`) is the one the backfill fix uses.
- **[R2-SF4-BACKFILL] New migration, `20261031200400` not edited** (`20261102100100_qcompass_agent_memory_dev_backfill_fix.sql`). It sets `tenant_id` back to null on rows of the six `agent_*` tables whose tenant is a user-owned `dev` (`created_by is not null`, or any member: the round-2 scenarios cover both a creator and the `created_by = null` bypass, where the squatter is a member). Null rows belong to no tenant and are invisible to every caller and to `ConversationStore`. Nothing is deleted; the count is reported with a NOTICE. Why this is safe:
  - No environment has applied `20261031200400`: `DATABASE_URL` is BLOCKED-ON-JAMES, and the backend harness builds a throwaway cluster per run. The first real deploy applies `…200400` and `…100100` in one `supabase db push` / `ucgle_f1.db.migrate` run, so the backfill is undone before any request is served.
  - The service's own `dev` tenant keeps the rows `…200400` gave it.
  - The real owner of a legacy tenant-less row is unknown, so null is the only safe owner.
  - The down migration deliberately changes nothing: restoring the assignment would hand other customers' legacy agent memory back to that user. No column, policy or row is removed in either direction (R13).
- **[R2-UUID-SLUG] Castability, not a regex.** `public.qcompass_text_is_uuid(text)` (IMMUTABLE, `perform _value::uuid` with an `invalid_text_representation` handler) backs a new constraint `tenants_slug_not_uuid_check check (not qcompass_text_is_uuid(slug))`, for every writer. Added NOT VALID and validated only when no row violates it (otherwise a NOTICE), like `20261031200000`. It is a separate constraint so `tenants_slug_reserved_check` (and its round-1 down/up test) stays untouched.
- **[R2-M1-USING][R2-VIEWER-PLANT] Writer role on every client write hung off a run** (`20261102100200_qcompass_client_run_writes.sql`). `public.qcompass_can_write_run(tenant, user)` is `tenant is null or tenant_role(tenant, user) in ('owner','admin','member')`. It is now in the USING and WITH CHECK of runs insert/update/delete, "authors write results", "authors write audits", "authors write timelines" and the storage policies "authors write/update/delete viz-timelines" and "authors write/delete run-artifacts". Viewers and non-members write nothing hung off a tenant run; reads are unchanged.
  - Grep for legitimate client writes before restricting: `supabase/functions/` does not exist. In `src/`, `src/lib/persistence.ts` upserts `runs` (never sets `tenant_id`), `run_results`, `audit_reports`, `viz_timelines` and uploads `viz-timelines/<runId>/timeline.json`; `src/services/simulator.ts` calls those helpers. `src/lib/billing.ts` and `src/lib/tenants.ts` only read `tenants`/`tenant_members`; `startCheckout` is a stub, and there is no Stripe or billing webhook anywhere (`grep -riE 'stripe|webhook'` over `src/`, `supabase/`, `workers/`, `apps/`, `backend/src` finds only `billing.ts`'s note that no provider is wired yet and an unrelated GitHub webhook comment in `tools/patch.py`). All of these keep working: they write personal runs (`tenant_id` null), or runs that main's `20260427001133` backfilled into the author's personal tenant, which the author owns. Billing will set `subscription_tier` through the service role.
  - Writer roles rather than `tenant_id is null` everywhere: authors keep their pre-April runs that the backfill filed under their personal tenant.
- **[R2-VIEWER-PLANT] The API serves only runs it created.** `JobQueue.get_run(…, tenant_uuid=…)`, `list_runs` and the tenant-joined result query add `author_user_id is null`. Every client-written row carries its author (the insert policy requires `author_user_id = auth.uid()`), and the API's rows have none, so a member's client row is that member's data, never a platform run.
- **[R2-QUOTA] The monthly quota counts rows clients cannot forge**: `public.runs` rows of the tenant with `author_user_id is null` created this month (`plans.enforce_at_enqueue`). Clients cannot create such rows, and the update/delete policies never match them (`author_user_id = auth.uid()`). This is equivalent to counting `public.jobs` (one job per API run, service-only since `20261031200100`) and keeps P3-05's boundary test, which seeds runs directly, unchanged.
- **[R2-STORAGE-SHIM] Shim grants as on Supabase**: `grant select, insert, update, delete on storage.objects to anon, authenticated, service_role` and `grant select on storage.buckets` (the shim enables no RLS on buckets, so no writes there). `storage.objects` joins the per-test truncation list in `ucgle_f1.db.pytest_plugin`.
- **[R2-FORGED-REPORT] Report, never delete.** `public.qcompass_forged_row_report()` (service-only: execute revoked from `public`, `anon`, `authenticated`) returns `(kind, ref, tenant_id, detail)` rows of three kinds: `job_tenant_differs_from_run` (jobs forged before `20261031200100`), `run_author_not_a_writer` (runs whose author is not owner/admin/member of `tenant_id`, including viewers' plants), and `storage_object_of_such_run`. `20261102100200` prints the count with a NOTICE when it is non-zero.
- **[R2-TOKEN-LOG] Redact at the store.** `ConversationStore.record_tool_call` stores `redact_secrets(request)` and `redact_secrets(response)`: the value of any key `token`, `approval_token` or `*_token` (any case, any depth) becomes `"[redacted]"`. One place covers `/v1/chat` and any future caller.
- **[R2-TOKEN-RACE] One conditional UPDATE spends a token**: `update agent_approval_tokens set consumed = true where "tokenId" = :t and tenant_id = :tenant and not consumed and "expiresAt" > now() and :scope = any(string_to_array(scopes, ',')) returning "tokenId"`. Concurrent spends on any number of instances serialise on the row lock, and the loser's re-checked WHERE fails. The per-process `RLock` no longer matters for tokens.
- **[R2-TOKEN-TTL] No wildcard; one hour at most.** Nothing issues `*` (grep of `src/`, `backend/`, `packages/`, `e2e/`, `acceptance/`: only the store's own comment mentioned it), so `*` is removed rather than bound to a principal. Scopes are the `ApprovalScope` literal in `memory/store.py` (`start_run`, `cancel_run`, `scan_parameters`, `save_plan`, `precision_override`); `get_capabilities().approvalScopesRequired` is built from the same tuple (R20). `POST /api/approvals` takes `scopes: list[ApprovalScope]` (at least one) and `ttl_seconds: int` in (0, 3600], default 3600; anything else is 422 (a huge TTL used to be a 500). `issue_approval` enforces the same rule with ValueError. Every token is one-shot. A legacy `*` row or a row with a null `expiresAt` approves nothing.
- **[R2-RUN-ID] Server ids, per-tenant aliases** (`20261102100300_qcompass_run_client_alias.sql`). `POST /api/qcompass/domains/{d}/runs` always generates `runs.id` (`qc_<domain>_<12 hex>`, retried on the unlikely primary-key collision). A body `runId` (same safe-component grammar, 400 otherwise) is stored in `runs.client_run_id`, unique on `(tenant_id, client_run_id) where client_run_id is not null and author_user_id is null`. A run route accepts the id or the caller's own alias (`get_run` with a tenant: `(id = :id or client_run_id = :id) and tenant_id = … and author_user_id is null order by (id = :id) desc limit 1`), and every later step uses the resolved `rec.id`. The only 409 is reusing one's own alias. This closes both the oracle and squatting, including squatting through a PostgREST insert of a personal run. `runs.id` stays the primary key, so `jobs`, `run_results`, `run_provenance`, `job_events` and storage paths are unchanged.
  - Wire and SDK in step: `SubmitRunResponse` gains `clientRunId` (nullable, documented), `runId` is documented as API-generated, `SubmitRunRequest.runId` in `packages/ts/qcompass-frontend-sdk/src/types.ts` is documented as an alias, and `scripts/gen_sdk_types.sh` regenerated `openapi.json`/`openapi.ts`. The frontend never sends `runId` and already uses the response's `runId`; `backend/tests/test_frontend_contract.py` passes unchanged.
- **[R2-PLAN-PATH]** `ConversationStore.save_plan` writes `<artifacts>/agent-sandbox/<tenant slug>/<conversation>/plans/<plan>.json` with `safe_component` on the tenant and the conversation id and `safe_join` under the root (as `qcompass_routes._tenant_root` does), and stores that path relative to the artifacts root. `research.save_plan` validates the conversation id before it spends the approval (INVALID_INPUT).
- **[R2-START-ORDER]** `start_run` checks the agent trace, then that `get_hypothesis(hypothesisId, tenant=…)` exists, then the config, and only then spends the token (as `cancel_run` already did). A foreign or unrecorded hypothesis is `AUDIT_VIOLATION` (409). `cancel_run`/`start_run` run the store calls with `asyncio.to_thread`.
- **[R2-CHAT-LOOP]** `/v1/chat` runs `_dispatch` and `record_tool_call` with `asyncio.to_thread` (which copies the request context), so no tool's database work or `cancel_run`'s own loop runs on the server's event loop. `_run_coroutine` is unchanged; its docstring records that callers on a loop must not call `_dispatch` there.

## Corrected tests (old → new)

- **[R2-H1-TESTS]** `backend/tests/test_security_gate1.py::test_h1_no_dev_tenant_fallback_outside_dev` (tightened).
  - Old: `from ucgle_f1.m8_agent.principal import TenantNotBound`; `with pytest.raises(TenantNotBound): RunRegistry().get("run_x")`; in dev, `RunRegistry().get("run_x") is None`. On `3d2355a` it failed at the import, before the fallback ran.
  - New: imports nothing the fix added. Outside dev: `asyncio.run(RunRegistry().submit(cfg))` raises a `RuntimeError` whose type name is `TenantNotBound`, and afterwards no `dev` tenant and no run exist; a run filed under the service's `dev` tenant is refused by `RunRegistry().get` the same way. In dev: the same `get` returns that run and `get("run_x") is None`. On `3d2355a` it fails with `DID NOT RAISE RuntimeError` (the dev fallback created and used the shared tenant).
- **[R2-H1-TESTS]** `…::test_h1_resolve_tenant_prefers_the_id_match_and_slug_guard_is_reversible` (tightened).
  - Old: `victim = ensure_tenant("victim")`; `rollback("20261031200000")`; insert the shadow after the victim; `resolve_tenant(victim) == (victim, "victim")` ×5; re-apply; constraint validated. On `3d2355a` it failed at `rollback` (FileNotFoundError). The shadow came second in heap order, so the old lookup may well have returned the right row anyway.
  - New: a context manager drops every CHECK constraint on `tenants` and restores each with its own `pg_get_constraintdef` (no migration file needed); the shadow (slug = a fresh UUID) is inserted before the victim with that id, then the same five assertions run. Then the guard's reversibility: validated → down drops it → up re-adds it validated. On `3d2355a` it fails on the first `resolve_tenant` (the shadow's id is returned).
  - The old shape also broke on this branch: after `rollback("20261031200000")` the new `tenants_slug_not_uuid_check` still refuses the UUID-shaped shadow.
- **[R2-RUN-ID]** `…::test_l2_run_id_collision_does_not_reveal_another_tenants_run`.
  - Old: globex submits `runId: qc_shared_id`; acme's submit with the same runId and globex's resubmit both 409 with identical bodies; the message has no "exist" and no id.
  - New: acme's submit is 202 with a different `runId` (its own alias); globex's resubmit is 409 `CONFLICT` with the same message checks; `GET …/runs/qc_shared_id` returns each tenant's own run. The old 409 for acme encoded the global namespace, which round 2 identified as the squatting bug (c4).
- **[R2-M1-USING]** `…::test_m1_runs_policy_migration_is_reversible`.
  - Old: asserted that the head policies contain `is_tenant_member`, rolled back `20261031200200` alone and re-applied it.
  - New: `20261102100200` now replaces these policies, so the head no longer contains that text, and re-applying `…200200` alone would leave its policies active while `…100200` stays recorded as applied. The test records the head policies, rolls back every later migration (newest first), then checks `…200200`'s own state, its down (main's policies) and the re-application of all of them, and finally that the head policies are identical to before.
- **[R2-START-ORDER] Setup only, no assertion changed.** These tests started runs that cite a hypothesis nobody recorded, which A6 now refuses. Each now records the hypothesis first with `ConversationStore.record_hypothesis` and cites its id:
  - `test_security_gate1.py::test_h1_post_api_runs_files_the_run_under_the_callers_tenant` (acme's hypothesis);
  - `test_security_gate1.py::test_sf4_agent_memory_is_tenant_scoped` (globex's own hypothesis for the stolen-token request, so it still reaches the token check and gets 403 `APPROVAL_REQUIRED`; acme's for the legitimate request);
  - `backend/tests/agent/test_approval_flow.py::test_full_agent_run_flow`;
  - `backend/audit/agent/test_a6_run_traceability.py::test_start_run_rejects_without_approval`.
- **[R2-START-ORDER]** `backend/audit/agent/test_a6_run_traceability.py::test_start_run_links_run_to_conversation`.
  - Old: cited the literal `hypothesisId="hyp_a6"`, never recorded, and asserted `link.hypothesisId == "hyp_a6"`.
  - New: records a hypothesis in the tenant and cites its generated id; asserts `link.hypothesisId == hyp` (the cited id), with the other assertions unchanged. The literal was an unrecorded hypothesis, which is exactly what A6 now refuses.
  - Added `test_start_run_rejects_a_hypothesis_the_tenant_never_recorded` (A6): `AUDIT_VIOLATION`, and the token is still unspent.
- **[R2-STORAGE-SHIM]** `backend/src/ucgle_f1/db/pytest_plugin.py`: `storage.objects` added to the per-test truncation list (harness, not a test).
- New tests: `backend/tests/test_security_gate1_round2.py` (19 functions, 26 cases).

## Removals with replacement

- **[R2-TOKEN-TTL]** Wildcard approval scope `*` (session-wide, never consumed) → named one-shot scopes only; nothing issued `*`.
- **[R2-TOKEN-TTL]** `IssueReq.ttl_seconds: int | None` (null produced a token that had already expired; any size accepted) → `int` in (0, 3600], default 3600.
- **[R2-RUN-ID]** Client-chosen `runs.id` on `POST /api/qcompass/domains/{d}/runs` → server-generated id plus `runs.client_run_id` (per-tenant alias, accepted by every run route).
- **[R2-RUN-ID]** The generic 409 for a runId held by another tenant (SEC-L2's round-1 fix) → no conflict across tenants; 409 only when the caller's own tenant reuses an alias.
- **[R2-QUOTA]** Quota over all `runs` rows of the tenant → over API-created rows only.
- **[R2-PLAN-PATH]** Absolute `agent_plans.path` → path relative to the artifacts root, under the tenant's sandbox.
- **[R2-M1-USING]** Policies replaced by `20261102100200` (its down migration restores them): runs "authenticated users create runs", "authors update own runs" (both from `20261031200200`), "authors delete own runs"; "authors write results" (`20261031200200`); "authors write audits"; "authors write timelines"; storage "authors write/update/delete viz-timelines", "authors write/delete run-artifacts" (main's `20260424153958`).

## BLOCKED-ON-JAMES

- **[all]** `BLOCKED-ON-JAMES:DATABASE_URL`: none of these migrations has been applied to a real project. Each was applied, rolled back and re-applied on the local Postgres 16 harness (`test_r2_migrations_are_reversible`).
- **[R2-DEV-SLUG][R2-SF4-BACKFILL]** If production has a user-owned tenant with slug `dev`: the API refuses to use it as its dev tenant (`BLOCKED-ON-JAMES:rename-user-owned-dev-tenant`), and `20261102100100` sets its legacy agent rows back to null (NOTICE with the count). James should rename that tenant. If `20261031200000` also reported it (constraint NOT VALID), validate `tenants_slug_reserved_check` after the rename.
- **[R2-UUID-SLUG]** If an existing slug casts to uuid, `tenants_slug_not_uuid_check` stays NOT VALID with a NOTICE; rename the tenant, then `alter table public.tenants validate constraint tenants_slug_not_uuid_check`.
- **[R2-FORGED-REPORT]** After the first deploy, James reviews `select * from public.qcompass_forged_row_report()` (service role). The migration NOTICE gives the count. Nothing is deleted automatically.

## Observations outside these findings (not changed)

- c1 residuals not assigned to this lane: runs filed under `dev` before SEC-H1 are not reassigned, and a tenant row left NOT VALID by `20261031200000` makes every later UPDATE of that row fail until its slug changes. A rename by James clears both.
- `AuthError("…", code="TENANT_RESERVED")` has no entry in `api_errors.HTTP_STATUS_FOR_CODE`, so a dev-mode request that reaches a user-owned `dev` answers 500 with the BLOCKED-ON-JAMES message. It only happens under `QCOMPASS_ENV=dev` on a database that needs James's rename.
