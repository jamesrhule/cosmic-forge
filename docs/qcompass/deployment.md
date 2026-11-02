# Deployment

QCompass deploys as code (P3-07): container images from `docker/`, Cloud Run
services from `deploy/`, and `.github/workflows/deploy.yml`.

| What                               | Where                                                | Built from                                 |
| ---------------------------------- | ---------------------------------------------------- | ------------------------------------------ |
| Compute API (`qcompass-api`)       | Cloud Run service                                    | `docker/Dockerfile.cpu --target api`       |
| CPU worker (`qcompass-worker-cpu`) | Cloud Run service, CPU always on                     | `docker/Dockerfile.cpu --target worker`    |
| GPU worker (`qcompass-worker-gpu`) | Cloud Run service, one NVIDIA L4                     | `docker/Dockerfile.cuda12 --target worker` |
| Workbench                          | Cloudflare Worker `qcompass-workbench-<environment>` | `bun run build` with `VITE_API_URL` set    |

**When it runs.** Staging on every push to `main`. Production on the
meta-package's release (`qcompass-v*`, called from `release-please.yml`), on a
`qcompass-v*` tag pushed by a person, or by hand (Actions → deploy → Run
workflow). Each job uses the GitHub environment of the same name (`staging`,
`production`).

**Production comes only from `main` or a `qcompass-v*` tag.** Every job in
`deploy.yml` carries the same `if` guard: staging deploys from any ref,
production only when the run's ref is `refs/heads/main` or
`refs/tags/qcompass-v*`, and any other environment name deploys nothing. A
production run dispatched from another branch skips every job
(`backend/tests/test_security_gate1_deploy.py`). The guard cannot stop a
person with write access from pushing a `qcompass-v*` tag on an unreviewed
commit; the environment's protection rules below do that.

**When something is missing.** Every job checks what it needs first. If a
secret, registry or Secret Manager entry is missing, the job writes
`BLOCKED-ON-JAMES:<NAME>` to its summary and finishes successfully without
deploying. Nothing in the workflow creates accounts, projects, registries or
secrets.

## What each environment needs

### GitHub environment secrets (`staging` and `production`)

| Secret                                       | Used for                                                                                                                                              |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GCP_PROJECT_ID`                             | Project that hosts Cloud Run, Artifact Registry and Secret Manager                                                                                    |
| `GCP_REGION`                                 | Cloud Run and Artifact Registry region (an L4 region for the GPU worker)                                                                              |
| `GCP_WORKLOAD_IDENTITY_PROVIDER`             | Workload Identity Federation provider (`projects/<n>/locations/global/workloadIdentityPools/<pool>/providers/<provider>`) trusted for this repository |
| `GCP_SERVICE_ACCOUNT`                        | Service account the workflow impersonates (the deployer). Until the split below exists, also the services' runtime account                            |
| `CLOUDFLARE_API_TOKEN`                       | Token with Workers Scripts: Edit on the account. An environment secret, never a repository secret                                                     |
| `CLOUDFLARE_ACCOUNT_ID`                      | Cloudflare account that hosts the Worker. An environment secret, never a repository secret                                                            |
| `QCOMPASS_CORS_ORIGINS` (secret or variable) | The workbench's origin(s), comma-separated. Unset → the API allows no browser origin (reported as `BLOCKED-ON-JAMES:QCOMPASS_CORS_ORIGINS`)           |

### GitHub environment variables (public values)

| Variable                                                                         | Used for                                                                  |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_SUPABASE_PROJECT_ID` | Workbench sign-in (Supabase Auth)                                         |
| `QCOMPASS_API_URL` (optional)                                                    | API URL for a Worker-only deploy when the GCP job is skipped              |
| `GPU_MIN_INSTANCES` (optional, default `0`)                                      | Minimum GPU workers. At `0` no L4 runs and `gpu_*` jobs wait in the queue |

The remaining frontend flags per environment are committed in
`deploy/web/staging.env` and `deploy/web/production.env`. `VITE_API_URL` is
always the environment's own Cloud Run API URL, read after that deploy. A
workbench is never deployed without an API, because a build without
`VITE_API_URL` serves fixtures (P4-02).

