# W1 ops lane notes (`build/w1-ops`, Gate 1 round 3)

Base `9c6bf4c`. Scope: the deploy and release workflows (c6) and small backend
ops findings (c7). Evidence: `docs/build/evidence/W1-security-round3-ops.md`.

Finding ids used here:

| Id                         | Finding                                                                          |
| -------------------------- | -------------------------------------------------------------------------------- |
| `SEC-M2-residual`          | c6 MEDIUM (deploy.yml:240): the secret-free build can plant code the wrangler step runs |
| `c6-setup-bun-cache`       | c6 LOW: setup-bun restores the bun binary from a shared Actions cache            |
| `c6-gcp-job-env`           | c6 LOW: the gcp job reads secrets in its job-level `env`                         |
| `c6-branch-guard`          | c6 LOW: nothing limits production deploys to main or release tags                |
| `c6-release-please`        | c6 MEDIUM: workflow-wide write permissions, unpinned actions and pip packages    |
| `SEC-L5-residual`          | c6 MEDIUM: the public API runs as the account that deploys and reads every secret |
| `c6-wrangler-devdep`       | c6 NIT: wrangler only reachable through hoisting                                 |
| `c7-jwks-stale-if-error`   | c7 LOW: no stale-if-error, backoff or single flight on the JWKS refresh          |
| `c7-L1-readyz-exact`       | c7 NIT: the DATABASE_URL readiness test matched the marker as a substring        |
| `c7-uv-workspace-members`  | c7 NIT: `packages/*` member glob                                                 |
| `c6-cuda12-residual`       | c6 residual: CI never builds the CUDA image; the licence gate never sees its wheels |

## Decisions

- **[SEC-M2-residual] Three jobs for the workbench.** Reproduced first: with
  wrangler 4.82.2, `wrangler deploy --dry-run --config dist/server/wrangler.json`
  runs a planted `"build": {"command": …}` with `CLOUDFLARE_API_TOKEN` in its
  environment (the new test does this with the real wrangler and gets
  `token=fake-CLOUDFLARE_API_TOKEN` on `9c6bf4c`). The deploy is now:
  - `web-check` (environment job, no checkout, `permissions: {}`): the
    Cloudflare secrets as booleans, and the environment's public build
    variables as job outputs. It exists because GitHub environment variables
    are visible only to jobs that use the environment, and the build job must
    not use it.
  - `web-build` (no `environment`, no `secrets.` reference, `contents: read`):
    API-URL check, checkout without persisted credentials, `setup-bun`
    without cache, `bun install --frozen-lockfile --ignore-scripts`,
    `bun run build`, `actions/upload-artifact` (pinned) of `dist/`. A job with
    no environment cannot receive environment secrets at all, whatever a build
    dependency does on its runner; GitHub's own guidance only promises that
    secrets not referenced by the workflow are scrubbed from runner memory, and
    this workflow references the token.
  - `web` (environment job, `contents: read`): fresh checkout,
    `setup-bun` with `no-cache: true`, `bun install --frozen-lockfile
    --ignore-scripts`, `actions/download-artifact` (pinned) by the artifact id
    the build job output (the action checks its digest), the refusal step, then
    the only step that sees `CLOUDFLARE_API_TOKEN`/`CLOUDFLARE_ACCOUNT_ID`,
    running `./node_modules/.bin/wrangler deploy --config "$WRANGLER_CONFIG"`.
  - Approvals: with required reviewers on `production`, `gcp` and `web-check`
    wait together (one approval) and `web` waits after the build (a second),
    the same count as before (`gcp`, then `web`).
- **[SEC-M2-residual] What the refusal step refuses, and why a deny-list.**
  Read from wrangler 4.82.2's `wrangler-dist/cli.js`: the deploy path starts a
  process for `build.command` (`runCustomBuild`), for `containers` (docker
  image builds) and for `unsafe.capnp` (`capnp compile`). The step refuses any
  of those keys at any depth (so every `env.<name>` too), a missing config and
  a config that is not JSON (jq fails). It also refuses `.env`/`.env.local` in
  the working directory: wrangler's CLI parser loads them into its own
  `process.env` at start-up (`loadDotEnv(getDefaultEnvFiles(...))`), so a
  `CLOUDFLARE_API_BASE_URL` there would send the token elsewhere. An allow-list
  of config keys was rejected: `@cloudflare/vite-plugin` writes about 45
  top-level keys that change between versions, so it would break deploys on
  every plugin upgrade without adding protection for the token.
