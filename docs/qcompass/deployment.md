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
| `GCP_SERVICE_ACCOUNT`                        | Service account the workflow impersonates; also the services' runtime account                                                                         |
| `CLOUDFLARE_API_TOKEN`                       | Token with Workers Scripts: Edit on the account                                                                                                       |
| `CLOUDFLARE_ACCOUNT_ID`                      | Cloudflare account that hosts the Worker                                                                                                              |
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
  `SUPABASE_SERVICE_ROLE_KEY` (artefact uploads to `run-artifacts`).
- `GCP_SERVICE_ACCOUNT` needs to push to the repository, deploy Cloud Run
  services, act as itself on them, and read those secrets.
- L4 GPU quota in `GCP_REGION` for `qcompass-worker-gpu`.

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
