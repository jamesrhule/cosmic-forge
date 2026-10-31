# W1 platform lane notes (`build/w1-platform`)

## Decisions
- **P3-06 error envelope:** `{"detail": {"code", "message", "errors"?}}`. The `ServiceError` `{code, message}` shape sits under FastAPI's `detail` key. That keeps the A8 assertions (`resp.json()["detail"]["code"]`) and FastAPI conventions, and gives one shape for every error (R20).
- **P3-06 `QCOMPASS_ENV`:** defaults to `production`, so an unset environment never relaxes CORS (or, in P3-04, auth).
- **P3-06 readiness:** each store (`ConversationStore`, `AuthStore`, `ScanRegistry`, `RunRegistry`) gains `ping()`. The probe is written against that interface so it survives the P3-01 move to Postgres and the P3-02 queue.

- **P4-01 verdict auth:** correction 9 needs a verified Supabase admin. JWT verification lives in `m8_agent/supabase_auth.py` as the shared module P3-04 builds on, not a one-off. Roles are read through PostgREST with the caller's token, so RLS decides; the service-role key is never used. Only asymmetric algorithms are accepted (ES256/RS256).
- **P4-01 run shape:** `GET …/runs/{id}` returns `qcompass_core.wire.DomainRunResult`, the frontend's type, built from the provenance sidecar (manifest plus terminal status in `payload`). P3-03 replaces the sidecar source with the persisted `RunResult`. An empty `classical_reference_hash` is returned as recorded (`""`), not dropped.
- **P4-01 domain ids:** paths accept full `DomainId`s and short names; responses use the full id.
- **P4-01 literature:** the backend serves its own copy (`m8_agent/data/literature/`); the frontend keeps its fixtures for offline mode, and `test_frontend_contract.py` asserts the two are identical.
- **Local lint hygiene:** `**/.venv` added to the eslint and prettier ignores. A root uv environment held 35k vendored JS files that eslint walked.

- **P3-04 principal model:** one `require_scope` dependency covers HTTP and WebSocket and accepts either credential type. A Supabase user with a non-member tenant, and any cross-tenant resource, gets 404 so tenant and resource existence don't leak; a key pointed at another tenant via the header keeps the existing 403 `TENANT_MISMATCH` (A8). Legacy `/api/runs` (start, get, audit, stream), `/api/approvals`, `/api/models` and `/mcp/tools` now require a principal: they start compute or mutate state, and a public SaaS can't leave them open. `/api/benchmarks` stays public, as A8 pins.
- **P3-04 storage:** implemented on the current SQLite stores' interfaces (`api_keys`, `tenant_members`, scans `tenant_id`). P3-01 ports these tables to Postgres with RLS.

## Substitutions
- None yet.

## Corrected tests (old → new)
- `backend/audit/agent/test_a7_qcompass_routes.py::test_get_run_returns_sidecar_payload` (A7 is editable under R4, correction 2). The route's contract changed in P4-01 from the raw sidecar to the frontend's `DomainRunResult`.
  - Old: `assert body["runId"] == run_id` and `assert body["domain"] == "cosmology"`.
  - New: `assert body["id"] == run_id`, `assert body["domain"] == "cosmology.ucglef1"` and `assert "classical_reference_hash" in body["provenance"]`, plus a GET by the full domain id returning the identical body.
  - Same intent (the stored run comes back for its id and domain); strictly more assertions.
- `backend/tests/test_lovable_contract.py::test_verdict_sample_yaml_round_trips_when_present`: the data path moved (correction 9). Old `VERDICT_DIR = _FIXTURES_ROOT / "verdict"` with `"sample-verdict.yaml"`; new `backend/src/ucgle_f1/m8_agent/data/verdicts` with `"sample.yaml"`. Assertions unchanged.

- **P3-04 fixtures** (no assertion changed): `QCOMPASS_DEV_ALLOW_ANONYMOUS=1` alone no longer enables anonymous access; it also needs `QCOMPASS_ENV=dev`.
  - `QCOMPASS_ENV=dev` is now set next to the existing flag in `audit/agent/test_a7_qcompass_routes.py`, `audit/agent/test_a9_observability.py` and `tests/test_path_guards.py`.
  - `tests/agent/test_server_routes.py` gains an autouse fixture setting both, because its routes now require a principal.
  - `tests/test_api_hardening.py` (P3-06, this lane) sends a real tenant API key, so it still exercises production CORS defaults.