- **[SEC-M2-residual] Hidden files are uploaded.** The build output contains
  `dist/client/.assetsignore` and `dist/server/.vite/manifest.json`;
  `include-hidden-files: true` hands over the build output as built. Hidden
  files under `dist/` cannot reach wrangler's environment (it loads `.env`
  from the working directory, which the refusal step checks).
- **[c6-branch-guard] One guard on every job.** A job-level `if` cannot read
  `env`, so each job repeats it: staging from any ref; production only when
  `github.ref` is `refs/heads/main` or starts with `refs/tags/qcompass-v`; any
  other environment name runs nothing. GitHub compares strings without case,
  so a `workflow_call` with `Production` is held to the production rule (the
  environment name resolves to the same environment). The release-please call
  runs on `refs/heads/main`, so it passes. The test evaluates each job's `if`
  with a small evaluator of GitHub's expression semantics (`||`/`&&` return
  operands, case-insensitive `==`, `startsWith`).
- **[c6-gcp-job-env] Step-level env.** The gcp job has no `env`; each step gets
  only what it uses. The secrets check now sees booleans (`HAS_GCP_*`), like the
  web check, and the CORS warning a boolean. Image references reach the deploy
  step through `env` instead of `${{ }}` inside the shell text.
- **[c6-release-please] Permissions per job.** Top level `{}`;
  `release-please` contents+pull-requests write; `publish-pypi` contents read
  and id-token write; `publish-docker` contents read and packages write;
  `publish-docs` contents write (`mkdocs gh-deploy` pushes `gh-pages`; nothing
  uses the Pages API, so `pages: write` is gone); `deploy-production`
  unchanged (contents read, id-token write). release-please-action's README
  also lists `issues: write`; `9c6bf4c` never granted it, so it is not added
  here (that would widen the job). If labelling the release PR fails, James can
  add it.
- **[c6-release-please] Pins** (resolved 2026-11-02 with
  `git ls-remote https://github.com/<owner>/<repo>.git 'refs/tags/<tag>*'`,
  annotated tags peeled; the newest patch of the major the workflow already
  used, at least two weeks old):
  `googleapis/release-please-action` v4.4.1 `5c625bfb…`,
  `actions/checkout` v4.4.0 `11d5960a…` (as deploy.yml),
  `astral-sh/setup-uv` v3.2.4 `caf0cab7…`,
  `pypa/gh-action-pypi-publish` v1.14.2 `dc37677b…` (annotated tag object
  `a892a5a6…`; v1.14.3 is 13 days old, so not taken),
  `docker/setup-buildx-action` v3.12.0 `8d2750c6…`,
  `docker/login-action` v3.7.0 `c94ce9fb…`,
  `docker/build-push-action` v6.19.2 `10e90e36…`,
  `actions/setup-python` v5.6.0 `a26af69b…`; and for deploy.yml
  `actions/upload-artifact` v7.0.2 `cf430e03…`,
  `actions/download-artifact` v8.0.2 `9000827c…`. Full SHAs are in the
  workflows and the evidence file.
- **[c6-release-please] Docs tools from a hash lock.** `docs/requirements.in`
  (the same three names) → `docs/requirements.txt` by
  `uv pip compile --generate-hashes --python-version 3.12 --exclude-newer 2026-10-19`
  (29 packages, 481 hashes; mkdocs 1.6.1, mkdocs-material 9.7.7,
  pymdown-extensions 12.3). The job runs
  `python -m pip install --require-hashes --only-binary ':all:' -r docs/requirements.txt`.
  Checked in a clean Python 3.12 venv: installs, `pip check` clean,
  `mkdocs build` builds the site (with the nav warnings it had before).
  `publish-pypi` and `publish-docker` check out with
  `persist-credentials: false`; `publish-docs` keeps the credential because
  `gh-deploy` pushes with it.
