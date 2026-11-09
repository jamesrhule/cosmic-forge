# W1 staging lane notes (`build/w1-staging`, JAMES DECISION 20)

Base `8778158` (`build/w1-foundations`). Scope: the staging database job.
`qcompass-staging` (ref `ndvzxqvetwkapbdansyp`, `ca-central-1`) is the
product's one Supabase project. Its migrations are applied by the P3-01
runner, and James's admin user and role are seeded through the same path
with the service-role key, from CI or the deploy job, never by hand.
Evidence: `docs/build/evidence/W1-staging-db.md`.

New files only. `deploy.yml`, `ci.yml`, existing migrations, PLAN, LEDGER
and PROGRESS are untouched.

| File | What it is |
|---|---|
| `.github/workflows/staging-db.yml` | Reusable (`workflow_call`) and dispatchable (`workflow_dispatch`) job in the `staging` environment |
| `backend/src/ucgle_f1/db/staging.py` | CLI: `python -m ucgle_f1.db.staging migrate` and `… seed-admin`; secret checks (R9) and masking |
| `backend/src/ucgle_f1/db/seed_admin.py` | The seed: Supabase Auth Admin API for the user, `public.user_roles` for the role |
| `backend/tests/test_staging_db.py` | 30 tests: seed and CLI against the local Postgres harness, stubbed Auth Admin API |
| `backend/tests/test_staging_db_workflow.py` | 12 tests: parses `staging-db.yml` |

## Decisions

- **How the codebase models "admin" (reused, nothing new).** `public.user_roles (user_id, role public.app_role)`, unique on `(user_id, role)`, from main's first migration `20260424153958`.
  - `public.has_role(uid, 'admin')` reads it, and so do the RLS policies.
  - The frontend's `hasRole()` reads it (`src/lib/auth.tsx`).
  - The verdict API's `require_supabase_admin` reads it (correction 9, `ucgle_f1.m8_agent.supabase_auth`), over PostgREST with the caller's token.
  - The seed inserts `(user_id, 'admin')` with `on conflict (user_id, role) do nothing`, and leaves `granted_by` null: no user granted it, the deploy job did.
  - `claim_admin()` was not used. It is the browser's bootstrap path and needs the user's own verified JWT.
- **The user comes from the Admin API, not SQL.** The calls follow supabase/auth `internal/api/admin.go`, read at master on 2026-11-02 (R10):
  - `GET /auth/v1/admin/users?page=&per_page=&filter=` looks the user up. The match is exact and case-insensitive on the client; `filter` only narrows the list.
  - `POST /auth/v1/admin/users {"email", "email_confirm": true}` creates it. No `password` is sent; Supabase Auth then stores a random password that nobody knows.
  - A 422 `email_exists` (a race, or a filter that missed the user) is answered by a full unfiltered lookup.
  - A user that already exists is reused unchanged, even if it is unconfirmed; the output says so.
- **Key headers.** Supabase's API-key guide (`apps/docs/content/guides/getting-started/api-keys.mdx`, "Known limitations") says: "Send publishable and secret keys on the `apikey` header, not on `Authorization: Bearer`."
  - An `sb_secret_…` key, which is what Decision 20 provides, therefore goes on `apikey` only.
  - A legacy JWT service-role key (`eyJ…`, three segments) also goes on `Authorization: Bearer`, which Supabase Auth needs for those keys.
- **The role is written over `DATABASE_URL`**, the connection the P3-01 runner already holds. No new secret is involved.
  - The insert runs inside a transaction that does `set local role service_role` when the connection's role may assume it (`pg_has_role(current_user, 'service_role', 'MEMBER')`). Otherwise it runs as the connection's own role, the owner that just applied the migrations. The output names the role used.
  - Against the harness, the role used is `service_role`.
  - The user is created in Supabase Auth, but the role row lives in the database that `DATABASE_URL` names. If the two secrets name different projects, the `user_roles → auth.users` foreign key fails. The seed reports "SUPABASE_URL and DATABASE_URL name different projects", exits 1 and writes no role row.
- **The email is committed, not a workflow input.** `seed_admin.ADMIN_EMAIL = "jamesrhule@projecthumancity.com"` (Decision 20).
  - With an input, anyone allowed to dispatch the workflow could pick who becomes admin. With a committed value, that changes only through a reviewed commit.
  - `--email` exists for local use. The workflow doesn't pass it.