## Removals with replacement
- `CORSMiddleware(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])` → env allowlist with explicit methods and headers.
- `server._status` table, `mcp_server._status_for` table, `qcompass_routes._AUTH_CODE_TO_HTTP` → `api_errors.HTTP_STATUS_FOR_CODE`. The two function names remain as thin delegates.

- `public/fixtures/verdict/sample-verdict.yaml` → `backend/src/ucgle_f1/m8_agent/data/verdicts/sample.yaml`; `sample-verdict.md` → `…/verdicts/sample.md`; `sample-verdict.yaml.json` → removed, replaced by `GET /api/verdict/{id}` (correction 9).
- `src/services/qcompass/verdict.ts` static-fixture read → authenticated API fetch.
- `qcompass_routes._qcompass_auth` / `_maybe_auth_dependency` / `_allow_dev_anonymous` and `server._chat_auth` → `principal.require_scope` / `principal.dev_anonymous_allowed` (one auth path, R20).
- API-key storage `tokens.token_id` (plaintext) → `api_keys.key_hash` (SHA-256). The old table is kept, deprecated and unused, so keys issued before P3-04 must be reissued.

## Behaviour fixes
- `admin.verdict.tsx`: a failed verdict fetch now shows an error instead of an endless "Loading…".
- `POST /api/approvals` `scopes`: comma string → list, matching its documented contract.

## BLOCKED-ON-JAMES
- None yet.


## P3-01 (Postgres) — new section

### Decisions
- **[P3-01] Build on main's tenancy schema.** `api_keys`, `scans` and `tenant_budgets` reference `public.tenants`; membership uses `public.tenant_members` (role enum `owner/admin/member/viewer`; `owner` gets admin scopes and is reported as `admin` by `/api/qcompass/tenants`). The external tenant id (header, `Token.tenant_id`, artifact paths) is the tenant **slug**; a UUID is accepted too. P3-04's `extra_scopes` on members is dropped, since main's `tenant_members` has no scopes column; roles alone decide scopes.
- **[P3-01] Local and CI Postgres harness with a Supabase-compat shim** (`ucgle_f1/db/supabase_shim.sql`): applied only where no `auth` schema exists. `pg_cron`'s `create extension` becomes a no-op where it isn't installable. Real Supabase projects are never shimmed.
- **[P3-01] Test safety:** tests never use a pre-existing `DATABASE_URL`; only `TEST_DATABASE_URL` or a cluster they start themselves (R13).
- **[P3-01] Down migrations deprecate, never drop:** tables and their indexes are renamed `_deprecated_*_<version>` (R13).
- **[P3-01] Migration tracking** uses the Supabase CLI's `supabase_migrations.schema_migrations`, so `supabase db push` and the runner agree.
- **[P3-01] New dependency:** `psycopg[binary]>=3.2` (LGPL-3.0, weak copyleft, R11; licence gate 0 violations).

### Corrected tests (old → new)
- **[P3-01]** `audit/agent/test_a8_auth_tenancy.py::test_api_keys_are_stored_only_as_hashes`. Old: dumped the SQLite file `tmp_path/auth.db` and asserted the key was absent. After the move that file no longer existed, so the test would have passed vacuously. New: reads `public.api_keys` in Postgres, asserts rows exist, the plaintext is absent and the SHA-256 hash is present. Strictly stronger.
- **[P3-01]** `…::test_supabase_users_resolve_tenants_through_membership` and `…::test_ws_rejects_supabase_non_member`. Old: user ids `"user-1"`/`"user-2"`. New: real `auth.users` rows (UUIDs), as Supabase issues; `tenant_members.user_id` is a UUID foreign key.
  - Old: `assert tenants == [acme viewer, initech admin]`.
  - New: the same two entries asserted exactly, plus main's `handle_new_user_tenant` trigger's personal tenant (owner → reported `admin`), with exactly 3 tenants.

### Removals with replacement
- **[P3-01]** SQLite files `${UCGLE_F1_STATE_DIR}/auth.db`, `scans.sqlite` and `agent.db` → Postgres tables in `supabase/migrations/20261031160000_*`. SQLite data is not migrated (dev-only state).
- **[P3-01]** `ConversationStore(db_path=…)` and `SQLModel.metadata.create_all` → the shared engine; the schema comes from migrations.

