# Evidence: staging database job (JAMES DECISION 20)

Branch `build/w1-staging`, base `8778158`. Lane notes: `docs/build/lanes/W1-staging.md`.

Status: built and tested locally. The real run against `qcompass-staging` is `BLOCKED-ON-JAMES:DATABASE_URL,SUPABASE_URL,SUPABASE_SERVICE_ROLE_KEY`: the `staging` environment exists, but its values are not entered yet. Nothing here has connected to `qcompass-staging`; this lane has no credentials for it, and Decision 20 forbids applying migrations by hand.

Versions (R17), measured in the worktree's environment:

- uv 0.11.32, Python 3.12.13, PostgreSQL 16.15 (local harness).
- psycopg 3.3.6, httpx 0.28.1, PyYAML 6.0.3, pytest 9.2.0.
- Actions:
  - `actions/checkout@11d5960a326750d5838078e36cf38b85af677262` (v4.4.0)
  - `astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e` (v6.8.0)

  Both were resolved with `git ls-remote --tags` on 2026-11-02 (v6.8.0's tag points at that commit).

## The exact step: how the staging database gets migrated and seeded

1. **James enters the values** under GitHub → Settings → Environments → `staging`.
   - Secrets:
     - `DATABASE_URL`: the session-pooler URI from the Supabase dashboard, Connect → Session pooler, with the database password filled in.
     - `SUPABASE_URL`: `https://ndvzxqvetwkapbdansyp.supabase.co`.
     - `SUPABASE_SERVICE_ROLE_KEY`: the `sb_secret_…` key.
     - `SUPABASE_PUBLISHABLE_KEY`: the `sb_publishable_…` key, for the API. This job doesn't use it.
   - Variables: `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` and `VITE_SUPABASE_PROJECT_ID`, for the workbench build. This job doesn't use them.
2. **Run the job.** GitHub shows "Run workflow" only for a workflow file that is on the default branch. The API/CLI can dispatch it on any ref once it has run at least once (github/docs `events-that-trigger-workflows.md`, `workflow_dispatch`). There are two routes:
   - **After `staging-db.yml` is on `main`:**

     ```
     gh workflow run staging-db.yml --ref main
     gh run watch "$(gh run list --workflow staging-db.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
     ```

     Once the coordinator adds the `uses:` job to deploy.yml (lane notes), every push to `main` also runs it as part of the staging deploy.
   - **Before that (from a branch):** dispatch `deploy.yml`, which is already on `main`, against a branch that carries both `staging-db.yml` and the deploy.yml `uses:` job:

     ```
     gh workflow run deploy.yml --ref <branch> -f environment=staging
     ```

     The other deploy jobs end with their own BLOCKED-ON-JAMES notices until GCP and Cloudflare are set up.

   The job runs `uv sync --frozen --no-dev --package ucgle-f1`, then:
   - `python -m ucgle_f1.db.staging migrate`: the P3-01 runner, `ucgle_f1.db.migrate.apply_migrations`, against `DATABASE_URL`;
   - `python -m ucgle_f1.db.staging seed-admin`: the Admin API with the service-role key, then `public.user_roles` over `DATABASE_URL`.

### What success looks like (job log)

First run, on today's empty database. The `::add-mask::` lines are consumed by the runner and not shown.

```
applied 20260424153958
… one line per file in supabase/migrations (21 today) …
applied 20261102105000
migrations: 21 applied

admin user <uuid>: created (email confirmed: yes)
admin role: granted (public.user_roles, as database role service_role)
```

The role line names `postgres` instead of `service_role` if the pooler's login role can't assume `service_role`. Either way the insert runs over the same `DATABASE_URL`.

Every later run:

```
migrations: 0 applied
admin user <uuid>: already present, unchanged (email confirmed: yes)
admin role: already held, unchanged (public.user_roles, as database role service_role)
```

Checks James can make afterwards, in the Supabase dashboard:

- Authentication → Users lists `jamesrhule@projecthumancity.com`, confirmed.
- In the SQL editor, `select role from public.user_roles where user_id = '<uuid>'` returns `admin` and `viewer`. `viewer` comes from main's `on_auth_user_created` trigger.
- `select count(*) from supabase_migrations.schema_migrations` returns 21.

### What "not yet" looks like

With the secrets still empty, both steps succeed and print only these lines (also written to the job summary):

```
BLOCKED-ON-JAMES:DATABASE_URL
```

```
BLOCKED-ON-JAMES:DATABASE_URL
BLOCKED-ON-JAMES:SUPABASE_URL
BLOCKED-ON-JAMES:SUPABASE_SERVICE_ROLE_KEY
```

### Failure modes (exit 1, red job, nothing printed that is secret)

- **`admin seed failed: … SUPABASE_URL and DATABASE_URL name different projects`.** The user exists in the Auth project, but not in the database's `auth.users`. No role row is written.
- **`admin seed failed: Supabase Auth user lookup failed: HTTP 401 …`.** Wrong or revoked service-role key.
- **`admin seed failed: SUPABASE_URL must be the project's https:// URL …`.** Not `https://<host>`; no request is sent.
- **`migrations failed: <psycopg error>`.** Connection or SQL failure. Each migration is its own transaction, so versions applied before the failure stay applied and recorded, and a rerun resumes at the failed one.

## Commands run in this lane

All commands ran from the worktree, against the backend's local Postgres harness (`ucgle_f1.db.pytest_plugin`, `supabase_shim.sql`), with Supabase Auth replaced by `httpx.MockTransport`. There was no network.

| Command | Exit | Summary |
|---|---|---|
| `cd backend && pytest -q tests/test_staging_db.py tests/test_staging_db_workflow.py` | 0 | `42 passed` (30 + 12) |
| `ruff check` / `mypy` on `ucgle_f1/db/staging.py` and `ucgle_f1/db/seed_admin.py` (+ ruff on both test files) | 0 | `All checks passed!` / `Success: no issues found in 2 source files` |
| `bunx prettier --check .github/workflows/staging-db.yml` | 0 | `All matched files use Prettier code style!` |
| `UV_PROJECT_ENVIRONMENT=<scratch> uv sync --frozen --no-dev --package ucgle-f1`, then `uv run --no-sync python -m ucgle_f1.db.staging migrate` / `seed-admin` with no secrets | 0 / 0 | The workflow's exact install works. It prints `BLOCKED-ON-JAMES:DATABASE_URL`, then the three-line block above. |

### What the tests prove (`backend/tests/test_staging_db.py`)

- **Creates once.**
  - One `POST /auth/v1/admin/users` with exactly `{"email": "jamesrhule@projecthumancity.com", "email_confirm": true}`, so no password is sent.
  - One confirmed `auth.users` row.
  - `user_roles` = `admin` (seed, `granted_by` null) + `viewer` (trigger); `has_role(uid, 'admin')` is true.
  - The `sb_secret` key goes on `apikey` only, never on `Authorization`, and it never appears in the output.
- **Idempotent on rerun.** No POST; one user, one admin row; the output reads "already present, unchanged" / "already held, unchanged".
- **Reuses an existing user unchanged.** A user who signed up, unconfirmed, with the email in upper case: GET only, the user row is unchanged, and the role is granted.
- **Edge cases.**
  - `email_exists` race: a filtered list that misses the user is followed by a 422 on create, then an unfiltered lookup. Nothing is duplicated.
  - Paging through 3 pages.
  - A legacy JWT key goes on `Authorization: Bearer` as well.
- **Refusals.**
  - Different projects: exit 1 with the message, no rows.
  - Auth 401: exit 1 with `HTTP 401 no_authorization`, no key in the output, no rows.
  - Non-https, scheme-less or path-carrying `SUPABASE_URL`: exit 1 before any request, the value never printed.
  - Invalid `--email`: exit 1.
- **Missing secrets (R9).**
  - Each of the three seed secrets is tested unset, empty and whitespace-only: stdout is exactly `BLOCKED-ON-JAMES:<NAME>\n`, exit 0, no HTTP request (any request fails the test), no `psycopg.connect` call, and `auth.users`/`user_roles` stay empty.
  - All three missing gives three lines plus the job-summary block.
  - `migrate` without `DATABASE_URL` gives `BLOCKED-ON-JAMES:DATABASE_URL`, exit 0, and `apply_migrations` is never called.
- **Masking.**
  - With `GITHUB_ACTIONS=true`, `::add-mask::` lines come before any other output. They cover the password as written (`p%40ss%2Fw0rd`) and decoded (`p@ss/w0rd`), and the URL.
  - No later line contains the password. The seed masks the key, the normalised `SUPABASE_URL` and `DATABASE_URL`.
  - Outside Actions, nothing is masked.
- **End to end from an empty database.**
  - A fresh database on the test server; `migrate` applies all 21 files in order and records them in `supabase_migrations.schema_migrations`.
  - A second `migrate` applies 0.
  - `seed-admin` creates the user and grants the role; a second `seed-admin` changes nothing.
  - `staging.apply_migrations is ucgle_f1.db.migrate.apply_migrations` (the P3-01 runner).

### What the workflow test proves (`backend/tests/test_staging_db_workflow.py`)

- **Triggers.** Exactly `workflow_call` and `workflow_dispatch`. `workflow_call` declares exactly the three secrets (`required: true`) and no inputs.
- **Permissions and environment.** `permissions: {contents: read}` at workflow and job level. Every job uses `environment: staging` and the `staging-db` concurrency group (`cancel-in-progress: false`).
- **Secrets.**
  - Every `secrets` string is a step-level `env` value of the form `${{ secrets.NAME }}`, under the same name.
  - The migrate step gets only `DATABASE_URL`; the seed step gets only the three.
  - No `secrets: inherit`. No `run` script interpolates a secret or names `$DATABASE_URL` and the others.
- **Actions.** Every `uses:` is `owner/repo@<40-hex> # vX.Y.Z`. Checkout has `persist-credentials: false`; setup-uv has `enable-cache: false`.
- **Pins and order.**
  - `UV_VERSION`/`PYTHON_VERSION` equal ci.yml's, and setup-uv uses `env.UV_VERSION`.
  - `uv sync --frozen` runs before the migrate step, which runs before the seed step. Both use `uv run --no-sync`.
- **Mutation check.** Each of these edits to the workflow makes the suite fail, and it passes again once restored:
  - a job-level secret;
  - an unpinned checkout;
  - `uv sync` without `--frozen`;
  - `environment: production`;
  - `contents: write`;
  - `echo "$DATABASE_URL"` in a run step.

## Full suites (end of lane)

See the lane's final report for the end-of-lane runs: backend fast, `uv lock --check`, `bun run lint`, `bunx prettier --check .`, `scripts/check_r19.sh` and the physics dirhash. No TypeScript was touched, so `tsc` was not required.