### In the GCP project (per environment)

- Artifact Registry Docker repository named `qcompass` in `GCP_REGION`.
- Google Secret Manager secrets (the services read the `latest` version):
  `DATABASE_URL` (Supabase Postgres connection string), `SUPABASE_URL`,
  `SUPABASE_SERVICE_ROLE_KEY` (artefact uploads to `run-artifacts`; mounted
  on the worker services only, never on the API).
- `GCP_SERVICE_ACCOUNT` needs to push to the repository, deploy Cloud Run
  services, act as itself on them, and read those secrets. This is the
  single-account setup the services use today; the split below replaces it.
- L4 GPU quota in `GCP_REGION` for `qcompass-worker-gpu`.

### Service accounts and per-secret IAM

Today the API, both workers and the deploy workflow share
`GCP_SERVICE_ACCOUNT`. The API is public (`ingress: all`), so any code
execution in it can take that account's token from the metadata server, read
`SUPABASE_SERVICE_ROLE_KEY` and redeploy every service. The fix is three
accounts. Two of them need new secret names, which PLAN Part 6 does not list,
so the split is `BLOCKED-ON-JAMES:GCP_API_SERVICE_ACCOUNT` and
`BLOCKED-ON-JAMES:GCP_WORKER_SERVICE_ACCOUNT`. No code reads either name until
James creates the accounts and approves the names; then `deploy/qcompass-api.yaml`
takes `${GCP_API_SERVICE_ACCOUNT}` and both worker services
`${GCP_WORKER_SERVICE_ACCOUNT}` as `serviceAccountName`, and `deploy.yml`
renders them.

| Account (GitHub environment secret)     | Used as                                            | Roles, each on the narrowest resource                                                                                                                                                                                                                                                                                                                                                    |
| --------------------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GCP_SERVICE_ACCOUNT` (exists)          | Deployer: impersonated by `deploy.yml` through WIF | `roles/artifactregistry.writer` on the `qcompass` repository; `roles/run.developer` on the project (creating a service needs it there); `roles/iam.serviceAccountUser` on the two runtime accounts only; `roles/secretmanager.viewer` on the three secrets (the workflow's `gcloud secrets describe` reads metadata, never a value). No `secretAccessor`. Runtime account of no service. |
| `GCP_API_SERVICE_ACCOUNT` (proposed)    | Runtime of `qcompass-api`                          | `roles/secretmanager.secretAccessor` on `DATABASE_URL` and `SUPABASE_URL` only. Nothing else: no Cloud Run, Artifact Registry or IAM role, no `actAs`.                                                                                                                                                                                                                                   |
| `GCP_WORKER_SERVICE_ACCOUNT` (proposed) | Runtime of `qcompass-worker-cpu` and `-gpu`        | `roles/secretmanager.secretAccessor` on `DATABASE_URL`, `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. Nothing else.                                                                                                                                                                                                                                                                    |

Per secret, bind `roles/secretmanager.secretAccessor` on the secret itself,
never on the project:

| Secret Manager secret       | May read the value          | Must not read it              |
| --------------------------- | --------------------------- | ----------------------------- |
| `DATABASE_URL`              | API runtime, worker runtime | the deployer                  |
| `SUPABASE_URL`              | API runtime, worker runtime | the deployer                  |
| `SUPABASE_SERVICE_ROLE_KEY` | worker runtime only         | the API runtime, the deployer |

The Workload Identity Federation provider should trust only the deploy
workflow of this repository, so no other workflow's OIDC token (for example
`release-please.yml`'s PyPI job, which holds `id-token: write`) can become the
deployer. Its attribute condition, and the `roles/iam.workloadIdentityUser`
binding on `GCP_SERVICE_ACCOUNT`, should require:

```text
assertion.repository == 'jamesrhule/cosmic-forge'
&& assertion.job_workflow_ref.startsWith('jamesrhule/cosmic-forge/.github/workflows/deploy.yml@')
&& (assertion.environment == 'staging'
    || (assertion.environment == 'production'
        && (assertion.ref == 'refs/heads/main' || assertion.ref.startsWith('refs/tags/qcompass-v'))))
```