### BLOCKED-ON-JAMES
- **[P3-01]** `DATABASE_URL` (the Supabase Postgres connection string) for staging and production. Missing → 503 `BLOCKED-ON-JAMES:DATABASE_URL`; `/readyz` reports not ready.

## P3-01 part 2 (library-package stores) — new entries

### Decisions
- **[P3-01] Package stores take an injected SQLAlchemy `Engine`.** Packages can't import `ucgle_f1` (boundary guard), so `qcompass_core.db.engine_from_env()` resolves `DATABASE_URL` with the same rules as `ucgle_f1.db.engine` (psycopg 3 URL rewrite, `BLOCKED-ON-JAMES:DATABASE_URL` when missing, no fallback). The two are kept in step by hand; the backend cannot depend on `qcompass-core` (it is an optional extra), so one shared module is not possible without moving the backend's engine. The API and worker always inject their own engine.
- **[P3-01] Pricing cache and free-tier ledger keep their offline modes for the standalone library.** They were never SQLite (JSON files, in memory). With an engine they are Postgres (`router_pricing_cache`, `router_free_tier_ledger`); without one, `pip install qcompass-router` still works offline. Calibration and the leaderboard have no non-DB mode any more (their SQLite files are gone).
- **[P3-01] Free-tier ledger accounts:** `house` (PHC's provider accounts, service-only) or `tenant:<uuid>` (a tenant's own account, tenant RLS). `consume` is an atomic SQL decrement so two workers can't double-spend a tier.
- **[P3-01] Bench leaderboard is publicly readable** (RLS `anon` select), since P2-14 publishes it on a public page; only the service role writes.
- **[P3-01] One test database per process:** `ucgle_f1.db.pytest_plugin.scratch_database()` is shared by the backend's autouse fixtures and `packages/conftest.py`'s `pg_engine`, so a combined run starts one cluster.

### Corrected tests (old → new), fixtures only; no assertion changed
- **[P3-01]** Router calibration fixtures and tests (`tests/audit/conftest.py`, `src/qcompass_router/audit/conftest.py`, 5 tests in `tests/test_prompt6_v2.py`, 6 in `tests/test_p002_unification.py`): old `CalibrationCache(db_path=tmp_path / "….sqlite")`; new `CalibrationCache(pg_engine)` (per-test truncated Postgres). Assertions unchanged.
- **[P3-01]** `packages/qcompass-bench/tests/test_runner.py::isolated_store`: old `LeaderboardStore(db_path=tmp_path / "leaderboard.sqlite")` plus `QCOMPASS_BENCH_DB`; new `LeaderboardStore(pg_engine)`. Assertions unchanged.

### Removals with replacement
- **[P3-01]** `~/.cache/qcompass/calibration.sqlite` and `QCOMPASS_CALIBRATION_DB` → `public.router_calibration_daily` / `public.router_calibration_devices`.
- **[P3-01]** `~/.qcompass/bench/leaderboard.sqlite` and `QCOMPASS_BENCH_DB` → `public.bench_runs`.
- **[P3-01]** `CalibrationCache(db_path=…)` / `LeaderboardStore(db_path=…)` → `(engine=…)`.
- **[P3-01]** Dependency `sqlite-utils` (declared, never imported) → `sqlalchemy` + `psycopg[binary]`.

### BLOCKED-ON-JAMES
- **[P3-01]** None new (`DATABASE_URL` for staging and production, already listed, also covers the package stores).

## P3-02 / P3-03 (worker queue, persisted results) — new entries

