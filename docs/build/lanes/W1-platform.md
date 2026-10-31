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

## Substitutions
- None yet.

## Corrected tests (old → new)
- `backend/audit/agent/test_a7_qcompass_routes.py::test_get_run_returns_sidecar_payload` (A7 is editable under R4, correction 2). The route's contract changed in P4-01 from the raw sidecar to the frontend's `DomainRunResult`.
  - Old: `assert body["runId"] == run_id` and `assert body["domain"] == "cosmology"`.
  - New: `assert body["id"] == run_id`, `assert body["domain"] == "cosmology.ucglef1"` and `assert "classical_reference_hash" in body["provenance"]`, plus a GET by the full domain id returning the identical body.
  - Same intent (the stored run comes back for its id and domain); strictly more assertions.
- `backend/tests/test_lovable_contract.py::test_verdict_sample_yaml_round_trips_when_present`: the data path moved (correction 9). Old `VERDICT_DIR = _FIXTURES_ROOT / "verdict"` with `"sample-verdict.yaml"`; new `backend/src/ucgle_f1/m8_agent/data/verdicts` with `"sample.yaml"`. Assertions unchanged.

## Removals with replacement
- `CORSMiddleware(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])` → env allowlist with explicit methods and headers.
- `server._status` table, `mcp_server._status_for` table, `qcompass_routes._AUTH_CODE_TO_HTTP` → `api_errors.HTTP_STATUS_FOR_CODE`. The two function names remain as thin delegates.

- `public/fixtures/verdict/sample-verdict.yaml` → `backend/src/ucgle_f1/m8_agent/data/verdicts/sample.yaml`; `sample-verdict.md` → `…/verdicts/sample.md`; `sample-verdict.yaml.json` → removed, replaced by `GET /api/verdict/{id}` (correction 9).
- `src/services/qcompass/verdict.ts` static-fixture read → authenticated API fetch.

## Behaviour fixes
- `admin.verdict.tsx`: a failed verdict fetch now shows an error instead of an endless "Loading…".
- `POST /api/approvals` `scopes`: comma string → list, matching its documented contract.

## BLOCKED-ON-JAMES
- None yet.
