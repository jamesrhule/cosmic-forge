# W1 — Gate 1 security fixes and code-review fixes

Branch `build/w1-platform`. Lane notes: `docs/build/lanes/W1-platform.md` ("Gate 1 security fixes" and "Gate 1 code review fixes").

Method (LEDGER decision 14): each finding has a regression test that fails on the reviewed head `3d2355a` and passes after the fix. Every database change is a new migration whose down migration restores main's version (or the previous lane version), and no existing migration was edited.

How "before" was measured: the fixed test files were copied into a detached worktree at `3d2355a` and run against that tree's sources (`PYTHONPATH=<base>/backend/src`, same venv, own Postgres 16 cluster; the vitest files likewise). Result: 43 of the new or changed backend tests failed on `3d2355a`, and 4 of the 6 new vitest cases failed (the other two are no-regression guards). With the fixes, all pass.

## Per finding

| ID | Fix | Regression test(s) | 3d2355a | After |
|---|---|---|---|---|
| SEC-H1 | Principal tenant passed explicitly (`RunRegistry`, simulator/research/patch tools, `_dispatch`, `/api/runs*`, `/mcp/tools/*`, `/v1/chat`); async `require_scope` binds the tenant in the request context; no `dev` fallback outside `QCOMPASS_ENV=dev`; migration `20261031200000` (slug guard); `resolve_tenant` prefers the id match | `test_security_gate1.py::test_h1_*` (8); A8 `test_cross_tenant_legacy_runs_and_mcp_tools_are_404` | 8 + 1 failed | pass |
| SEC-H2 | Migration `20261031200100` (service role only enqueues); worker refuses `JOB_TENANT_MISMATCH`/`JOB_RUN_MISSING`; tenant-filtered `result`/`provenance`/`events`; `src/lib/jobs.ts` removed (unused direct insert) | `test_h2_*` (4) | 4 failed | pass |
| SEC-M1 | Migration `20261031200200` (runs insert/update and "authors write results" require membership of `tenant_id`, or null) | `test_m1_*` (2) | 2 failed | pass |
| SEC-M2 | `deploy.yml`: every action pinned by SHA with `# vX`; Cloudflare secrets only on the wrangler step; `bun install --frozen-lockfile --ignore-scripts`; locked wrangler | `test_deploy_config.py::test_deploy_workflow_pins_every_action_and_scopes_the_cloudflare_token` | failed | pass |
| SEC-L1 | `/readyz` detail `unavailable` (or a bare `BLOCKED-ON-JAMES:<NAME>`), exception logged | `test_api_hardening.py::test_readyz_not_ready_when_a_dependency_fails` (corrected, see lane notes) | failed | pass |
| SEC-L2 | Generic 409 for a colliding `runId`, identical for own and foreign ids | `test_l2_run_id_collision_does_not_reveal_another_tenants_run` | failed | pass |
| SEC-L3 | Per-job wall-clock limit (`QCOMPASS_JOB_TIMEOUT_SECONDS`, default 3600, `JOB_TIMEOUT`, abandoned handler can't write, `/healthz` 503 while it lives); `_custom_expr` caps size, literals, exponents, constant digits | `test_l3_*` (10 cases; the 7 parametrised hang cases run in a subprocess with a 60 s timeout) | 9 failed, 1 passed (`…still_accepts_real_potentials`, a no-regression guard) | pass |
| SEC-L4 | Visualization (HTTP + WS) needs a run of the caller's tenant; `provenanceSidecar` is a relative logical ref; SDK regenerated | `test_l4_*` (2); A7 `test_post_run_writes_provenance_sidecar` (corrected) | 3 failed | pass |
| SEC-L5 | API service no longer mounts `SUPABASE_SERVICE_ROLE_KEY` | `test_deploy_config.py::test_cloud_run_services_are_production_safe[qcompass-api.yaml]` (corrected, stricter) | failed | pass |
| SEC-verify | `resolve_tenant` nondeterminism confirmed; fixed with SEC-H1 | `test_h1_resolve_tenant_prefers_the_id_match_and_slug_guard_is_reversible` | failed | pass |
| REV-B1 | (= H1) plus `cancel_run` MCP tool scoped to the tenant; budget hook sees the API tenant | A8 `test_cross_tenant_legacy_runs_and_mcp_tools_are_404`, `test_cancel_run_tool_cancels_the_callers_own_run`, `test_budget_hook_sees_the_principals_tenant_in_the_api` | 3 failed | pass |
| REV-B2 | `VisualizationResponse.synthetic/source`, WS header flag, UI label for `synthetic-bake` | `test_b2_visualization_frames_are_labelled_synthetic`; vitest `domainFrames.test.ts` "keeps the API's synthetic flag…" | failed / failed | pass / pass |
| REV-SF1 | Migration `20261031200300`: dead-letter fails the run + terminal event; bounded SSE/WS/legacy streams (`STREAM_ABORTED`) | `test_sf1_*` (2), `test_sf1_sf2_queue_migration_is_reversible` | 3 failed | pass |
| REV-SF2 | Same migration: `complete_job(job, worker, …)` lease-holder only, 3-arg form refuses; lease-guarded run writes; canceled never overwritten | `test_sf2_*` (2) | 2 failed | pass |
| REV-SF4 | Migration `20261031200400`: `tenant_id` on agent tables + member read policies; `ConversationStore` tenant-filtered | `test_sf4_*` (2) | 2 failed | pass |
| REV-SF5 | Live cosmology on the platform route only; `awaitRun` waits for the terminal status | vitest `cosmologyLive.test.ts` (3 SF5 cases) | 2 failed, 1 passed (the "unfinished run" case, which also held before) | pass |
| REV-SF6 | Both engine resolvers kept (see lane notes); parity guard | `test_sf6_*` (7) | passed (no behavioural bug; guard only) | pass |
| nit JWKS | One rate-limited refetch on an unknown `kid` | `test_nit_unknown_kid_triggers_one_rate_limited_jwks_refetch` | failed | pass |
| nit CUDA lock | `cuda12` extra in uv.lock; Dockerfile installs nothing outside it | `test_deploy_config.py::test_cuda_image_installs_nothing_outside_the_lock` | failed | pass |
| nit artefacts | API mode reports `NOT_IMPLEMENTED` | vitest `cosmologyLive.test.ts` "artefacts in API mode" | failed | pass |
| nit A8 202 | Assert exactly 202 | A8 `test_scopes_are_enforced` (tightened) | passed (behaviour was already 202) | pass |
| nit pipes | 50-run test drains and closes worker pipes before asserting | `test_worker_queue.py::test_fifty_concurrent_runs_complete_with_two_worker_processes` | n/a (test hygiene) | pass |
| nit uv `__pycache__` | Workspace exclude added | not reproducible here: `uv lock --check` on 3d2355a with `packages/__pycache__/x.pyc` present still passes (uv as installed) | — | pass |
| nit openapi-spec-validator | Not a bug: it is only in dev groups | — | — | — |
| nit `A_END_H_END` | Dropped by the coordinator (physics lane, decision 11) | — | — | — |

The corrected A7 visualization test and the A8 WS test only gained setup (submit or enqueue the run first). They pass on both trees, which is expected: they are kept green, not regression tests.

## Suites on the final tree

| Suite | Result |
|---|---|
| Backend fast (`pytest -q -m "not slow"`) | 466 passed, 2 deselected, 1 xfailed (the P3-07 evidence recorded 418) |
| Packages (`pytest packages -q --import-mode=importlib`) | 350 passed, 7 skipped |
| `bun run lint` | 0 errors, 15 warnings (pre-existing `react-refresh` warnings) |
| `bunx prettier --check .` | clean |
| `bunx tsc --noEmit` | clean |
| `bun run test` (vitest) | 20 files, 109 tests passed |
| `bun run build` | built |
| Playwright chromium (fixture suite) | 52 passed, 3 failed: the three cosmology screenshot comparisons (R19, sandbox fonts; see below) |
| Playwright live (`-c playwright.live.config.ts`) | 3 passed |
| `scripts/check_r19.sh` | 9 PNGs match R19.sha256 |
| `scripts/gen_sdk_types.sh --check` | SDK types match |
| `uv lock --check` | passes (557 packages) |
| `docker build --check -f docker/Dockerfile.cuda12 .` | no warnings |
| `bun install --frozen-lockfile --ignore-scripts && bun run build && wrangler deploy --dry-run` (M2's secret-less build) | works |

**R19 in this sandbox.** The three chromium `cosmology-byte-identity` comparisons fail the same way on `3d2355a`: the sandbox's fonts differ from CI's. The actual renders match across trees:
- `/` gives `358c1a759c2e` on both trees;
- `/visualizer` gives `5118e9dd436c` on both trees;
- `/visualizer/kawai-kim-natural` alternates between `2ca2b0313f18` and `3bdbd1fc0c1a` from run to run, and both values were observed on both trees.

No baseline or `R19.sha256` was touched. CI is the authority.
