# W1 — Gate 1 round 3, ops lane (deploy/release workflows, backend ops)

Branch `build/w1-ops`, based on `9c6bf4c`. Lane notes:
`docs/build/lanes/W1-ops.md` (finding ids, decisions, the one corrected test,
BLOCKED-ON-JAMES). Findings: c6-deploy and c7-misc clusters and the critic's
SEC-M2/SEC-L5 residuals.

## How "before" was measured

`git archive 9c6bf4c` was unpacked into a scratch directory, the new test files
were copied into its `backend/tests/`, and they were run against that tree's
sources (`PYTHONPATH=<scratch>/backend/src`, this branch's venv; `import
ucgle_f1` was checked to resolve to the scratch tree). The scratch tree's
`node_modules` is a link to this branch's install, so both runs use the same
wrangler 4.82.2. The scratch tree and copies were deleted afterwards. Only
behavioural failures are counted below; an `AttributeError` for a constant
that does not exist on `9c6bf4c` is listed but not counted.

Versions: Python 3.12 (uv-managed venv), uv 0.11.32, bun 1.4.4, wrangler
4.82.2, jq 1.7, Postgres 16 (the backend harness's own cluster).

## Per finding

| Id | Fix | Test(s) | 9c6bf4c (reason) | After |
|---|---|---|---|---|
| SEC-M2-residual (c6 MEDIUM, deploy.yml:240) | `web-check` / `web-build` (no environment, no secret, `contents: read`, uploads `dist/`) / `web` (fresh checkout, `no-cache` setup-bun, `--ignore-scripts` install, download by artifact id, refusal step, token on the wrangler step only) | `test_security_gate1_deploy.py::test_m2_planted_wrangler_config_never_runs_next_to_the_token` (7 cases), `::test_m2_build_and_deploy_are_separate_jobs`, `::test_m2_clean_build_output_deploys` (positive control) | 7/7 planted cases fail for the bug: "build at the top level" — the planted command ran with the token (`token=fake-CLOUDFLARE_API_TOKEN` written by wrangler's custom build); the other six — the deploy step ran wrangler with the token on an unchecked config. Separate-jobs test fails: `'web' != 'web'` (the build shares the token's job). Positive control passes on both | 9/9 pass |
| c6-setup-bun-cache (LOW) | `no-cache: true` on both setup-bun steps | `::test_setup_bun_never_restores_from_the_actions_cache` | fails: `web: setup-bun without no-cache: true` | pass |
| c6-gcp-job-env (LOW) | GCP_* / QCOMPASS_CORS_ORIGINS at step level; check step sees booleans | `::test_no_secret_in_workflow_or_job_env` | fails: `gcp: secret in job-level env` | pass |
| c6-branch-guard (LOW) | Same `if` guard on every job | `::test_production_deploys_only_from_main_or_release_tags` (10 cases) + `::test_expression_evaluator_follows_github_semantics` | the 5 "must not deploy" cases fail (production from `refs/heads/feature`, `refs/tags/ucglef1-v1.0.0`, `refs/pull/7/merge`, `Production` from a feature branch, unknown `prod`): `gcp` and `web` have no guard; the 5 "deploys" cases pass on both | 11/11 pass |
| c6-release-please (MEDIUM) | `permissions: {}` + per-job minimum; every action SHA-pinned with its tag; hash-locked docs tools; `persist-credentials: false` where the job only reads | `test_security_gate1_release.py` (5) | 4 fail for the bug: workflow-wide `{contents, id-token, packages, pages, pull-requests: write}`; `googleapis/release-please-action@v4` not pinned; `publish-pypi` checkout keeps its token; `pip install mkdocs mkdocs-material pymdown-extensions` without `--require-hashes`. `test_what_each_job_publishes_is_unchanged` passes on both (guard) | 5/5 pass |
| SEC-L5-residual (c6 MEDIUM) | Documentation only: IAM split and per-secret IAM in `docs/qcompass/deployment.md`; `BLOCKED-ON-JAMES:GCP_API_SERVICE_ACCOUNT`, `BLOCKED-ON-JAMES:GCP_WORKER_SERVICE_ACCOUNT` | — (no code change; `test_deploy_config.py` unchanged and green) | — | — |
| c6-wrangler-devdep (NIT) | `"wrangler": "4.82.2"` devDependency, one-line `bun.lock` change | `bun install --frozen-lockfile` passes; npm licence gate 813 packages, 0 violations; `node_modules/.bin/wrangler` → `wrangler/bin/wrangler.js` 4.82.2 | — | pass |
| c7-jwks-stale-if-error (LOW) | stale-if-error (≤ TTL + 1 h), 30 s retry interval after a failure, single-flight fetch per URL | `test_supabase_auth_jwks.py` (7) | 5 fail for the bug: TTL lapse + endpoint down → `[503, 503, …]` (stale-if-error); 4199 s after the fetch, inside the bound, → 503 (no stale-if-error); cold-start outage → 50 fetches for 50 requests; 16 concurrent cold-start callers → 16 fetches; concurrent TTL refresh → callers block on their own fetches instead of answering from the cache. `test_constants_are_the_documented_bounds` fails with `AttributeError` (not counted). `test_unknown_kid_during_an_outage_is_503_and_rate_limited` passes on both (guard for unchanged forced-refetch behaviour) | 7/7 pass |
| c7-L1-readyz-exact (NIT) | Tightened assertion (lane notes, Corrected tests) | `test_postgres_stores.py::test_missing_database_url_is_503_blocked_on_james` | passes (the L1 fix is already in `9c6bf4c`). Mutation that appends the exception repr to the marker: old assertion passes, new fails | pass |
| c7-uv-workspace-members (NIT) | Explicit member list | `test_workspace_members.py` (2) | both fail: `glob in members: ['backend', 'packages/*', 'workers']`; with non-empty `packages/node_modules`, `packages/dist`, `packages/__pycache__`: `uv lock --check --offline` → `Workspace member …/packages/dist is missing a pyproject.toml (matches: packages/*)` | 2/2 pass |
| c6-cuda12-residual | No change (lane notes, Routed) | — | — | — |

### Repro outputs

`gate1/scratch-c7/jwks_repro.py` (fake clock), run unchanged on each tree:

| Case | 9c6bf4c | build/w1-ops |
|---|---|---|
| 1 rotation within TTL | 200 / 200, 2 fetches | 200 / 200, 2 fetches |
| 2 forged-kid flood, 100 req over 50 s | 3 fetches | 3 fetches |
| 3 forged kid, failing upstream; old kid after | 503, 200 (2 fetches) | 503, 200 (2 fetches) |
| 4 slot burned before rotation (t0+1, +29, +31) | 401 401 200 | 401 401 200 |
| 5 endpoint down after the TTL, 50 requests | {503}, 50 fetches | {200}, 1 fetch |

wrangler custom build, by hand (scratch workspace, wrangler 4.82.2 from
`node_modules`): a `dist/server/wrangler.json` with
`"build": {"command": "echo LEAK token=$CLOUDFLARE_API_TOKEN > leak.txt"}` and
`wrangler deploy --dry-run --config dist/server/wrangler.json` → wrangler
prints `[custom build] Running: …`, exits 0, and `leak.txt` holds
`LEAK token=fake-token`. The new refusal step stops the same file before the
token step (test above).

uv workspace: on a copy holding only the root `pyproject.toml`, `uv.lock` and
the member manifests, with non-empty `packages/node_modules/foo/index.js`,
`packages/dist/x`: `9c6bf4c`'s pyproject → error above; this branch's →
`Resolved 557 packages`, exit 0. (An empty directory does not trigger it.)

### Action pins (resolved 2026-11-02)

`git ls-remote https://github.com/<owner>/<repo>.git 'refs/tags/<major>.*'`,
newest patch of the major already in use, annotated tags peeled, commit dates
read from a depth-1 fetch:

| Action | Tag | Commit | Tag type | Commit date |
|---|---|---|---|---|
| googleapis/release-please-action | v4.4.1 | 5c625bfb5d1ff62eadeeb3772007f7f66fdcf071 | lightweight | 2026-03-30 |
| actions/checkout | v4.4.0 | 11d5960a326750d5838078e36cf38b85af677262 | lightweight | (as deploy.yml) |
| astral-sh/setup-uv | v3.2.4 | caf0cab7a618c569241d31dcd442f54681755d39 | lightweight | 2024-11-23 |
| pypa/gh-action-pypi-publish | v1.14.2 | dc37677b2e1c63e2034f94d8a5b11f265b73ba33 | annotated (tag object a892a5a61159132606e93a2fa6f4358831b04d26) | 2026-07-28 |
| docker/setup-buildx-action | v3.12.0 | 8d2750c68a42422c14e847fe6c8ac0403b4cbd6f | lightweight | 2025-12-16 |
| docker/login-action | v3.7.0 | c94ce9fb468520275223c153574b00df6fe4bcc9 | lightweight | 2026-01-27 |
| docker/build-push-action | v6.19.2 | 10e90e3645eae34f1e60eeb005ba3a3d33f178e8 | lightweight | 2026-02-12 |
| actions/setup-python | v5.6.0 | a26af69be951a213d495a4c3e4e4022e16d87065 | lightweight | 2025-04-23 |
| actions/upload-artifact | v7.0.2 | cf430e030ddbb5b0abf93d22962f4752f3646cd9 | lightweight | 2026-10-07 |
| actions/download-artifact | v8.0.2 | 9000827ccba6bdab643e8b6fd33ac0654aef8333 | lightweight | 2026-10-07 |

`pypa/gh-action-pypi-publish` v1.14.3 (commit 7245906f…, 2026-10-20) was the
newest but under two weeks old. Pinned by SHA, it runs the container image
`ghcr.io/pypa/gh-action-pypi-publish:<sha>` (its `create-docker-action.py`
derives the image tag from `github.action_ref`).

Docs lock: `docs/requirements.txt`, 29 packages, 481 hashes. In a clean
Python 3.12 venv, `python -m pip install --require-hashes --only-binary ':all:'
-r docs/requirements.txt` installs, `pip check` reports no broken
requirements, `mkdocs build` builds the site (nav warnings as before).

## Suites

SUITES_PLACEHOLDER
