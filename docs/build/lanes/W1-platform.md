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

## Gate 1 security fixes (R16 review of Wave 1) — new section

Evidence: `docs/build/evidence/W1-security-fixes.md`. Regression tests: `backend/tests/test_security_gate1.py` (27 cases), plus the deploy and hardening tests named below. Every finding was reproduced on `3d2355a` before it was fixed; none was a false positive.

### Decisions
- **[SEC-H1] Tenant passed explicitly, ambient binding kept as defence in depth.** `RunRegistry.submit/get/result/cancel/stream`, the simulator and research tools and `mcp_server._dispatch` take `tenant=`; `/api/runs*`, `/mcp/tools/{name}` and `/v1/chat` pass `principal.tenant_id`. `require_scope`'s dependency is now `async` (it runs `authenticate` with `asyncio.to_thread`), so `set_active_tenant` lands in the request's own context and reaches sync endpoints; the old sync dependency set it in a threadpool copy that was then discarded. The budget hook reads that binding.
- **[SEC-H1] No default tenant outside dev.** `principal.resolve_tenant_slug(None)` returns the bound tenant, else `dev` only under `QCOMPASS_ENV=dev`, else raises `TenantNotBound` (a 500: it marks a programming error, so it fails closed). This replaces the P3-02 decision "a run without a bound tenant is recorded under the dev tenant".
- **[SEC-H1] Slug guard** (`20261031200000_qcompass_tenant_slug_guard.sql`): CHECK `tenants_slug_reserved_check` refuses a slug shaped like any UUID form Postgres casts (hyphens and braces optional, any case), and refuses `dev` unless `created_by is null`. Only the service creates tenants without `created_by` (users' inserts must set it to `auth.uid()` under main's RLS), so the API's own dev tenant still works while no user can create or rename a tenant to `dev`. The constraint is added `NOT VALID` and validated only when no existing row violates it. Otherwise a NOTICE is raised and no rows are rewritten (R13). Local and test databases validated it.
- **[SEC-H1] `AuthStore.resolve_tenant`** orders an id match first (`order by (id = cast(:t as uuid)) desc limit 1`), so a slug that predates the guard can never shadow a tenant id.
- **[SEC-H2] Service-role-only enqueue** (`20261031200100_qcompass_jobs_service_enqueue.sql`): main's "tenant members enqueue jobs" is dropped and replaced by "service role enqueues jobs" (`to service_role`). No SECURITY DEFINER RPC: the only client insert was `src/lib/jobs.ts::enqueueJob`, which nothing imports and whose kinds (`run.simulate`, `run.audit`) no worker handles. Clients enqueue through the API, which checks scopes and plan limits.
- **[SEC-H2] Worker ownership check:** before running a job with a `run_id`, the worker reads `runs.tenant_id` and fails the job with `JOB_TENANT_MISMATCH` (or `JOB_RUN_MISSING`) unless it equals `job.tenant_id`. The run, its events, result and artefacts are not touched, and the handler never runs.
- **[SEC-H2] Tenant-filtered reads:** `JobQueue.result/result_text/provenance/events` take `tenant_uuid`. `RunRegistry` and every qcompass run route pass the run's own tenant, so `job_events`/`run_results`/`run_provenance` rows written under another tenant are never served.
- **[SEC-M1] Run writes stay in the writer's tenants** (`20261031200200_qcompass_runs_tenant_write_check.sql`): "authenticated users create runs", "authors update own runs" and "authors write results" add `tenant_id is null or public.is_tenant_member(tenant_id, auth.uid())` to with-check. `tenant_id is null` keeps the frontend's personal-run persistence (`src/lib/persistence.ts`) working.
- **[SEC-M2] Deploy workflow:**
  - Every action in `deploy.yml` is pinned to a full commit SHA with a `# vX` comment: `actions/checkout@11d5960a…` v4.4.0, `oven-sh/setup-bun@0c5077e5…` v2.2.0 (tags resolved with `git ls-remote`; both are lightweight tags), plus the existing google-github-actions pins. Checkout uses `persist-credentials: false`.
  - The Cloudflare token and account id are no longer job-level env. Only the wrangler step receives them; the check step sees booleans (`secrets.X != ''`).
  - The build is secret-less: `bun install --frozen-lockfile --ignore-scripts`. It was verified locally that the build and `wrangler deploy --dry-run` work that way, so no separate build job is needed.
  - The deploy runs the locked `./node_modules/.bin/wrangler` (4.82.2, `bun.lock`). `bunx wrangler` would download an unpinned copy when none is installed.
  - release-please's `deploy-production` job only calls `./.github/workflows/deploy.yml`, a local path that cannot carry a SHA. It now inherits these pins.