- **[c7-jwks-stale-if-error] Semantics.** `_JWKS_TTL_S` 600 s (unchanged),
  `_JWKS_RETRY_MIN_S` 30 s after a failed fetch, `_JWKS_STALE_IF_ERROR_S`
  3600 s past the TTL, `_JWKS_FETCH_WAIT_S` 10 s for a caller waiting on
  another caller's fetch. A TTL refresh that fails serves the cached set while
  it is younger than TTL + 1 h; no fetch for that URL within 30 s of a failure;
  one fetch per URL at a time (callers with a servable set answer from it,
  callers without one wait for that fetch and never fetch again). The forced
  refetch for an unknown `kid` keeps its 30 s rate limit and never settles for
  a stale set (an outage answers 503, as before). The bound limits how long a
  key Supabase removed keeps verifying during an outage to TTL + 1 h. Result in
  the c7 repro (case 5): 50 requests after the TTL with the endpoint down give
  1 fetch and 50 × 200 (9c6bf4c: 50 fetches, 50 × 503); cases 1–4 unchanged.
- **[c7-uv-workspace-members]** `members` lists `backend`, the eleven
  `packages/<name>` directories that hold a `pyproject.toml`, and `workers`.
  `exclude` keeps `.lovable`, `supabase`, `e2e`, `packages/ts`; the
  `packages/__pycache__` entry is moot without the glob and is removed. `uv.lock`
  is unchanged; `uv lock --check` passes.
- **[c6-wrangler-devdep]** `"wrangler": "4.82.2"` in `devDependencies`; bun 1.4.4
  `bun install` added one line to `bun.lock` (the root workspace's
  devDependencies) and changed no package; `bun install --frozen-lockfile`
  passes; `scripts/licence_gate.py npm node_modules`: 813 packages, 0
  violations (wrangler is `MIT OR Apache-2.0`).
- **[all] Workflow validation.** The workflows parse as YAML, pass prettier, and
  the new tests check their structure and evaluate their guards. `actionlint`
  could not be run (downloading it was not permitted here). The workflows only
  run on `main`/tags, so their first real run is CI-PENDING.

## Corrected tests (old → new, with proof)

- **[c7-L1-readyz-exact]** `backend/tests/test_postgres_stores.py::test_missing_database_url_is_503_blocked_on_james`,
  a tightening.
  - Old: `assert "BLOCKED-ON-JAMES:DATABASE_URL" in ready.json()["checks"]["database"]["detail"]`
  - New: `assert ready.json()["checks"]["database"]["detail"] == "BLOCKED-ON-JAMES:DATABASE_URL"`
  - Proof: `health._public_detail` returns only the regex match
    `BLOCKED-ON-JAMES:[A-Z][A-Z0-9_]*`, so the exact value is the contract.
    Mutation on a copy of `9c6bf4c` (`_public_detail` returning the marker plus
    `repr(exc)`): the old assertion passes, the new one fails with
    `'BLOCKED-ON-JAMES:DATABASE_URL (DatabaseNotConfigured(…))'`. Unmutated,
    the new assertion passes on `9c6bf4c` and on this branch.
- No other existing test was changed. `test_deploy_config.py` (including the
  SEC-M2 test `test_deploy_workflow_pins_every_action_and_scopes_the_cloudflare_token`)
  passes unchanged on the new workflows.

## Removals with replacement

- **[SEC-M2-residual]** The `web` job's checkout, install and build steps →
  job `web-build`; the `web` job now only deploys. The API-URL check moved from
  `web`'s check step to `web-build`'s first step, with the same
  `BLOCKED-ON-JAMES:GCP_*(no <env> API URL)` notice.
- **[c6-gcp-job-env]** The gcp job's `env:` block → step-level `env` on the
  steps that use each value; the check step's `${!name}` over values → `HAS_*`
  booleans; `${{ steps.images.outputs.* }}` in the deploy step's shell →
  `IMAGE_*` step env.
- **[c6-release-please]** Workflow-level `permissions` (five write scopes) →
  `permissions: {}` plus per-job permissions; `pip install mkdocs
  mkdocs-material pymdown-extensions` → hash-locked install from
  `docs/requirements.txt`; tag/branch refs → commit SHAs.
- **[c7-uv-workspace-members]** `members = ["backend", "packages/*", "workers"]`
  and the `packages/__pycache__` exclude → the explicit member list.

## Routed to later tickets

