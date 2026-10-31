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