- **[SEC-L1] `/readyz`:** a failed check reports `ok: false` with detail `unavailable`, or a bare `BLOCKED-ON-JAMES:<NAME>` marker (a variable name, never a value), and the exception goes to the log.
- **[SEC-L2] Colliding `runId`:** the least invasive option is a generic 409 `CONFLICT` "runId is not available; choose another runId or omit it". It is identical whether the id belongs to the caller or to another tenant, and never says "exists". Per-tenant id namespaces would change `runs.id` (the primary key that `jobs`, `run_results` and `run_provenance` reference, and that main's storage policy reads), which is far more invasive. Residual: a client still learns that an id it guessed is taken somewhere. Generated ids carry 48 random bits.
- **[SEC-L3] Wall-clock limit:** each handler runs on its own thread, and the loop waits at most `job_timeout_seconds` (`--job-timeout-seconds` / `QCOMPASS_JOB_TIMEOUT_SECONDS`, default 3600 s, the API's Cloud Run timeout; non-positive or invalid values fall back to the default). On expiry:
  - the job fails with `JOB_TIMEOUT: …` and the run is marked failed;
  - the heartbeat stops renewing the lease;
  - the handler's later queue writes raise `JobCancelled` (`_GuardedQueue`).

  Python cannot kill a thread, so the worker's `/healthz` reports 503 while an abandoned handler is still alive, and Cloud Run replaces the container.
- **[SEC-L3] Custom potentials:** `m2_scalar/potentials.py` lives in `backend/src`, not under `backend/audit/physics`, so it may be edited. `_custom_expr` now caps:
  - source length 4096 and AST size 512 nodes;
  - numeric literals at |x| ≤ 1e30, real numbers only (strings, complex and booleans refused);
  - constant exponents at |e| ≤ 64;
  - every constant subexpression at 1000 digits, estimated from the AST without evaluating it.

  `phi**(9**9**9)`, `9**(64*64*64*64)` and `((9**64)**64)**64` are refused in milliseconds; real potentials are unchanged (`tests/unit/test_m2*` pass).
- **[SEC-L4] Visualization:** HTTP and WS look the run up in the caller's tenant (`_stored_run`) before baking: 404 or close 1008 otherwise, and nothing is written. `provenanceSidecar` is now a logical reference relative to the artifacts root (`qcompass/<tenant>/<domain>/<runId>.provenance.json`). The SDK was regenerated: only the field's description changed, and the frontend reads nothing from it.
- **[SEC-L5]** `deploy/qcompass-api.yaml` no longer mounts `SUPABASE_SERVICE_ROLE_KEY`. Grep: only `ucgle_f1/artifacts.py` reads it, called only from `worker._record_provenance`; the API verifies users with JWKS and reads roles with the caller's token.
- **[SEC-verify] `resolve_tenant`:** confirmed: `.first()` with no ORDER BY was nondeterministic when a UUID-shaped slug existed. Fixed as above (SEC-H1).

### Behaviour fixes
- **[SEC-H1]** `mcp_server._dispatch` returned `model_dump()` (Python datetimes), so `POST /mcp/tools/get_run` for a run that exists answered 500 (response validation). It was unreachable before, because tenant lookups never found the caller's runs. Every dispatch now returns `model_dump(mode="json")`.

### Corrected tests (old → new)
- **[SEC-L1]** `backend/tests/test_api_hardening.py::test_readyz_not_ready_when_a_dependency_fails`.
  - Old: `assert "db down" in body["checks"]["database"]["detail"]`. That pinned the leak itself.
  - New: the exception carries a host and user. The test asserts detail `== "unavailable"`, that none of `db down`/`db.internal`/`postgres` appears in the response, and that the full message is in the log (`caplog`). Every other assertion is unchanged.
  - `tests/test_postgres_stores.py::test_missing_database_url_is_503_blocked_on_james` is unchanged and still passes (the marker is still public).
- **[SEC-L4]** `backend/audit/agent/test_a7_qcompass_routes.py::test_post_run_writes_provenance_sidecar`.
  - Old: `sidecar = Path(body["provenanceSidecar"]); assert sidecar.exists()`, an absolute server path.
  - New: asserts the reference is relative with no `..`, then the same `exists()` and content assertions on `_artifacts_root().parent / ref`.
- **[SEC-L4]** `…::test_visualization_endpoint_returns_typed_timeline`. Old: GET for a never-submitted id `schwinger-1plus1d`. New: submits a hep run with that `runId` first, then the same GET and assertions. A visualization now needs the caller's run.
- **[SEC-L4]** `backend/audit/agent/test_a8_auth_tenancy.py::test_ws_visualization_accepts_valid_token`: setup only. An `acme` run `kawai-kim-natural` is enqueued before connecting. Assertions are unchanged.
- **[SEC-L5]** `backend/tests/test_deploy_config.py::test_cloud_run_services_are_production_safe`.
  - Old: all three Secret Manager refs required on every service.
  - New: `SECRETS_BY_SERVICE` (API: `DATABASE_URL`, `SUPABASE_URL`; workers: all three), each still required as a `latest` Secret Manager ref. Two assertions are added: the service's secret refs equal that set exactly, and the API has no `SUPABASE_SERVICE_ROLE_KEY`.
  - Stricter for every service. The one dropped requirement, the API holding the key, is the finding.
- **[SEC-H1] Fixtures only, no assertion changed.** In-process tool calls with no principal now need `QCOMPASS_ENV=dev`. Autouse `_dev_tenant` was added in `tests/agent/test_approval_flow.py` and `audit/agent/test_a6_run_traceability.py`, and a `dev_tenant` fixture on `tests/test_worker_queue.py::test_cosmology_progress_comes_from_modules_as_they_finish`.
- New tests:
  - `backend/tests/test_security_gate1.py` (27);
  - `test_deploy_config.py::test_deploy_workflow_pins_every_action_and_scopes_the_cloudflare_token`.

### Removals with replacement
- **[SEC-H2]** `src/lib/jobs.ts` (`enqueueJob`, a direct `jobs` insert from the browser, never imported) → enqueue through the API: `POST /api/qcompass/domains/{id}/runs` via `src/lib/sdk.ts`.
- **[SEC-H2]** RLS policy "tenant members enqueue jobs" → "service role enqueues jobs" (down migration restores main's).
- **[SEC-H1]** Dev-tenant fallback in `runs._tenant_uuid` (any environment) → `principal.resolve_tenant_slug` (dev only).
- **[SEC-M2]** `bunx wrangler deploy` → `./node_modules/.bin/wrangler deploy` (the locked copy).
- **[SEC-L5]** API service env `SUPABASE_SERVICE_ROLE_KEY` → none (workers keep it).

### BLOCKED-ON-JAMES
- **[SEC-H1]** If the production Supabase project already has a tenant whose slug is `dev` (with `created_by` set) or is UUID-shaped, `20261031200000` leaves the constraint `NOT VALID` and raises a NOTICE. James should rename that tenant, then run `alter table public.tenants validate constraint tenants_slug_reserved_check`. New rows are guarded either way.
- **[SEC-M2]** None new. The workflow first runs on GitHub with the existing secrets (CI-PENDING).

### Observations outside these findings (not changed)
- `deploy/qcompass-api.yaml` doesn't provide `SUPABASE_PUBLISHABLE_KEY`, which `supabase_auth` needs for verdict roles (P4-01). Until it is added, those routes answer `BLOCKED-ON-JAMES:SUPABASE_PUBLISHABLE_KEY`.
- The other `release-please.yml` jobs (outside this finding's scope) still use tag-pinned actions (`release-please-action@v4`, `pypa/gh-action-pypi-publish@release/v1`, …).

## Gate 1 code review fixes (R16, folded into the security lane) — new section

### Decisions
- **[REV-B1]** Same bug as SEC-H1.
  - With the async `require_scope`, `active_tenant()` is bound in the API process, so the router's budget hook (`auth.install_budget_hook`) gates by the caller's tenant. Before, `gate_spend` received `None` and skipped silently.
  - `cancel_run` is now an MCP tool (approval-gated, tenant-scoped). Another tenant's run, or a missing one, is `NOT_FOUND` before the approval is spent.
  - Async tools run from the sync dispatcher through `mcp_server._run_coroutine`.
- **[REV-B2] Option chosen: label the frames, don't refuse them.** `VisualizationResponse` gains `synthetic: true` and `source: "synthetic-bake"`, and the WS header carries the same flag.
  - The domain visualizer already labels `metadata.synthetic`. `normalizeDomainTimeline` now passes through `source`, and `surface.tsx` says "Synthetic frames — not a computed result. Real-run timelines arrive with P4-04."
  - A synthetic response also never opens the live stream (existing rule).
  - Unknown or foreign run ids are 404 (SEC-L4). The SDK was regenerated.
  - A 501 would have broken A7's visualization contract tests, which R4 forbids weakening. The label keeps them, and R7 is met.
  - The cosmology visualizer card (`CosmologyVisualizerDetail`) is left to the physics lane, which owns the cosmology synthetic badge (decision 13). `VisualizationTimeline.synthetic` is populated for it.
- **[REV-SF1]** New migration `20261031200300_qcompass_queue_lease_guard.sql` (`create or replace`; the down migration restores the 20261031180000 bodies). In the dead-letter branch, the janitor sets the run to `failed` (only if it hasn't ended, and only within the job's tenant) and inserts a `status: failed` job event.
  - Streams are bounded: SSE, WS and `RunRegistry.stream` (`settings.StreamBound`) stop after `QCOMPASS_STREAM_IDLE_SECONDS` (default 900) with no new event, or after `QCOMPASS_STREAM_MAX_SECONDS` (default 7200) overall.
  - When they stop, they emit an `error` event `{code: "STREAM_ABORTED"}`. SSE then sends `end`, WS closes 1000, and the legacy SSE sends `event: error`. Clients may reconnect and replay.
- **[REV-SF2] Lease holder only.**
  - The same migration adds `complete_job(job, worker, result, error) → boolean`, which completes only while `status = 'running' and locked_by = worker`.
  - The old 3-argument `complete_job` now raises, so no caller can bypass the check (its only caller was `JobQueue`).
  - `heartbeat_job` already checked `locked_by`.
  - `JobQueue.set_run_status/save_result/save_provenance/emit` take `job_id` + `worker_id` and apply only under the lease. `set_run_status` and `save_result` never touch a `canceled` run, with or without a lease.
  - The worker's `_GuardedQueue` injects the lease into every handler write and turns a refused write into `JobCancelled`. The worker's own failure and completion paths pass `worker_id` too, so worker A can no longer fail or complete worker B's job or run.
- **[REV-SF4] Agent memory tenancy.** New migration `20261031200400_qcompass_agent_memory_tenancy.sql`:
  - adds nullable `tenant_id` (FK to tenants, indexed) to the six `agent_*` tables;
  - backfills them to the `dev` tenant if one exists, otherwise leaves them null (invisible to everyone);
  - adds member read policies on hypotheses, plans, run links, tool calls and patches. Approval tokens stay service-only, since a token id is a bearer secret.
  - The down migration renames the columns `_deprecated_tenant_id_20261031200400` (R13), and re-applying renames them back.

  `ConversationStore` takes `tenant=` on every method (`None` falls back to `resolve_tenant_slug`, the dev tenant in dev only). `/api/approvals`, `/v1/chat`, `/api/runs`, the MCP patch, hypothesis and cancel tools, and `start_run`/`cancel_run`/`save_plan` all pass the principal's tenant. An approval token issued to one tenant doesn't verify in another. This also closes the approval-token cross-tenant observation from the security section.
- **[REV-SF5] One shape: the platform route.** In API mode `services/simulator.ts` reads `GET /api/qcompass/domains/cosmology.ucglef1/runs/{id}` and streams its `/stream`. This one route serves both run kinds: workbench `qcompass.run` stores `payload.result.run_result`, and agent `ucgle_f1.run` stores the RunResult itself. `cosmologyRunResult` reads either.
  - A not-yet-completed run is `NOT_FOUND`.
  - The cosmology adapter's `run()` calls the new `awaitRun`, which follows the stream to its terminal status and then reads the result.
  - Fixture mode is unchanged byte for byte, so R19 holds (`check_r19.sh` passes).
  - The legacy `/api/runs/*` routes remain for MCP and agent clients.
  - Only API-mode code paths were edited. The cosmology run views and home summary belong to the physics lane.
- **[REV-SF6] Both engine resolvers kept.** `qcompass_core.db` and `ucgle_f1.db.engine` stay separate:
  - `qcompass-core` is only an optional extra (`qcompass`) and a dev-group dependency of the backend.
  - Making the backend's core engine import it would make `qcompass-core` (with `openfermion`, `h5py`, …) a hard runtime dependency of `ucgle_f1`.
  - `qcompass_core` may not import `ucgle_f1` (boundary guard).
  - The drift alarm's `uv sync --package ucgle_f1` still installs the dev group, but a plain `pip install ucgle_f1` would break.

  Parity tests (`test_sf6_*`, 7 cases) assert identical URL rewriting, identical `BLOCKED-ON-JAMES:DATABASE_URL` blocking and identical pool settings. There was no behavioural bug, so these tests pass on 3d2355a too. They are a guard, not a regression test.
- **[REV-nit] JWKS:** an unknown `kid` forces one refetch, rate-limited to one per 30 s per URL, so a rotated Supabase key works without waiting out the 600 s cache and forged kids can't hammer the endpoint. HS256 stays refused. A legacy Supabase project with HS256 signing needs asymmetric JWT signing keys enabled.
- **[REV-nit] CUDA plugin in the lock:** `ucgle_f1` gains the extra `cuda12 = ["jax-cuda12-plugin[with-cuda]==0.12.0.1 ; sys_platform == 'linux'"]`. `uv lock` resolved it with no conflict (+15 packages: the plugin, the pjrt plugin and NVIDIA CUDA wheels). `Dockerfile.cuda12` syncs `--extra cuda12` and installs nothing outside the lock (`docker build --check`: no warnings). CI's `UV_SYNC` doesn't select this extra, so the licence gate's environment is unchanged. The NVIDIA wheels' own licence covers the CUDA image as before.
- **[REV-nit] uv workspace:** `packages/__pycache__` added to `[tool.uv.workspace].exclude`.
- **[REV-nit] Artefacts in API mode:** `services/artifacts.ts` `listArtifacts`/`downloadArtifact` throw `NOT_IMPLEMENTED` ("not available from the API until P4-04/P4-06") instead of calling the nonexistent `/api/runs/{id}/artifacts*` routes.
- **[REV-nit] openapi-spec-validator: not a bug.** It is not a backend runtime dependency. It appears only in the backend's `[dependency-groups] dev` (`backend/pyproject.toml`) and the root dev group. Nothing changed.
- **[REV-nit] `A_END_H_END`:** dropped by the coordinator. The physics lane owns `couplings.py` (LEDGER decision 11).

### Corrected tests (old → new)
- **[REV-nit]** `audit/agent/test_a8_auth_tenancy.py::test_scopes_are_enforced`: old `assert ok.status_code in {200, 202}`; new `assert ok.status_code == 202`. This is a tightening; submit is always 202 since P3-02.
- **[REV-nit]** `tests/test_worker_queue.py::test_fifty_concurrent_runs_complete_with_two_worker_processes`:
  - The two workers are terminated, and their pipes drained and closed with `communicate()`, in the `finally`.
  - The `statuses`, `workers` and return-code assertions, unchanged, now run after it.
  - Before, two assertions ran inside the `try` and the stderr reads in the `finally` could leak a pipe on failure.
- **[REV-SF2]** `tests/test_worker_queue.py::test_heartbeat_janitor_requeue_and_dead_letter`: the stale-worker call `q.complete(job.id, result=…)` now names its worker (`worker_id="dead-worker-2"`), because completion requires one. Assertion unchanged (the job stays `failed`).
- **[REV-SF4] Fixtures only:**
  - `audit/agent/test_a5_audit_preservation.py` gains an autouse `QCOMPASS_ENV=dev` fixture, because in-process patch tools use the dev tenant.
  - `tests/test_postgres_stores.py::test_backend_migration_is_reversible_without_data_loss` re-applies `20261031200400` after recreating the agent tables, so later tests see the current schema. Its assertions are unchanged.
- **[REV-SF1/SF2] Fixtures only:** `tests/test_postgres_stores.py::test_worker_queue_migration_is_reversible_without_data_loss` re-applies `20261031200300` after it re-creates the 20261031180000 functions, for the same reason as above. Its assertions are unchanged.
- **[REV]** The Gate 1 tests seed legacy runs from their own frozen payload (`backend/tests/data/gate1_run_result.json`, a copy of the 3d2355a run fixture) rather than `public/fixtures/runs/kawai-kim-natural.json`, which the physics lane now owns.
- New tests:
  - `tests/test_security_gate1.py`: B2, SF1 (2), SF2 (3), SF4 (2), JWKS nit, SF6 (7);
  - `audit/agent/test_a8_auth_tenancy.py`: cross-tenant legacy runs and MCP tools, `cancel_run` own run, budget hook;
  - `tests/test_deploy_config.py::test_cuda_image_installs_nothing_outside_the_lock`;
  - `src/lib/__tests__/cosmologyLive.test.ts` (4);
  - `src/lib/visualizer/__tests__/domainFrames.test.ts` (+2).

### Removals with replacement
- **[REV-SF2]** `complete_job(uuid, jsonb, text)` (no lease check) → `complete_job(uuid, text, jsonb, text)`. The old signature remains and raises.
- **[REV-SF5]** API-mode `sdk.getUcgleRun`/`sdk.streamUcgleRun` in `services/simulator.ts` → `sdk.getRun`/`sdk.streamRun` on `cosmology.ucglef1`. The SDK functions remain for agent clients.
- **[REV-nit]** `Dockerfile.cuda12` `uv pip install jax-cuda12-plugin…` → `uv sync --frozen … --extra cuda12`; the `JAX_VERSION` build arg is removed.

### BLOCKED-ON-JAMES
- **[REV-nit]** `BLOCKED-ON-JAMES:supabase-jwt-signing-keys`, only if the production Supabase project still signs with the legacy HS256 secret. The API accepts only asymmetric (RS256/ES256) keys from the JWKS, so James would enable asymmetric JWT signing keys in the Supabase dashboard. No secret is needed by the code.
- **[REV-SF4]** If production agent rows exist with no `dev` tenant, they stay `tenant_id is null` (invisible). Assigning them to tenants needs James's call.

## W1 potential-parameter boundary (Gate 1)

Evidence: `docs/build/evidence/W1-potential-params.md`. The frontend sent potential parameters M2 does not define (`natural {f, Lambda4}`, `hilltop {mu, p}` with no `V0`). With `coupling_model="physical"` the default (Decision 11), an API run of the Configurator's V2 default failed in the worker with "potential parameters missing: ['f_a', 'Lambda']".

### Decisions
- **[W1-PARAMS] One wire shape: the API carries the potential's parameters in the units the Configurator shows, and the backend request model is the boundary.** `ucgle_f1.domain.POTENTIAL_PARAM_FORMS` is the one table of names and units; every name has exactly one unit:
  - starobinsky `M` [M_Pl];
  - natural `f` [GeV] and `Lambda4` [M_Pl⁴] (the Configurator's names), or `f_a` and `Lambda` [M_Pl] (M2's names, which Decision 11 put in `kawai-kim-natural.json` and which the audits, `backend/configs/*.yaml` and the agent tools use);
  - hilltop `V0` [M_Pl⁴], `mu` [GeV], `p` (integer 2–64, default 4);
  - any kind: optional `phi0` [M_Pl] (`initial_field`'s override); custom: the snippet's own symbols.

  A params dict must use one form: mixing natural's two spellings is refused as ambiguous. The run route's request model and the agent's `RunConfig` share this one model (`CosmologyPotential` now subclasses `domain.Potential`), one validator and one conversion.

  M2's natural names stay accepted because Decision 11 put them in `kawai-kim-natural.json`, and R4 protects the tests and audits that send them: `test_qcompass_adapter.py`'s round trip, `backend/audit/conftest.py`, and the agent tests' configs. Refusing them would need James. Hilltop has one form: its `mu` is GeV on the wire, and only `engine()` produces M2's M_Pl value.
- **[W1-PARAMS] Why the backend, not the frontend service layer.**
  - The only M_Pl is `M_PL_GEV` (`m1_background/background.py`). Converting in `services/simulator.ts` would need a second constant in TypeScript, or a generated copy of it.
  - The physics lane already converts the other GeV inputs in the backend: `Γ_φ` at the pipeline's M1 step and `couplings.f_a` in `couplings.py`. The potential's conversion now runs at the pipeline's M2 step, beside Γ_φ.
  - Every client gets the same rule: the UI, the agent's `/api/runs` and MCP tools, hydra YAML configs.
  - A RunConfig stays exactly what the client sent, so a stored run's config re-validates unchanged and round-trips through the qcompass manifest (`test_manifest_round_trip`, R4).
- **[W1-PARAMS] The conversion, exactly once.** `Potential.engine()` returns M2's form: `f_a = f / M_PL_GEV`, `Lambda = Lambda4 ** 0.25`, hilltop `mu / M_PL_GEV`. Every other parameter (M, V0, p, phi0, M2's natural names, custom symbols) passes through as the same float objects. It returns an `EnginePotential`, whose `engine()` is itself, so nothing is converted twice. `RunPipeline.run` applies it at the M2 step. `compile_potential`, `initial_field` and `coupling_profile` also call it, which is a no-op on a converted potential, so a GeV value can never reach M2 unconverted. Existing engine-form configs (the audits, the Decision 11 fixture, Starobinsky) produce bit-identical results: the adapter's `data_regression` snapshot and the slow suite, `test_gb_to_zero_decoupling` included, pass unchanged.
- **[W1-PARAMS] Validation and 422.**
  - `domain.Potential` refuses unknown names, mixed spellings, non-finite values, non-positive dimensionful parameters, and a `p` that is not an integer from 2 to 64. Each message names the kind and the accepted forms with their units.
  - Completeness (every parameter of the chosen form) is required by `CosmologyPotential`, the run route's model, not by `domain.Potential`. The agent's A1 audit (`backend/audit/agent/test_a1_schema.py`, frozen) parses a partial natural dict through `StartRunInput`.
  - `POST /api/qcompass/domains/{d}/runs` now calls the plugin's optional `validate_problem` before enqueueing. Cosmology's parses the `CosmologyManifest` and compiles the potential in M2's units with every parameter bound (`potential_args`). A failure is 422 `INVALID_INPUT`, with one message part per error (`api_errors.invalid_input`). Before, a bad problem was queued (202) and failed in the worker.
  - `POST /api/runs` answers a refused RunConfig with 422 instead of 500.
- **[W1-PARAMS] Hilltop V0: a Configurator field, never invented by the API.** `V0` is added to the Configurator's hilltop parameters, defaulting to 1e-7 M_Pl⁴. That is the value the V(ψ) preview always drew (`potentialEvaluator.ts` hard-coded it), so the run now uses the V(ψ) the user sees, and the preview reads the field. The API supplies no V0: a hilltop without one is 422 "missing V0 [M_Pl^4]". No R19 page shows hilltop, because they render the natural default. The radio hint "μ, p" is on the R19 default page, so it stays as it is.
- **[W1-PARAMS] Hilltop p: generalised, not refused.** M2's hilltop is now V0 (1 − (φ/μ)^p) for an integer p from 2 to 64, default 4. p is an integer exponent inside the sympy expression, not a lambdify argument. So p = 4, or no p, builds the original expression symbol for symbol and lambdifies the same code:
  - `test_hilltop_p4_is_the_original_expression_symbol_for_symbol` checks `srepr` equality;
  - `test_hilltop_p4_values_are_bit_identical_to_the_original` checks V, V′ and V″ with `array_equal`.

  No existing test used hilltop, and the fast and slow suites are unchanged. This was chosen over refusing p ≠ 4 because the Configurator exposes p and V0(1 − (φ/μ)^p) is the standard hilltop family.
- **[W1-PARAMS] SDK types.** `Potential.params`'s OpenAPI schema is now `anyOf` of the per-kind forms, with units in each description. It is built from the same table (`WithJsonSchema`). `openapi.json` and `openapi.ts` were regenerated (`gen_sdk_types.sh --check` passes). `services/simulator.ts` types the problem as `config satisfies sdk.RunConfig`. The cosmology manifest schema (`GET …/schema`) marks every parameter of a form as required.
- **[W1-PARAMS] One source for the Configurator's defaults.** `src/lib/configDefaults.json` holds `defaultsForPotential`'s values and the V2 baseline. `configDefaults.ts` imports it, and the backend test reads it. Values and key order are unchanged for natural, Starobinsky and the V2 couplings (the R19 pages are pixel-identical to 040bc36, see evidence). `defaultsForPotential` still returns a fresh object.
- **[W1-PARAMS] Custom potentials.** `compile_potential` now refuses a symbol that `params` does not bind ("custom potential: unbound parameter(s) […]"). Before, this failed only when V was first evaluated. A snippet that is not one expression is now a `ValueError` naming the problem (it was a bare `SyntaxError`), so the route answers 422.

### Corrected tests (old → new)
- **[W1-PARAMS] Route-contract tests that posted an empty cosmology problem (6 tests).**
  - Tests:
    - `backend/tests/test_security_gate1.py::test_l2_run_id_collision_does_not_reveal_another_tenants_run`;
    - `…::test_l4_submit_returns_a_logical_sidecar_reference`;
    - `backend/audit/agent/test_a7_qcompass_routes.py::test_get_run_returns_sidecar_payload`;
    - `…::test_ws_visualization_streams_decodable_frames`;
    - `backend/audit/agent/test_a8_auth_tenancy.py::test_scopes_are_enforced` (the member's post);
    - `…::test_cross_tenant_runs_and_scans_are_404`.
  - Old: `json={"manifest": {"problem": {}}}` (L2: `body = {"runId": "qc_shared_id", "manifest": {"problem": {}}}`).
  - New: `json={"manifest": _COSMOLOGY_PROBLEM}`, a complete Starobinsky problem (M = 1e-5, `precision: "fast"`) defined once per file. L2 keeps its `runId`.
  - Why the old ones were wrong: they relied on the run route queueing a cosmology problem the worker refuses, the 202-then-fail path this fix closes. Their subjects are the run-id collision answer, sidecars, visualization frames, scopes and tenancy, none of which is problem validation. Every assertion is unchanged; the new bodies pass on 040bc36 too.
  - `backend/audit/physics/**` is not touched. The physics freeze (`golden.lock`) hashes only that tree.
  - The viewer posts in A8 (`test_scopes_are_enforced`, `test_supabase_users_resolve_tenants_through_membership`) are unchanged, and still answer 403: the scope is checked before the body.
- **[W1-PARAMS] Fixture (input only, no result field).** `public/fixtures/runs/failing-run.json` `config.potential.params`.
  - Old: `{"phi0": 0.4, "Lambda": 0.001}`.
  - New: `{"phi0": 0.4, "V0": 1e-7, "mu": 1e16, "p": 4}`.
  - `Lambda` was never a hilltop parameter, in M2 or the Configurator, and V0 and mu were missing, so the config could not compile ("potential parameters missing: ['V0', 'mu']"). V0, mu and p are the Configurator's hilltop defaults. `phi0` and every result field are kept. The fixture is not on an R19 page.
- New tests (each fails on 040bc36, passes now):
  - `backend/tests/test_frontend_potential_configs.py` (30): every frontend config accepted and compiled; the HTTP 202 and 422 cases; the custom snippet refusal;
  - `backend/tests/unit/test_potential_params.py` (23): conversion values, pass-through, idempotence, refusals, hilltop p;
  - `src/lib/__tests__/configDefaults.test.ts` (4).

### Removals with replacement
- **[W1-PARAMS]** `CosmologyPotential`'s own copy of `kind`/`params`/`customPython` (a separate `BaseModel`) → a subclass of `domain.Potential` that adds completeness (R20). The now-unused `cosmology_manifest.PotentialKind` → `domain.PotentialKind`.
- **[W1-PARAMS]** `configDefaults.ts`'s literal `switch` and V2 object → `configDefaults.json`, which it imports.
- **[W1-PARAMS]** `potentialEvaluator.ts` hilltop `const V0 = 1e-7` → `p.V0 ?? 1e-7`.
- **[W1-PARAMS]** `couplings.py` docstring "The potential's parameters (`Potential.params`) are already in M_Pl units" → they arrive in API units and are converted once by `Potential.engine()`.

### BLOCKED-ON-JAMES
- **[W1-PARAMS] `BLOCKED-ON-JAMES:ui-v2-defaults-vs-paper-benchmark`.**
  - The Configurator's V2 natural default, `{f: 7e16 GeV, Lambda4: 2.5e-7 M_Pl⁴}`, is f_a = 0.0287 M_Pl and Λ = 0.0224 M_Pl. Decision 11's paper benchmark is f_a = 8.7 M_Pl and Λ = 0.0071154 M_Pl. The displayed defaults were left alone (R19, requirement 4).
  - Measured consequence: with the units right, the V2 default is accepted (202) but does not inflate under the physical default. A sub-Planckian f_a gives |η| ≈ 1/f_a² ≈ 1200, so inflation ends almost at once. `coupling_profile` then refuses: "trajectory covers τ ≥ -0.0013 only; M3 needs τ ≥ -5.0".
  - So `e2e-live` still fails: the run's status is `failed` where the spec expects `completed`. It no longer fails at the parameters.
  - Options:
    - (a) Make the V2 default the paper benchmark in the Configurator's units: f = 2.118624e19 GeV (8.7 × M_PL_GEV) and Lambda4 = 2.563334027300118e-09 M_Pl⁴. They convert back to f_a = 8.7 and Λ = 0.0071154324599829784 exactly, and the run completes at "fast" (η_B NaN from the budget gate, which the spec accepts). This needs an R19 rebaseline beyond Decision 13's two.
    - (b) Let the e2e-live cosmology spec run a configuration that inflates; the Configurator's Starobinsky default (M = 1.3e-5) completes. That changes the spec's input.
    - (c) Keep e2e-live red until a Decision.

### Observations (not changed)
- **[W1-PARAMS] Custom source format.** The Configurator's `DEFAULT_CUSTOM_PYTHON` is a `def V(psi):` function, and its linter (`potentialValidator.ts`) requires one. The backend compiles one expression in `phi`, although its module docstring says "defines a V(phi, **params) function". This is a source-format mismatch, not a parameter one. The API now refuses the default snippet at submit with "customPython must be one expression in phi". Whoever owns the custom contract (SEC-L3's safe parser) should pick one form.
- **[W1-PARAMS] Hilltop default.** `{V0: 1e-7, mu: 1e16 GeV, p: 4}` compiles but does not inflate under the physical model either (τ ≥ -0.0247 only). It is a UI default, not a benchmark.