### Decisions
- **[P3-02] Service role per transaction.** `claim_next_job`/`complete_job` (main) and the new `heartbeat_job`/`reap_expired_jobs` check `auth.role() = 'service_role'`. The API and worker connect with the privileged `DATABASE_URL` and set `request.jwt.claims = {"role":"service_role"}` locally in each queue transaction, as PostgREST does for the service key.
- **[P3-02] `complete_job` is redefined** (create or replace) to touch only `running` jobs and to clear `locked_until`; the down migration restores main's body. Without this a stale worker could mark a cancelled or dead-lettered job `succeeded`.
- **[P3-02] Retries are for lost leases only.** A handler exception fails the job at once (deterministic input errors don't improve on retry); a worker that dies loses its lease and the janitor requeues until `max_attempts`, then dead-letters with a `system_incidents` row.
- **[P3-02] Events in Postgres, polled.** Workers write `public.job_events`; streams poll every 0.2 s. No LISTEN/NOTIFY and no broker (R20; Part 4 forbids Redis etc.). The `result` event is a marker; the stream hydrates the body from `run_results`.
- **[P3-02] Job kinds without compute yet** (`scan`, `viz.bake`, `qpu.submit`, `qpu.poll`, `patch.dryrun`) are accepted by the queue and fail with the owning ticket's id (P4-07, P4-04, P2-01, P3-08/P5-05). Nothing is faked (R7).
- **[P3-02] Worker package:** `workers/qcompass_worker` is a uv workspace member (`qcompass-worker`, depends on `ucgle_f1[qcompass]` and the `qcompass` meta-package). It inherits the `ucgle-f1` vs `qcompass-router[braket]` conflict, now declared for it too (correction 3: P2-01 builds the qpu image without Hydra).
- **[P3-02] Submit validates the envelope only** (`Manifest.model_validate`, 422 `INVALID_INPUT`); domain validation (`prepare`) runs in the worker. A duplicate client-supplied `runId` is 409 `CONFLICT`. A run without a bound tenant (in-process MCP tool use) is recorded under the dev tenant slug `dev`.
- **[P3-02] `RunPipeline.run(cfg, on_module=None)`**: optional callback after each module's existing timing line. Physics unchanged; the physics lane owns the rest of `pipeline.py`.
- **[P3-03] Non-finite floats** are stored as `"NaN"`/`"Infinity"` strings (jsonb has none); pydantic reads them back as floats.
- **[P3-03] Artefacts:** `run-artifacts/<run_id>/provenance.json` via the Storage REST API with `SUPABASE_SERVICE_ROLE_KEY`; missing key → the row records `BLOCKED-ON-JAMES:SUPABASE_SERVICE_ROLE_KEY`.

### Corrected tests (old → new), fixtures only; no assertion changed
- **[P3-02]** `backend/tests/agent/test_approval_flow.py::test_full_agent_run_flow` and `backend/audit/agent/test_a7_qcompass_routes.py::test_sse_stream_replays_history_then_status` gain the `inprocess_worker` fixture (a real `Worker.run_forever` on a thread with its own engine). Before P3-02 the API computed the run itself; now a worker must, or the stream would never end. Assertions unchanged.

### Removals with replacement
- **[P3-02]** `RunRegistry._drive` (in-process pipeline with pre-emitted progress) and its in-memory `_runs`/listeners → `ucgle_f1.jobs.JobQueue` + `ucgle_f1.worker` (`ucgle_f1.run` handler) + `job_events` streaming. `RunRegistry`'s public methods (`submit/get/result/cancel/stream/ping`) are kept.
- **[P3-02]** Synchronous `prepare/run` inside `submit_run` → `qcompass.run` handler in the worker; response 200/202 with the computed status → always 202 `queued`.
- **[P3-03]** Sidecar-file reads in `list_runs`/`get_run`/`stream_run` → `public.runs`, `public.run_results`, `public.run_provenance`, `public.job_events`. The sidecar is still written at submit.
- **[P3-02]** `runs._validation_benchmarks_for` → `validation_benchmarks_for` (old name kept as an alias).

### BLOCKED-ON-JAMES
- **[P3-03]** `SUPABASE_SERVICE_ROLE_KEY` (with `SUPABASE_URL`) for artefact uploads to `run-artifacts` in staging/production. Until then provenance rows record the block; no data is lost.

## P3-05 (plan limits and budgets) — new entries

### Decisions
- **[P3-05] One limits table, checked for drift.** `ucgle_f1.plans.PLAN_LIMITS` copies `src/lib/billing.ts`; a backend test parses the TS file and fails on any difference. A generated shared file would need the backend image to read the frontend tree; the drift test keeps one source of truth (the pricing page) without that.
- **[P3-05] Limits are checked inside the enqueue transaction** with the tenant row locked, so two concurrent submits can't both pass.
- **[P3-05] "Concurrent jobs" = queued + running jobs** of the tenant. "Runs per month" = `public.runs` rows created since the first of the UTC month.
- **[P3-05] Codes:** `PLAN_RUNS_PER_MONTH_EXCEEDED`, `PLAN_CONCURRENT_JOBS_EXCEEDED` (429); `PLAN_GPU_REQUIRED`, `PLAN_TIMELINE_BYTES_EXCEEDED`, `BUDGET_EXCEEDED` (402). Added to both `ServiceErrorCode` literals (Python and TS) and `api_errors.HTTP_STATUS_FOR_CODE` (plus `CONFLICT: 409` for duplicate run ids).
- **[P3-05] Budget hook in both processes:** the old inline hook registration in the API lifespan became `auth.install_budget_hook()`, also called by the worker, which binds each job's tenant while it runs.

### Behaviour fixes
- **[P3-05]** `src/services/qcompass/runs.ts::startRun` swallowed every API error and returned a fixture run id; a plan-limit or budget refusal now propagates. `src/services/qcompass/http.ts::apiFetch` threw a bare `Error`; it now throws the same `ServiceError` as `src/lib/apiClient.ts`.

### Corrected tests
- **[P3-05]** None. The new `tests/test_worker_queue.py` `api` fixture puts its tenant on `enterprise`, since it submits up to 50 concurrent runs.

## P4-02 (generated SDK, live services) — new entries

### Decisions
- **[P4-02] Generator:** `openapi-typescript` 7.13.0 (MIT, exact pin in `package.json`/`bun.lock`; the tool PLAN Part 4 names). `scripts/dump_openapi.py` writes `build_app().openapi()` with sorted keys (deterministic; env-independent, tested); `scripts/gen_sdk_types.sh` writes `packages/ts/qcompass-frontend-sdk/{openapi.json,src/generated/openapi.ts}` and `--check` fails CI (backend job) when either is stale. Both generated files are excluded from prettier/eslint so CI compares bytes.
- **[P4-02] `--default-non-nullable false`:** a defaulted property is not required. FastAPI request bodies may omit defaulted fields (`ChatRequest.provider`), and the API's `required` lists say what it requires.
- **[P4-02] Hand-written SDK types only where OpenAPI has no schema:** free-form request bodies (`POST …/runs` and `POST …/scans` take `dict`; the manifest problem is per-domain), SSE event payloads, and visualization frames (the API types frames as JSON objects). Every response type is an alias of a generated schema.
- **[P4-02] One data source per build:** `DATA_SOURCE = "api"` when `VITE_API_URL` is set, else `"fixtures"` (`src/config/features.ts`). In API mode services call the SDK through `src/lib/sdk.ts` and never fall back to a fixture after an error; errors reach the UI as `ServiceError` (P3-05/P3-06 envelope, unchanged shape). `loadFixture`/`loadJsonlFixture` refuse data fixtures in API mode (client and SSR, `src/lib/fixtureGuard.ts`); the only allowed path is the static F1–F7 formula reference (`formulas/`).
- **[P4-02] One HTTP client (R20):** `src/services/qcompass/http.ts`'s own `fetch` and `src/lib/apiClient.ts`'s own `fetch`/SSE parser are replaced by the SDK client; `apiFetch`/`apiSse` remain as the untyped escape hatch for routes outside the OpenAPI document (cosmic_forge_viz manifest/timeline), on the same client, headers and error mapping.
- **[P4-02] SDK SSE over `fetch`:** `EventSource` can't send `Authorization` and only delivers unnamed events; the API sends named events (`status`, `progress`, `end`). `parseSse` follows the event-stream rules (tested).
- **[P4-02] Workbench cosmology runs go through the platform route** `POST /api/qcompass/domains/cosmology.ucglef1/runs` (validate, enqueue, 202), not the agent route `POST /api/runs`, which requires an approval token and the A6 agent ids. The Configurator follows the run's SSE stream and shows its status and the engine's η_B (`data-testid="workbench-run-status"`); the domain run page follows a queued/running run until it ends (`data-testid="run-status"`). Neither appears before a run is started, so the R19 screenshots are unaffected.
- **[P4-02] Per-environment flags:** `deploy/web/{staging,production}.env` (public `VITE_*` flags), `VITE_API_URL` from each environment's Cloud Run API URL (P3-07).
- **[P4-02] Live e2e:** separate Playwright config `playwright.live.config.ts` (testDir `e2e/live`, ignored by the main config) and CI job `e2e-live` with a `postgres:16.4` service. `scripts/live_stack.py` starts uvicorn + `python -m qcompass_worker` on the backend's test harness database (`TEST_DATABASE_URL` or a throwaway cluster), with `QCOMPASS_ENV=dev` + `QCOMPASS_DEV_ALLOW_ANONYMOUS=1` (test-only; P3-07's `test_deploy_config.py` proves no image/deploy file sets them). Cosmology uses the V2 defaults at precision `fast` (the smallest real config the pipeline supports; ~12 s), chemistry H2/STO-3G classical FCI.
- **[P4-02] Contract mismatches the generated types exposed, fixed:** `assistant.sendMessage` sent `conversation_id`/`model_id` (the API's `ChatRequest` is camelCase → 422); `qcompass/scans` expected an array from `GET /api/qcompass/scans` (the API returns `{scans: ScanEnvelope[]}`); `startScan` posted no `kind` (422). The HEP visualizer panel's literature compare read `/fixtures/literature/…` directly with the wrong shape; it now uses the literature service (API in live mode).

### Behaviour fixes
- **[P4-02] Worker could not run cosmology through the qcompass route:** jobs carry the short domain (`cosmology`) but the plugin registers as `cosmology.ucglef1`, so every such run failed ("No qcompass.domains plugin named 'cosmology'"). `ucgle_f1.worker.resolve_simulation` maps short names to plugin names; the schema route uses it too (it served a generic `{"type": "object"}` for cosmology). Tested in `backend/tests/test_sdk_contract.py`.
- **[P4-02]** Services no longer swallow API errors and return fixtures (`qcompass/runs`, `auth`, `manifestSchema`, `scans`, `visualizer`, `simulator`, `assistant`, `artifacts`).

### Corrected tests (old → new)
- **[P4-02]** None. No existing test was changed. New: `backend/tests/test_sdk_contract.py` (4), `src/lib/__tests__/sdkClient.test.ts` (3), `src/lib/__tests__/dataSource.test.ts` (4), `e2e/live/workbench-live.spec.ts` (3). New `@endpoint` annotations (simulator, assistant) add parametrized cases to `test_frontend_contract.py`.

### Removals with replacement
- **[P4-02]** `src/services/qcompass/http.ts` (own `fetch` wrapper) → `src/lib/sdk.ts` (`api`, `apiStream`, `usesApi`, `authHeaders`) over `@qcompass/frontend-sdk`.
- **[P4-02]** `src/lib/apiClient.ts` `fetch`/SSE implementation → the SDK client (`apiFetch`/`apiSse` keep their signatures); `errorFromResponse` moved to `src/lib/apiErrors.ts` and is re-exported from `apiClient`.
- **[P4-02]** SDK hand-aligned mirror types (`types.ts`) and the `datamodel-codegen` script (never run; it targeted Python models, not the API) → aliases of generated OpenAPI schemas; `ProvenanceSidecar`-returning `getRun` → `DomainRunResult` (what the API returns since P4-01).
- **[P4-02]** `ParticleObservablesTable` `literatureUrl` prop (direct `/fixtures/` fetch) → `getLatticeQCDReferences()`; `particle-suite.tsx` direct `loadFixture` → `services/qcompass/bench.ts::getParticleSuite` (fixture mode unchanged; API mode reports that the leaderboard arrives with P2-14).

### Gaps (owned elsewhere)
- **[P4-02]** API mode has no source yet for: the cosmology six-panel timelines (`services/visualizer.ts`; P4-04 real-run timelines), the bench particle-suite leaderboard (P2-14), run artefact listing/download (`/api/runs/{id}/artifacts` does not exist; artefacts are in `run-artifacts` storage, P4-04/P4-06). In API mode these views report the missing source instead of showing fixtures. The domain visualization endpoint still bakes synthetic frames (P4-04 removes `bake_synthetic`). Scans as jobs: P4-07.

### BLOCKED-ON-JAMES
- **[P4-02]** None new.

## P3-07 (containers and deploy-as-code) — new entries

### Decisions
- **[P3-07] One Python environment, two targets per Dockerfile** (`--target api` → `qcompass-api`, `--target worker` → `qcompass-worker`; PLAN Part 4 "one worker image, class by `--classes`"). The last stage stays `api`, so release-please's untargeted `qcompass-runtime:{cpu,cuda12}` builds keep serving the API.
- **[P3-07] Pins:** CPU base `python:3.12.15-slim-bookworm@sha256:6a0e06f5…` (3.12.16 was published 2026-10-28, under two weeks old); uv `astral/uv:0.11.32@sha256:df4cae8f…` (Docker Hub copy of the official image; same uv as CI); CUDA base `nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04@sha256:8aef630a…`. Dependencies: `uv sync --frozen --no-dev --all-packages --extra qcompass --extra viz` from `uv.lock`.
- **[P3-07] CUDA image Python 3.12.13** (uv-managed python-build-standalone): the Debian-built 3.12.15 can't run on Ubuntu's older glibc, and 3.12.13 is the newest 3.12 the pinned uv can install. `jax-cuda12-plugin[with-cuda]==0.12.0.1` (the locked jax version) is added on top of the lock because it is CUDA-only.
- **[P3-07] No system packages:** every locked dependency ships a manylinux or pure-Python wheel (the one sdist, `antlr4-python3-runtime` 4.9.2, is pure Python) and no installed shared object needs the system `libgomp`, so the old `apt-get` compiler/BLAS layers are gone.
- **[P3-07] Worker `/healthz`:** `ucgle_f1.worker.serve_health` serves `GET /healthz` on `$PORT` (or `--health-port`): 200 while the loop turns or a job runs, 503 when stalled or stopping; it never touches the database. Cloud Run services need a listening port, and the HEALTHCHECK needs the same probe.
- **[P3-07] Cloud Run services** (`deploy/*.yaml`, Knative v1, `gcloud run services replace` after `envsubst`): secrets only as Secret Manager references (`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`); workers `minScale 1` (cpu) with CPU always allocated and internal ingress; GPU worker on `nvidia-l4`, `minScale ${GPU_MIN_INSTANCES}` (default 0, so no idle GPU cost until James raises it); runtime account = `GCP_SERVICE_ACCOUNT` (the only account name in Part 6).
- **[P3-07] Deploy workflow:** staging on push to `main`, production on `qcompass-v*` tags and from `release-please.yml` (tags pushed with `GITHUB_TOKEN` don't start other workflows), or by hand. Jobs use GitHub environments `staging`/`production`, check secrets first, and on a miss write `BLOCKED-ON-JAMES:<names>` to the summary and succeed. It also checks (never creates) the Artifact Registry repo and the Secret Manager entries. The web job never deploys without an API URL (a build without `VITE_API_URL` serves fixtures). Third-party actions pinned by SHA: `google-github-actions/auth@7c6bc770…` (v3.0.0), `setup-gcloud@aa5489c8…` (v3.0.1).
- **[P3-07] CI `images` job:** lints both Dockerfiles (`docker build --check`), builds the two CPU images, runs `scripts/container_smoke.sh` against a `postgres:16.4` service: non-root, Python 3.12, `/healthz` HEALTHCHECK, migrations from the API image, `/healthz` + `/readyz` 200, anonymous 401 (production config), worker `/healthz` + "serving cpu", then a real H2 job submitted with an API key through the API container and computed by the worker container. The CUDA image is linted only (size); the deploy workflow builds it.

### Corrected tests (old → new)
- **[P3-07]** None. New: `backend/tests/test_deploy_config.py` (14 cases).

### Removals with replacement
- **[P3-07]** Dockerfile `pip install -e` of each member (unpinned transitive deps, root user, compilers in the runtime image) → `uv sync --frozen` in a build stage, slim non-root runtime stage. `ENV` `UCGLE_F1_STATE_DIR`/`UCGLE_F1_ARTIFACTS`/`QCOMPASS_PRICING_CACHE` kept. Port 8787 → `$PORT` (default 8080, Cloud Run's).
- **[P3-07]** CUDA base `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04` with apt `python3.12` (not in Ubuntu 22.04's archive, so that build could not succeed) and unpinned `jax[cuda12]>=0.4.30` → CUDA 12.6.3/Ubuntu 24.04 by digest, uv-managed CPython, locked jax + matching CUDA plugin.

### BLOCKED-ON-JAMES
- **[P3-07]** GitHub environment secrets `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT` (staging, production) → Cloud Run deploys.
- **[P3-07]** `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` (staging, production) → Worker deploys.
- **[P3-07]** In each GCP project: Artifact Registry Docker repo `qcompass`; Secret Manager `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`; IAM for the service account; L4 quota.
- **[P3-07]** `QCOMPASS_CORS_ORIGINS` per environment (the workbench origin), and environment variables `VITE_SUPABASE_URL`/`VITE_SUPABASE_PUBLISHABLE_KEY`/`VITE_SUPABASE_PROJECT_ID`.