- **[c6-cuda12-residual]** No change. CI lints `docker/Dockerfile.cuda12`
  (`docker build --check`, ci.yml `images`) but never builds it or runs its
  `uv sync --extra cuda12`; the deploy workflow is the first place it builds.
  The licence gate syncs `UV_SYNC` without `jax`/`cuda12`, so it never sees
  the 15 packages the extra adds (`jax-cuda12-plugin`, `jax-cuda12-pjrt`
  0.12.0.1 and 13 `nvidia-*-cu12` wheels: cublas, cuda-cccl, cuda-cupti,
  cuda-nvcc, cuda-nvrtc, cuda-runtime, cudnn, cufft, cusolver, cusparse, nccl,
  nvjitlink, nvshmem), whose licences are NVIDIA's own (LEDGER [REV-nit] CUDA
  plugin). Building the image in CI (several GB) or adding a licence-gate run
  over the extra is not trivial and belongs with the image/deploy work after
  Gate 1; whether the NVIDIA licence is acceptable for a distributed image
  under R11 is James's call. `uv python install 3.12.13` downloads outside
  `uv.lock` (checksum-pinned by uv itself), as recorded before.
- **[new, not in this lane's list] mkdocs site loads `polyfill.io`.**
  `mkdocs.yml` `extra_javascript` loads `https://polyfill.io/v3/polyfill.min.js`
  (a domain taken over in the 2024 supply-chain incident) and an unpinned
  `https://cdn.jsdelivr.net/npm/mathjax@3/...` into every page of the published
  docs. Fixing it changes the published site, which this lane was told not to
  do; recommended for the coordinator: drop polyfill.io (MathJax 3 needs no
  ES6 polyfill) and pin MathJax to an exact version with a subresource
  integrity hash.

## BLOCKED-ON-JAMES

- **[c6-branch-guard] `BLOCKED-ON-JAMES:production-environment-protection`.**
  Repository settings (R13). Settings → Environments → `production`:
  deployment branches and tags = selected only, branch `main` and tag pattern
  `qcompass-v*`; required reviewer (James) with "Prevent self-review"; keep
  the Cloudflare and GCP secrets as environment secrets, never repository
  secrets. Optionally a tag ruleset so only maintainers create or move
  `qcompass-v*` tags. Documented in `docs/qcompass/deployment.md`.
- **[SEC-L5-residual] `BLOCKED-ON-JAMES:GCP_API_SERVICE_ACCOUNT` and
  `BLOCKED-ON-JAMES:GCP_WORKER_SERVICE_ACCOUNT`** (proposed names; PLAN Part 6
  lists only `GCP_SERVICE_ACCOUNT`, so no code reads them). IAM split,
  documented in `docs/qcompass/deployment.md`:
  - `GCP_SERVICE_ACCOUNT` = deployer only: `roles/artifactregistry.writer` on
    the `qcompass` repository, `roles/run.developer` on the project,
    `roles/iam.serviceAccountUser` on the two runtime accounts only,
    `roles/secretmanager.viewer` on the three secrets (metadata for the
    workflow's `gcloud secrets describe`); no `secretAccessor`; runtime of no
    service.
  - `GCP_API_SERVICE_ACCOUNT` = `qcompass-api` runtime:
    `roles/secretmanager.secretAccessor` on `DATABASE_URL` and `SUPABASE_URL`
    only; nothing else.
  - `GCP_WORKER_SERVICE_ACCOUNT` = both workers' runtime:
    `roles/secretmanager.secretAccessor` on `DATABASE_URL`, `SUPABASE_URL`,
    `SUPABASE_SERVICE_ROLE_KEY`; nothing else.
  - Per-secret bindings on the secret, never the project. The WIF provider's
    attribute condition and the `workloadIdentityUser` binding should require
    this repository, `job_workflow_ref` = `deploy.yml`, and environment
    `staging`, or `production` from `main`/`qcompass-v*` (exact condition in
    deployment.md).
  - Once James creates the accounts and approves the names:
    `serviceAccountName: ${GCP_API_SERVICE_ACCOUNT}` in
    `deploy/qcompass-api.yaml`, `${GCP_WORKER_SERVICE_ACCOUNT}` in both worker
    YAMLs, both added to the deploy step's `envsubst` list and step env, and
    `test_cloud_run_services_are_production_safe` updated to match. Nothing in
    GCP was changed from here.
- **[c6-release-please]** PyPI trusted publishing for each package, the
  `pypi` GitHub environment, and Zenodo stay James's (PLAN Part 6); nothing
  was configured.