- **R9 behaviour.**
  - `migrate` needs `DATABASE_URL`. `seed-admin` needs `DATABASE_URL`, `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
  - A variable that is unset, empty or whitespace counts as missing. An unset environment secret reaches the step as an empty string.
  - For each missing name, the command prints exactly `BLOCKED-ON-JAMES:<NAME>` (one line per missing name). It appends the same lines to `$GITHUB_STEP_SUMMARY`, opens no connection, sends no request, writes nothing and exits 0.
  - `SUPABASE_URL` must be `https://<host>`, with no path. Anything else is refused (exit 1) before any request, so the key never travels over plain HTTP or to a sub-path. The message never contains the value.
- **Masking.** Under Actions (`GITHUB_ACTIONS=true`), each command first emits `::add-mask::` for every value it derives from the secrets:
  - each secret with surrounding whitespace removed;
  - `SUPABASE_URL` without a trailing slash;
  - the `DATABASE_URL` password as written (percent-encoded) and decoded, via `urlsplit` and `psycopg.conninfo`.

  Actions masks only exact secret values, so a decoded password would otherwise show. Error output carries the exception type and message (driver SQLSTATE or host, Auth HTTP status and `error_code`), never a key.
- **The workflow.** It runs on `workflow_call` (the three secrets declared as required, no inputs) and `workflow_dispatch`.
  - `permissions: contents: read` at workflow and job level. The job has `environment: staging` and job-level `concurrency: staging-db` (`cancel-in-progress: false`), so two runs never migrate together.
  - Actions are pinned by SHA, resolved with `git ls-remote` on 2026-11-02:
    - `actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0` (as in deploy.yml), with `persist-credentials: false`;
    - `astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e # v6.8.0` (ci.yml uses `@v6`; v6.8.0 is that line's latest tag), with `enable-cache: false`. Nothing restored from a cache that other workflows can write runs next to the database credentials.
  - `UV_VERSION "0.11.32"` and `PYTHON_VERSION "3.12"` are copied from ci.yml, and a test keeps them equal.
  - The install is `uv sync --frozen --no-dev --package ucgle-f1`: the backend's locked runtime dependencies only, with no dev tools next to the secrets. The two commands use `uv run --no-sync`, so the installed environment is never re-resolved.
  - Secrets appear only as step-level `env` values, `${{ secrets.NAME }}` under the same name: `DATABASE_URL` for the migrate step, the three for the seed step. No `run` script interpolates or names a secret.
- **Environment secrets in a called workflow.** Read 2026-11-02 in github/docs `content/actions/how-tos/reuse-automations/reuse-workflows.md` (docs.github.com itself isn't reachable from this sandbox):
  - "To use an environment secret in a reusable workflow, set `environment` on the job in the reusable workflow. The job that calls the reusable workflow can't use the `environment` keyword."
  - "The caller workflow must still pass the secret. Use `secrets: inherit` or pass the secret by name … You can pass a secret by name even if it only exists in the environment."
  - "If the caller workflow doesn't pass an environment secret, the secret resolves to an empty string in the reusable workflow."

  So `on.workflow_call.secrets` declares exactly the three names with `required: true`. A caller that forgets one fails at once, instead of the job silently reporting BLOCKED-ON-JAMES while the environment has the value. `required` only checks that a secret is passed, not that it has a value, so an empty staging secret still degrades per R9. A `workflow_dispatch` run reads the environment directly. The workflow has no `inputs`.

## For the coordinator: wiring it into deploy.yml's staging path

The one line is `uses: ./.github/workflows/staging-db.yml`, as a job in `deploy.yml`, guarded to the staging target (staging-db.yml always uses the `staging` environment, so it must never run on a production deploy). The secrets are passed by name, not with `inherit`:

```yaml
  staging-db:
    name: staging database (migrations + admin seed)
    if: ${{ (inputs.environment || (startsWith(github.ref, 'refs/tags/') && 'production') || 'staging') == 'staging' }}
    permissions:
      contents: read
    uses: ./.github/workflows/staging-db.yml
    secrets:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
      SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
```

The calling job declares no `environment`; GitHub forbids `environment` on a job that calls a reusable workflow. It passes the names, and the called job, which has `environment: staging`, receives the staging values. Those three lines are job-level `secrets:`, not `env`. deploy.yml's header says "Secrets are passed at step level only", and a call needs this form, so the header needs one sentence about it. `test_no_secret_in_workflow_or_job_env` checks only `env`, so it still passes.

Optionally, `gcp` gains `needs: [staging-db]` with `if: ${{ !cancelled() && … }}` added to its existing guard, so the API is deployed onto a migrated schema. Without `!cancelled()`, the skipped `staging-db` job would skip production's `gcp`.

Two existing deploy.yml tests need a matching change in the same PR, because they assume every job in deploy.yml runs steps and runs for production:

- `backend/tests/test_deploy_config.py::test_deploy_workflow_pins_every_action_and_scopes_the_cloudflare_token` requires every `uses:` line to match `[\w.-]+/[\w./-]+@[0-9a-f]{40} # v\d`. A local reusable workflow (`./.github/workflows/…`) is pinned by the commit that contains it, so the test should accept exactly that form for job-level `uses`. Old: every `uses:` line is SHA-pinned. New: every step-level `uses:` is SHA-pinned, and a job-level `uses:` is `./.github/workflows/<name>.yml`.
- `backend/tests/test_security_gate1_deploy.py::test_production_deploys_only_from_main_or_release_tags` expects every job to run on production deploys. The `staging-db` job is expected to run iff the target is staging.

## BLOCKED-ON-JAMES (staging; from Decision 20)

The `staging` GitHub environment exists, with no protection rules. Its values are pending from James:

- Secrets:
  - `BLOCKED-ON-JAMES:DATABASE_URL`: the session-pooler URI. Migrations and the seed.
  - `BLOCKED-ON-JAMES:SUPABASE_URL`: `https://ndvzxqvetwkapbdansyp.supabase.co`. The seed.
  - `BLOCKED-ON-JAMES:SUPABASE_SERVICE_ROLE_KEY`: the `sb_secret_…` key. The seed.
  - `BLOCKED-ON-JAMES:SUPABASE_PUBLISHABLE_KEY`: the `sb_publishable_…` key. Not used by this job; the API's role lookup (`supabase_auth.current_supabase_user`) needs it.
- Variables:
  - `BLOCKED-ON-JAMES:VITE_SUPABASE_URL`, `BLOCKED-ON-JAMES:VITE_SUPABASE_PUBLISHABLE_KEY` and `BLOCKED-ON-JAMES:VITE_SUPABASE_PROJECT_ID`. The workbench build (deploy.yml `web-check` → `web-build`).

These clear once James has entered the values and `staging-db.yml` has run green. The production ones stay open (Decision 20).

`BLOCKED-ON-JAMES:supabase-auth-urls` waits for the staging frontend URL. No staging frontend URL exists yet: the Worker deploy is itself `BLOCKED-ON-JAMES:CLOUDFLARE_API_TOKEN,CLOUDFLARE_ACCOUNT_ID`, and the `workers.dev` subdomain of James's Cloudflare account is unknown, so no URL is guessed here. When the first staging Worker deploy prints its origin `<O>`, record the exact values for James:

- Site URL: `<O>`.
- Redirect URLs: the paths the app sends Supabase Auth to (`src/lib/auth.tsx`):
  - `<O>/auth/callback` (sign-up confirmation, and Google with `?redirect=…`);
  - `<O>/reset-password` (password reset).

## Notes for later lanes (observed, not changed)

- **First sign-in.** The app has no magic-link or OTP form; `src/lib/auth.tsx` offers password, Google and password reset. The seeded admin has no known password, so its first sign-in on staging is "Forgot password" → the `/reset-password` link → a new password. That needs the Auth URLs above.
- **Google sign-in.** It goes through `@lovable.dev/cloud-auth-js` (`src/integrations/lovable/index.ts`), Lovable Cloud's OAuth broker for the Lovable-managed project. Against `qcompass-staging` it will not produce a valid session until Google is configured in that project's Auth and the frontend calls `supabase.auth.signInWithOAuth` directly. That is out of this lane's scope; Decision 20 keeps main's frontend on the Lovable backend until the staging deploy.
- **First migration run.** The first run against `qcompass-staging` is the first time main's Lovable-generated migrations run on a Supabase project other than Lovable Cloud.
  - `20260426031125` does `create extension if not exists pg_cron with schema extensions`. pg_cron is available on Supabase, so the runner keeps the statement. If the project refuses it, the job fails at that version with the server's message; each migration is its own transaction, so earlier versions stay applied and recorded.
  - The bucket insert in `20260424153958` is `on conflict (id) do nothing`, so the existing `run-artifacts` and `viz-timelines` buckets are fine.
- **Dropped item.** "Rotate the Supabase publishable key" (P0-07) is dropped by Decision 20. That is a LEDGER/PROGRESS change for the coordinator; this lane doesn't edit those files.

## Corrected tests

None. No existing test was changed.