Nothing in the repository changes GCP IAM; these are James's settings.

### Production environment protection (James)

`BLOCKED-ON-JAMES:production-environment-protection`. Repository settings are
James's (R13). In Settings → Environments → `production`:

- **Deployment branches and tags:** selected branches and tags only, branch
  `main` and tag pattern `qcompass-v*`.
- **Required reviewers:** at least one reviewer (James), with "Prevent
  self-review" on.
- Keep the Cloudflare and GCP secrets as secrets of this environment (and of
  `staging`), never as repository secrets.

Because a `qcompass-v*` tag deploys production, a tag ruleset that lets only
maintainers create or move `qcompass-v*` tags closes the last path.

### Database

Migrations are applied by `supabase db push` (or
`python -m ucgle_f1.db.migrate up`, which the images contain) against the
environment's database. The deploy workflow never migrates a database (R13).

## Runtime configuration

The images run as user `qcompass` (uid 10001), Python 3.12 pinned by exact
patch (3.12.15 on the CPU base, 3.12.13 managed by uv on the CUDA base), with
`QCOMPASS_ENV=production` unless the service sets `staging`. Both images
answer `GET /healthz`: the API's process probe, and the worker's loop probe
(`ucgle_f1.worker.serve_health`, on `$PORT`). The API's `GET /readyz` checks
the database, storage and queue.

Development-only anonymous access needs both `QCOMPASS_ENV=dev` and
`QCOMPASS_DEV_ALLOW_ANONYMOUS=1`. Neither the images nor `deploy/` nor the
workflow sets either, and `backend/tests/test_deploy_config.py` fails if one
does. Only the test harnesses (`scripts/live_stack.py`, the backend tests) use
it.

## How the workbench deploys

The Cloudflare deploy is split so that no code a build dependency runs can
reach the Cloudflare token (SEC-M2):

1. `web-check` (environment job, no checkout) checks that the Cloudflare
   secrets exist, as booleans, and passes the environment's public build
   variables on.
2. `web-build` has no environment, no secret and a read-only token. It checks
   the API URL, checks out, installs with `--frozen-lockfile --ignore-scripts`,
   runs `bun run build` and uploads `dist/` as an artifact.
3. `web` (environment job) checks out afresh, installs the locked wrangler
   with `--ignore-scripts`, downloads exactly that artifact (digest checked),
   refuses a `dist/server/wrangler.json` that sets `build`, `containers` or
   `unsafe` anywhere (each makes wrangler start a process) or a `.env` file in
   the working directory, and only then gives `CLOUDFLARE_API_TOKEN` and
   `CLOUDFLARE_ACCOUNT_ID` to the `wrangler deploy` step.

`setup-bun` runs with `no-cache: true`, so the bun binary is downloaded, never
restored from an Actions cache another workflow can write. No job or workflow
`env` reads a secret; each secret is passed only to the steps that use it.

## Checks in CI

- `images` (ci.yml): builds both CPU images, lints both Dockerfiles, and runs
  `scripts/container_smoke.sh`. The smoke test checks the images run as
  non-root on Python 3.12 with a `/healthz` HEALTHCHECK, applies migrations
  from the API image, checks `/healthz` and `/readyz`, checks that anonymous
  requests get 401, starts the worker, and runs a real H2/STO-3G job through
  both containers.
- `e2e-live` (ci.yml): the workbench built with `VITE_API_URL` against a
  local API and worker completes a cosmology run and a chemistry run with no
  fixture reads (P4-02).
- The CUDA image is linted, not built, in CI (it is large). It is built when
  the deploy workflow runs.

## Run it locally

```bash
docker build -f docker/Dockerfile.cpu --target api    -t qcompass-api .
docker build -f docker/Dockerfile.cpu --target worker -t qcompass-worker .
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres \
  scripts/container_smoke.sh qcompass-api qcompass-worker   # throwaway Postgres only
```
