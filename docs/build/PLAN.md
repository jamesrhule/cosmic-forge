# QCOMPASS MARKET BUILD — MASTER PROMPT (single paste)

You are the build agent for QCompass in the repository `jamesrhule/cosmic-forge`. Your job is to take QCompass from its current state to general availability by executing every ticket in this prompt, in wave order, without asking James anything. James approved this plan by handing it to you; that approval covers every ticket, every merge into `main` that passes its gate, and the freeze move in P1-12. Do not write "waiting for approval" steps, do not pause for confirmation, do not ask questions. Where this prompt leaves a choice open, decide using the rules below and record the decision in the ledger.

This prompt is the plan of record. It supersedes every earlier plan file, prompt set and sprint list in the repository or in `/root/.claude/plans/` (including `the-schematic-a-b-coupling-cozy-hedgehog.md` and the QCompass canonical prompt set v2). Read older files only to learn what already exists on disk. If an older file contradicts this prompt, this prompt wins and you record the conflict in the ledger.

---

## PART 1 — STANDING RULES (apply to every ticket, every commit, every session)

**R1. Plan of record.** In your first action, copy this entire prompt verbatim to `docs/build/PLAN.md` and commit it. Never edit `docs/build/PLAN.md` afterwards. Ticket IDs, wave order, gates and done-when criteria come only from it. Never renumber, merge, split or skip a ticket.

**R2. Nothing is dropped.** Every capability in Part 7 must exist and work at the end. You may replace an implementation only when the replacement does everything the old one did; every replacement and every file deletion gets a ledger entry naming what replaced it. Deleting a capability, a route, a panel, a fixture set, a provider adapter, a domain plugin, an audit or a test without a named replacement is forbidden.

**R3. Tests are the definition of done.** A ticket is done only when its done-when check passes and the evidence (command, exit code, summary lines) is written to `docs/build/evidence/<TICKET>.md`. Never mark a ticket done on the strength of code that "should" work.

**R4. Never weaken a test to go green.** Do not delete, skip, mark `xfail`, loosen a tolerance, widen an assertion, lower a coverage floor, add a `filterwarnings` ignore for your own code, or edit a fixture's expected value so a test passes. Allowed: tightening a test, and fixing a test that is provably wrong — the fix must keep or raise coverage and needs a ledger entry quoting the old and new assertion and why the old one was wrong. The single pre-existing `xfail` (V2 η_B in `backend/tests/test_qcompass_adapter.py`) may be removed only by P1-08 passing for real.

**R5. Freeze contract.** `backend/audit/physics/` and `backend/audit/golden.lock` change only through P1-12. The drift-alarm workflow (`ucglef1-drift-alarm.yml`) must stay green on every other PR. Never edit the drift-alarm workflow to make it pass.

**R6. Physics integrity.** No fudge factors, rescaling constants, fitted offsets or hand-tuned couplings to make a benchmark pass. Every physical input comes from the cited paper or from a quantity the pipeline computes. Every number shown to a user as physical is computed by the Python engine; the browser only does monotone display transforms (log, sign, colour lookup). If V2 recovery does not reach 10% honestly, P1-08 stays open with the measured gap and its uncertainty budget recorded, the `xfail` stays, and you continue with every other ticket.

**R7. No fabricated results.** Never hard-code an output, never present synthetic data as a run result, never claim a hardware run that did not happen. Synthetic fixtures carry `"synthetic": true` and the UI labels them. Raw counts, provider job IDs and calibration snapshots are stored for every real QPU result.

**R8. Money caps.** Tests never call paid services live; use recorded cassettes (`vcrpy`/`respx` in Python, MSW or recorded fixtures in TypeScript). Live provider calls run only in jobs marked `live`, only when the relevant secret exists, and only while cumulative spend stays under the env cap `QCOMPASS_MAX_LIVE_SPEND_USD` (default `0`, which means free tiers and free simulators only). The router must refuse any job whose estimate would cross the cap. Model calls in CI use the cheapest model of each provider and a per-run token cap.

**R9. Secrets.** Never commit, print or log a secret. Code reads secrets only from environment variables with the names in Part 6. Add `gitleaks` to CI in W0. If a secret is missing, the code path reports `BLOCKED-ON-JAMES:<SECRET_NAME>` and degrades gracefully; it never crashes the app and never falls back to an insecure default.

**R10. Read before you change; verify before you substitute.** Open and read a file before editing it. Before using or replacing any library, model, tool or service you have not already seen working in this repo, check its official docs or registry page (PyPI, npm, GitHub) for the current API and licence. Never swap a named library for another silently: a substitution needs a ledger entry with the reason and evidence that the original is unusable.

**R11. Licences.** Distributed artefacts (Python packages, the TypeScript SDK, container images, the web bundle) contain only permissive or weak-copyleft code (Apache-2.0, MIT, BSD, MPL-2.0, ISC, PSF). No GPL or AGPL code is linked into them; GPL/AGPL tools may run as separate processes only. Vendored code needs a compatible licence, a pinned commit, and an entry in `NOTICE`. Add a licence gate to CI in W0 (`pip-licenses` and `license-checker` with an allowlist).

**R12. Git discipline.** Work on branches named `build/w<N>-<slug>` cut from the latest `main`. One pull request per wave (more if a wave is large; never mix waves in one PR). Conventional commits with the ticket ID: `feat(P3-02): worker lease loop`. Never force-push or rewrite `main`. Merge a PR only when every required CI check is green and the wave's gate checks (Part 5) pass or are recorded as blocked per R14. Use the GitHub MCP tools for PRs, checks and merges. Delete the two `claude/*` branches only after P0-01 and P0-02 are merged and their content is verified present.

**R13. Scope fences.** Work only in `jamesrhule/cosmic-forge`. Do not transfer the repository, change its settings, touch other repositories, or modify any production database. Supabase migrations are additive, idempotent and paired with a down migration. Never drop a table or column that holds user data; deprecate it instead.

**R14. Blocked work never stops the build.** If a ticket needs something only James can supply (a secret, an account, a legal sign-off, a customer), build everything that does not need it, write the tests against cassettes or local services, mark the ticket `BLOCKED-ON-JAMES:<what>` in `docs/build/PROGRESS.md`, and continue with the next ticket. If the sandbox lacks network access to a registry or service, implement the work, add the CI job that verifies it, mark it `CI-PENDING`, and confirm it once CI runs. A gate whose only unmet checks are `BLOCKED-ON-JAMES` items counts as passed for moving to the next wave; the blocked checks stay listed until they clear.

**R15. Progress and resume.** After every ticket, update `docs/build/PROGRESS.md` (ticket, status `DONE | IN-PROGRESS | CI-PENDING | BLOCKED-ON-JAMES:<x> | OPEN-WITH-GAP`, evidence path, next ticket) and append decisions, substitutions, conflicts and corrected tests to `docs/build/LEDGER.md`. Commit both. At the start of any session, after any context compaction, or when told "continue", first read `docs/build/PLAN.md`, `docs/build/PROGRESS.md` and `docs/build/LEDGER.md`, then resume at the first ticket that is not `DONE`. Never redo a `DONE` ticket unless a later check proves it broken.

**R16. Independent review at every gate.** Before merging a wave, start a review subagent with a fresh context. Give it the wave's gate checklist (Part 5), the ticket list and the PR diff, and tell it to verify each claim against the repository and test output and to report anything claimed but not true, any weakened test, any dropped capability and any secret. Fix every finding before merging. For W1 and W3 also run a security-review subagent over auth, the API and the sandbox.

**R17. Determinism and pinning.** Pin dependency versions; commit `uv.lock` and `bun.lock`; seed every stochastic test; record package versions in each evidence file.

**R18. Honest product.** The gravity learned-Hamiltonian guard must keep blocking render and merge when a warning is missing. `model_domain` badges and provenance panels stay on every result. A domain is described as delivered in the UI, docs and marketing pages only after the verdict pipeline marks it `DELIVERED`.

**R19. Cosmology regression guard.** Until P4-03 intentionally changes visuals, the cosmology workbench and its six-panel visualizer must render byte-identically (Playwright screenshots on Chromium, Firefox, WebKit). Screenshot baselines change only in the ticket that intends the change, with the reason in the ledger.

**R20. One shape per concern.** Do not create a second implementation of something that exists (a second router, a second auth system, a second job queue, a second fixture loader). Extend the existing one.

---

## PART 2 — FIRST ACTIONS (do these before any ticket)

1. `git fetch origin main claude/ucgle-f1-agent-simulator-agRxR claude/provider-adapters-routing-33xCz` with enough depth to merge (`--depth=1000` or unshallow if allowed).
2. Create `build/w0-consolidate` from `origin/main`.
3. Write `docs/build/PLAN.md` (this prompt verbatim), `docs/build/PROGRESS.md` (every ticket listed with status `OPEN`), `docs/build/LEDGER.md` (empty sections: Decisions, Substitutions, Conflicts, Corrected tests, Removals with replacement), `docs/build/evidence/` (empty). Commit: `chore(build): plan of record`.
4. Record a baseline in `docs/build/evidence/BASELINE.md`: on each of the three branches run the Python suites and the frontend install, build, typecheck, Vitest and lint, and record the results. Expected (verified 30 Oct 2026, for orientation; re-measure, do not trust):
   - Packages on the agent branch: 266 passed, 1 failed (`test_prompt9_v2.py::test_list_domains_has_eight_real_domains`, fails when the backend's cosmology plugin is not installed), 7 skipped.
   - Backend on the agent branch: 133 passed, 6 failed (deprecated `datetime.utcnow()` raised as error under `filterwarnings = ["error"]`; two tests shelling out to bare `python`; the A7 domain-list test needing every plugin installed), 3 skipped, 1 xfailed; the suite also needs `asyncio_default_fixture_loop_scope` set to start under current pytest-asyncio.
   - Frontend on main: `npm ci` fails (stale `package-lock.json`, zod 3 vs zod 4 peer conflict via `@tanstack/zod-adapter`); with `npm install --legacy-peer-deps` the build succeeds; Vitest 52 passed with one file failing to load (`@testing-library/dom` missing); `tsc --noEmit` has 1 error (`src/routes/pricing.tsx` `<Link to="/login">` missing required `search`); ESLint 691 errors and 13 warnings, 687 auto-fixable.

---

## PART 3 — VERIFIED STARTING STATE (for orientation; re-verify)

- `main`: built by Lovable, 377 commits after the branch point `876bb48`, last commit 21 June 2026. TanStack Start on Cloudflare Workers (`wrangler.jsonc`), Supabase (auth, `tenants`, `tenant_members`, `user_roles`, `profiles`, `runs`, `run_results`, `audit_reports`, `viz_timelines`, `tool_call_audit`, `jobs`, `api_rate_limit`, `system_incidents`; functions `claim_next_job`, `complete_job`, `check_rate_limit`, `claim_admin`, `has_role`, `is_tenant_member`, `tenant_role`, `ensure_personal_tenant`, `prune_old_audit_rows`; storage buckets for timelines and artefacts). Eight domain plugins under `src/lib/domains`, generic routes `src/routes/domains/$domain/{configurator,runs,runs.$id,research,visualizer,visualizer.$id}.tsx`, services under `src/services/qcompass/`, `admin.verdict`, `pricing`, `status`, `qa`, `login`, `reset-password`, `auth.callback`, HEP and nuclear observables tables, gravity provenance guard, literature compare sheet, locales `en` and `es`, 17 feature flags in `src/config/features.ts`, `docs/{audit.md,wcag-audit.md,architecture/gpu-scaling.md,ops/dr-runbook.md,frontend/qcompass-gap-audit.md,qa/*}`, `e2e/smoke.spec.ts` only. Per-domain visualizer panels are "coming online" cards. All data comes from fixtures unless `VITE_API_URL` is set.
- `claude/ucgle-f1-agent-simulator-agRxR` (31 commits not on main): `backend/src/ucgle_f1` (M1–M8, adapters), `backend/src/cosmic_forge_viz`, `backend/audit` (S1–S15, A1–A9, `golden.lock` with `physics_dir_hash`), `packages/` (qcompass-core, qcompass-router, qcompass-bench, qfull-chemistry, qfull-condmat, qfull-hep, qfull-nuclear, qfull-amo, qfull-gravity, qfull-statmech, qcompass meta-package, ts/qcompass-frontend-sdk), root `pyproject.toml` uv workspace, `Taskfile.yml`, `.pre-commit-config.yaml`, workflows `ci.yml`, `ucglef1-drift-alarm.yml`, `phase3-verdict.yml`, `release-please.yml`, `docker/Dockerfile.{cpu,cuda12}`, `mkdocs.yml`, `docs/qcompass/`, `acceptance/`, 19 domain visualizer panels in `src/components/visualizer/panels/`, `src/routes/domains/chemistry/*`, `e2e/{playwright.config.ts,cosmology-byte-identity.spec.ts,chemistry-h2-flow.spec.ts}`.
- `claude/provider-adapters-routing-33xCz` (2 commits not on main): router 6B with tests in `packages/qcompass-router/tests/audit/`, `transforms/_common.py`, CSV calibration seeds (`ibm_torino`, `ionq_forte`, `iqm_garnet`), `tests/test_pricing_stub.py`, an earlier six-frame `cosmic_forge_viz`, route `src/routes/visualizer.$domain.$id.tsx`, 14 domain panels, `src/services/visualizerStream.ts`, `src/types/manifest.ts`, flag `liveDomainStream`.
- Known defects to fix inside the tickets that own them: M3 couplings are schematic lambdas in `m7_infer/pipeline.py`; M4 uses `a(τ)=1/|τ|` and a zero adiabatic subtraction; M5 uses the analytic 28/79 fallback; M6 uses `_K_TO_HZ = 1e-19`; `_budget_total` uses fixed constants; η_B returns NaN through the 0.5% gate; every cloud provider `submit()` raises `NotImplementedError`; qcompass domain runs execute inside the HTTP request and persist only a status sidecar; the domain visualization endpoint calls `bake_synthetic`; the run registry is in memory; `RunRegistry._drive` emits progress before computing; model install is a simulated download; API tokens are stored in plain text in SQLite; CORS is `*`; anonymous mode is enabled by `QCOMPASS_DEV_ALLOW_ANONYMOUS=1`; the meta-package requires `qcompass-bench>=0.2` while bench is 0.1.0; no `uv.lock`; tag `ucglef1-v1.0.0` was never pushed; main's services call eight endpoints the backend lacks.

---

## PART 4 — TARGET ARCHITECTURE (fixed decisions; do not re-decide)

| Layer | Decision |
| --- | --- |
| Workbench | Main's TanStack Start app on Cloudflare Workers stays the frontend. Do not rebuild it; extend it. |
| Identity | Supabase Auth with main's tenants, roles and first-admin claim. The FastAPI compute API verifies Supabase JWTs (JWKS) on REST, SSE and WebSocket. The backend's bearer tokens remain as API keys for SDK and MCP use, stored as SHA-256 hashes with a short visible prefix, with scopes and expiry. Login-Process is added as an extra OIDC sign-in provider (P8-04). |
| Database | One Supabase Postgres. Every backend SQLite store (auth tokens and budgets, scans, calibration history, pricing cache and free-tier ledger, agent memory, bench leaderboard, run registry) moves into Supabase migrations with tenant row-level security. Python accesses it through SQLAlchemy 2 / SQLModel with a connection URL from `DATABASE_URL`; tests use a Postgres service container. |
| Jobs | Main's `public.jobs` table with `claim_next_job` / `complete_job` is the only queue. No Redis, Valkey, Dramatiq or Celery. Compute classes: `cpu`, `gpu_small`, `gpu_large`, `qpu`, `edge`. |
| Storage | Supabase Storage buckets `run-artifacts` and `viz-timelines`. Timelines are Zarr v3, read in the browser with `zarrita`. Provenance sidecars become rows plus objects. |
| Compute | One worker image (`docker/Dockerfile.cpu`, `docker/Dockerfile.cuda12`), compute class chosen by `--classes`. Deployed to Google Cloud Run (CPU scaling from zero; L4 GPU) by GitHub Actions with Workload Identity Federation. Deployment is code (workflows plus service YAML); it runs when the secrets exist. |
| Compute API | The existing FastAPI app in `backend/src/ucgle_f1/m8_agent/server.py` with `qcompass_routes.py` and the visualizer routes, on Cloud Run. It never runs a simulation inside a request: it validates, enqueues, and returns `202` with a run ID. |
| Quantum | `qpu`-class workers call `qcompass-router`, submit, poll, fetch raw results, store them, and reconcile cost. Tenants may store their own provider keys in Supabase Vault; PHC house keys from env cover free tiers. |
| Agent models | Anthropic API is the default for the hosted product; OpenAI, Ollama, vLLM and llama.cpp remain selectable; tenants may supply their own keys. |
| Contracts | FastAPI's OpenAPI schema is the contract. Generate the TypeScript SDK and frontend service types from it (`openapi-typescript`), replacing hand-written mirrors; a contract test fails CI on drift. Every JSDoc `@endpoint` in `src/services/qcompass/*.ts` must match a real route. |
| Observability | OpenTelemetry traces and Prometheus metrics from API and workers (`OTEL_EXPORTER_OTLP_ENDPOINT`); `system_incidents` feeds the status page. |
| Languages | Python 3.12 (3.13 allowed), Node 22, bun for the frontend, uv for Python. |
| Repository layout | Keep the existing layout (`backend/`, `packages/`, `packages/ts/`, `src/`, `public/`, `supabase/`, `e2e/`, `docs/`). Add `workers/` for the worker entrypoint and `deploy/` for Cloud Run service definitions. |

---

## PART 5 — WAVES, TICKETS AND GATES (execute in this order)

A wave starts only after the previous wave's PR is merged with its gate passed (R14 governs blocked checks). Within a wave, run independent lanes in parallel with subagents where useful; each subagent receives Part 1 verbatim plus its tickets.

### WAVE 0 — Consolidate the three code lines

**P0-01 — Merge the agent branch into main.** Merge `claude/ucgle-f1-agent-simulator-agRxR` into `build/w0-consolidate`. Resolution rules: main's generic `src/routes/domains/$domain/*` routes, rjsf manifest forms, eight-plugin registry and `register-all.ts` win; the branch's `src/routes/domains/chemistry/*` pages, energy-comparison card and provenance cards move into main's chemistry Result component (`src/components/results/...`) so their content survives; `src/config/features.ts` takes the union of flags; `public/fixtures/**` keeps main's files and adds branch-only files; backend, packages, docs, workflows, `acceptance/` come from the branch. Write `docs/build/MERGE-MAP.md` listing every conflicted file and its resolution. Done when: every package, backend module, route, panel and fixture from both sides exists; Python suites and the frontend build run; the cosmology screenshots match main's.

**P0-02 — Port the router branch's unique work.** Add from `claude/provider-adapters-routing-33xCz`: `transforms/_common.py` (merge into the agent branch's transforms if it duplicates), the three CSV calibration seeds converted to the agent branch's seed format (keep the CSVs too if anything reads them), `tests/test_pricing_stub.py`, any router test from `tests/audit/` that covers behaviour the in-package audit lacks, the 14 domain panels (keep any panel the agent branch lacks; where both have a panel for the same view, keep the richer one and log it), `visualizerStream.ts`, `types/manifest.ts` (merge with existing types), and the `liveDomainStream` flag. Fold `visualizer.$domain.$id` into main's `domains/$domain/visualizer.$id`. Done when: the union of both router histories passes every router test; every panel from either branch is reachable.

**P0-03 — One JavaScript lockfile.** Keep `bun.lock`; delete `package-lock.json` and `bun.lockb`; update CI and docs to bun. Resolve the zod conflict by upgrading `@tanstack/zod-adapter` to a version that accepts zod 4, or by moving route validation to zod 4's standard-schema support; do not downgrade zod. Add `@testing-library/dom`. Fix the `pricing.tsx` type error by supplying the `/login` route's required search params. Done when: fresh clone → `bun install --frozen-lockfile`, `bun run build`, `bun run test`, `bunx tsc --noEmit` all pass.

**P0-04 — Python hygiene.** Commit `uv.lock`; migrate `[tool.uv] dev-dependencies` to `[dependency-groups]`; set `asyncio_default_fixture_loop_scope = "function"` in every pytest config; replace every `datetime.utcnow()` with `datetime.now(UTC)` across backend and packages; make the two subprocess tests use `sys.executable`; install the backend and all plugins in the package test job so registry tests see every domain; align versions so the meta-package resolves (bench to 0.2.0 or the pin to 0.1 — choose bumping bench, since release-please will manage versions). Done when: `uv sync --all-packages` then every Python suite passes with no failures and no new ignores.

**P0-05 — One CI.** Merge main's `ci.yml` jobs (bun lint, Vitest, build, audit gate, Playwright smoke, Lighthouse) with the branch's Python matrix, boundary guards, drift alarm, verdict and release workflows. Add gitleaks (R9), the licence gate (R11), CodeQL for Python and TypeScript, and dependency review. Run `eslint --fix` and Prettier; fix the remaining non-auto-fixable lint errors by hand. Make every job required on `main`. Done when: all jobs green on the W0 PR.

**P0-06 — The six missing Playwright specs.** Write `e2e/cosmology-regression.spec.ts`, `hep-particle-observables.spec.ts`, `nuclear-observables.spec.ts`, `gravity-provenance-guard.spec.ts` (a fixture with `is_learned_hamiltonian: true` and no warning must refuse to render), `verdict-admin-gate.spec.ts` (non-admin cannot see it), `domain-shell-coming-online.spec.ts`; keep the branch's `cosmology-byte-identity` and `chemistry-h2-flow` specs; one `playwright.config.ts` with Chromium, Firefox, WebKit. Done when: all specs pass on three browsers in CI.

**P0-07 — Tag, keys, scanning.** Push tag `ucglef1-v1.0.0` at the commit recorded in `golden.lock` (if the remote refuses tag pushes, record `BLOCKED-ON-JAMES:tag-push-permission` and continue). Move the Supabase URL and publishable key from the committed `.env` into Vite build variables with a committed `.env.example` containing variable names only; keep the app working locally. Done when: gitleaks is clean and the app builds with variables from the environment.

**Gate 0:** every suite green on the merged main; drift alarm green with the unchanged `physics_dir_hash`; cosmology screenshots unchanged on three browsers; `docs/build/MERGE-MAP.md` accounts for every conflicted file; review subagent (R16) finds no dropped capability. Then delete the two `claude/*` branches.

### WAVE 1 — Foundations (two lanes: platform and physics)

**Platform lane**

**P3-01 — Postgres for every backend store.** New Supabase migrations for API keys (hashed), tenant budgets and spend, scans, calibration history, pricing cache, free-tier ledgers, agent conversations, hypotheses, plans, patch drafts, tool-call audit links, bench leaderboard, provenance records. Tenant row-level security on every tenant-owned table. Replace the SQLite code paths with SQLAlchemy/SQLModel repositories behind the existing interfaces. Done when: `grep -r sqlite3` finds no use in deployed code paths (tests may use Postgres containers only); all existing tests pass against Postgres.

**P3-02 — Worker service on main's queue.** `workers/` entrypoint: `python -m qcompass_worker --classes cpu,gpu_small`. Loop: `claim_next_job` with lease, heartbeat renewal, run, `complete_job`; janitor that requeues expired leases and dead-letters after `max_attempts` with a `system_incidents` row. Job kinds: `ucglef1.run`, `qcompass.run` (per domain), `scan`, `viz.bake`, `qpu.submit`, `qpu.poll`, `patch.dryrun`. Replace the in-process `RunRegistry._drive` and the synchronous `submit_run` in `qcompass_routes.py` with enqueue + `202`. Progress events come from the modules as they finish (M1…M6 timings), published through Postgres and streamed over SSE/WebSocket; no pre-emitted progress. Done when: a run started, then an API restart, then the run completes and streams its events; 50 concurrent fixture runs complete in CI with two workers.

**P3-03 — Persist results.** Store full `RunResult` payloads in `run_results`, provenance in its table and storage, artefacts in `run-artifacts`; implement `GET /api/qcompass/domains/{domain}/runs` (list, paginated, tenant-scoped) and make `GET …/runs/{id}` return the stored result. Done when: a run reloads byte-identical after restart.

**P3-04 — Auth.** FastAPI dependency verifying Supabase JWTs (JWKS from `SUPABASE_URL`) or hashed API keys; tenant from `X-QCompass-Tenant` checked against `tenant_members`; scopes `read`, `run`, `qpu`, `admin`; same check on the WebSocket handshake. Remove `QCOMPASS_DEV_ALLOW_ANONYMOUS` from production builds (allowed only when `QCOMPASS_ENV=dev`). Extend the A8 audit. Done when: A8 passes, including cross-tenant access attempts returning 404.

**P3-05 — Plan limits and budgets.** Enforce main's `PLAN_LIMITS` (runs per month, concurrent jobs, timeline bytes, GPU access) at enqueue time from the tenant's tier; enforce per-tenant QPU spend budgets in the router; return `429`/`402` with machine-readable codes the frontend displays. Done when: tests cover each limit at and over the boundary.

**P3-06 — API hardening.** CORS allowlist from `QCOMPASS_CORS_ORIGINS`; `/healthz` (process) and `/readyz` (DB, storage, queue); request size limits; one error envelope (`ServiceError` shape already in `domain.py`) on every route; `response_model` on every route; OpenAPI complete. Done when: an OpenAPI lint passes and every route has a typed response.

**P3-07 — Containers and deploy-as-code.** Non-root images, Python 3.12 pinned, `HEALTHCHECK`, labels; `deploy/` Cloud Run service YAML for `qcompass-api` and `qcompass-worker-{cpu,gpu}`; GitHub Actions workflow deploying to a `staging` environment on merge and to `production` on release tags via Workload Identity Federation; Cloudflare Worker deploy for the frontend with `VITE_API_URL` per environment. Done when: images build and pass a container smoke test in CI; deployment runs when secrets exist, otherwise `BLOCKED-ON-JAMES:GCP_*,CLOUDFLARE_*`.

**P4-01 — Close the endpoint contract.** Add the eight endpoints main calls and the backend lacks: run listing (P3-03), `GET/POST /api/qcompass/scans` and `GET /api/qcompass/scans/{id}` (keep `/api/scans` as an alias), `GET /api/qcompass/tenants`, `GET /api/qcompass/verdict` (shape = `public/fixtures/verdict/sample-verdict.yaml`), `GET /api/qcompass/literature/lattice-qcd` and `/nuclear` (shape = the fixtures in `public/fixtures/literature/`). Write `backend/tests/test_frontend_contract.py` that parses every `@endpoint` annotation and asserts a matching route and method, and that every fixture under `public/fixtures/<domain>/runs/*.json` validates against the backend response model. Done when: the contract test passes for every annotation and every fixture.

**P4-02 — Generated SDK and live services.** Generate types from OpenAPI into `packages/ts/qcompass-frontend-sdk`; make every service under `src/services/` use the SDK when `VITE_API_URL` is set and fixtures otherwise; per-environment flags. Done when: against a locally started API and worker, the workbench completes a cosmology run and a chemistry run with zero fixture reads (assert in Playwright by blocking `/fixtures/` requests).

**Physics lane**

**P1-01 — Conformal time in M1.** Add τ(N), a(τ), H(τ), ρ_φ(τ), ρ_r(τ) interpolants (`CubicSpline`) to `m1_background`. Done when: N→τ→N round trip below 1e-10 relative across the run.

**P1-02 — φ(τ) in M2.** New `m2_scalar/trajectory.py`: Klein–Gordon evolution of φ on the M1 background (`solve_ivp`, Radau for the stiff reheating stage) with φ′ and φ″; PyTransport 3.0 adapter as an optional multi-field backend (soft import). Done when: slow-roll analytic limit recovered to 1e-6 for the quadratic potential; tests in `tests/unit/test_m2_trajectory.py`.

**P1-03 — Physical couplings.** New `m7_infer/couplings.py` computing the Chern–Simons term A±(τ) from the coupling f(φ) and φ′ and the Gauss–Bonnet term B±(τ) from ξ(φ), φ′, φ″, H and a, following the mode equation h″± + [k² + A±k + B±]h± = 0 as defined in the original UCGLE-F1 spec (Kawai & Kim, arXiv:1702.07689). Replace the lambdas in `pipeline.py`. Done when: GB→0 decoupling and parity flip ξ→−ξ hold as strict property tests.

**P1-04 — Real adiabatic subtraction in M4.** Implement the adiabatic regularisation of Kamada et al. (arXiv:2007.08029) to fourth adiabatic order; use M1's a(τ); compare `mpmath.quad` (dps 30) with `scipy.integrate.quad` and flag disagreement above 1e-8. Done when: the V4 cross-check (arXiv:2412.09490, Eqs. 7–16) agrees within the run's uncertainty budget on the Kawai–Kim configuration.

**Gate 1:** a run survives an API restart; the workbench on a local stack reads no fixtures; A1–A9 green; contract test green; P1-01 to P1-04 tests green; drift alarm green; review and security-review subagents clean.

### WAVE 2 — Science, routing and visualizer (three lanes)

**Physics lane**

**P1-05 — ULYSSES for real.** Install ULYSSES v2 (`ulysses` on PyPI; verify the package and its `ULSBase` interface first per R10). Make `UCGLE_F1(ulysses.ULSBase)` inject ΔN_L as the B−L initial condition and keep ULYSSES's flavour density matrix, spectator processes and sphaleron decoupling. The analytic 28/79 path stays as a labelled fallback used only when ULYSSES is absent. Done when: ULYSSES and fallback agree within 20% in the degenerate regime and the run records which path produced η_B.

**P1-06 — Real gravitational-wave outputs.** Replace `_K_TO_HZ` with the k→f mapping through T_reh and entropy conservation; Ω_gw(f) and chirality via CosmoGW; LISA and Taiji sensitivity via CosmoGW interferometry; PTA overlap via PTAfast; detector networks via GWBird; tensor and TB/EB spectra via CAMB (classy optional). Verify each package and its licence first (R10, R11); any that cannot be installed is wrapped behind a soft import with a ledger entry and its own CI job. Done when: Ω_gw matches a CosmoGW reference case to 1%.

**P1-07 — Computed uncertainty budget.** Replace the constants in `_budget_total` with per-module estimates: grid convergence (k-grid and τ-grid halving), scheme difference (minimal vs adiabatic), solver tolerance sensitivity, and input propagation by sampling inputs within their stated uncertainties. Keep the refusal above 0.5%. Done when: the budget changes measurably when tolerances change and a test proves the refusal path.

**P1-08 — V2 recovery and strict audits.** Add `backend/audit/physics/fixtures/kawai_kim_v2.yaml` with parameters taken from arXiv:1702.07689 (cite equation and table numbers in the file) and `test_v2_eta_B_within_10_percent` at `precision='high'`; add V3 and V5 (arXiv:2403.09373 ghost bounds) benchmark tests; restore every relaxed S1–S15 assertion to its physics form (find them with `git log -p backend/audit/physics backend/tests/unit/test_pipeline.py` on the agent branch history). These edits land in the P1-12 PR because they touch `backend/audit/physics/`. Done when: V2 is recovered within 10% honestly (R6) and S1–S15 pass strictly; otherwise status `OPEN-WITH-GAP` with the measured gap, and continue.

**P1-09 — Inference live.** Run bilby with dynesty and Cobaya on a three-parameter posterior over the V2 configuration; DVC tracks large outputs (local remote in CI, object storage in deploy). Done when: the posterior reproduces with a fixed seed.

**P1-10 — Physics symbolic verification harness.** `physics/conventions.md` (metric −+++, natural units ℏ=c=k_B=1, index conventions, sign conventions), `physics/sympy_harness/` (dimensional consistency, step-by-step `simplify(lhs−rhs)==0`, limiting-case recovery against locked values), `physics/memo_template.md` with falsifiable predictions for LiteBIRD, LEGEND-1000 and CMB-S4 including unit restoration, `physics/reference_values/locked/`, CI job `physics-verify` (invariants INV-080 to INV-084). Done when: a deliberately wrong sign or unit in a test derivation fails `physics-verify`.

**P1-11 — Jupyter Book.** MyST-NB book reproducing V2 recovery (or its recorded gap), S1–S15, A1–A9, η_B with its budget, and the agent demo notebook. Done when: the book builds in CI from a clean environment.

**P1-12 — Move the freeze.** One PR containing P1-08's audit changes and the new `golden.lock` hash, using `.github/PULL_REQUEST_TEMPLATE/physics-reviewed.md` filled completely (V1–V8 recovery table with before and after, per-check rationale for S1–S15 changes). Apply the `physics-reviewed` label yourself — James authorised this when the V2 recovery tests pass. If P1-08 is `OPEN-WITH-GAP`, the freeze moves only for the strict-assert restorations that pass, and the V2 `xfail` stays. Done when: drift alarm green on the new hash.

**P1-13 — GPU path.** diffrax Kvaerno5 path with `jax_enable_x64` on the `gpu_small` class for `precision='high'`. Done when: a high-precision V2 run completes on one L4 in under 10 minutes (CI-PENDING until GPU deploy exists; prove correctness on CPU JAX in CI).

**Router lane**

**P2-01 — Real provider submission.** Replace every `NotImplementedError` in `packages/qcompass-router/src/qcompass_router/providers/` with submit, poll, cancel and result retrieval: IBM (`qiskit-ibm-runtime` SamplerV2/EstimatorV2), Braket (`AwsQuantumTask`, gate and AHS), Azure Quantum (IonQ and Quantinuum targets), IonQ native API, IQM (`iqm-client`), QuEra via Braket AHS, Pasqal via Pulser cloud. Job handles persist in Postgres. Done when: each adapter runs a Bell-state (or AHS equivalent) job against its provider's simulator through recorded cassettes; live runs execute in the `live` job when keys exist (R8).

**P2-02 — Pricing that matches bills.** Live refresh where providers publish pricing; quarterly seed review task; reconciliation of estimates against billed cost per job; free-tier ledgers per account in Postgres. Done when: reconciliation tests pass on cassettes; live reconciliation `BLOCKED-ON-JAMES` until keys exist.

**P2-03 — Real calibration.** Daily `cpu` job pulling device properties (IBM backend properties, Braket device properties, IQM) into Postgres; QDMI where available; the drift gate reads live history. Done when: drift gate refuses on recorded live data.

**P2-04 — Transforms with real add-ons.** Install `qiskit-addon-aqc-tensor`, `qiskit-addon-mpf`, `qiskit-addon-obp`, `qiskit-addon-cutting`, `qiskit-addon-utils`, `pytket` in the worker image; transform records flow into `ProvenanceRecord.error_mitigation_config`. Done when: measured depth reduction on the bench circuits is recorded and A-router-6 passes with real transforms.

**P2-05 — Fault-tolerant plans.** Azure Resource Estimator through a workspace when keys exist; check licences of QREChem and TFermion (R11) and vendor at pinned commits if permitted, otherwise wrap their published methods; the closed-form path stays as fallback. Done when: FeMoco and Schwinger plans reproduce `PINNED_TEST_VECTORS`.

**P2-06 — Core completion.** HDF5 read/write in M11 (`LatticeGaugeHamiltonian`, `NuclearShellHamiltonian`, LQCD-HDF5); live M12 adapters; block2, quimb and ipie installed in the CPU image and exercised in M13. Done when: M13 references cross-check PySCF on H₂ and LiH.

**Visualizer lane**

**P4-03 — Rich domain views.** Replace every "coming online" card with the merged panels and a real Result component per domain (chemistry, condmat, AMO, HEP, nuclear, gravity, statmech); 3Dmol loaded client-side only via dynamic import inside `ClientOnly`. Done when: no coming-online card remains; Playwright covers each domain's Result and visualizer.

**P4-04 — Visualizer on real runs.** HDF5 writer adapter from `PipelineResult` and domain results (no edits to M1–M6 internals beyond what P1 tickets own); baker reads real run output; Zarr v3 in `viz-timelines`; `zarrita` in the browser; `ACCURACY_CONTRACT` module with `transform_provenance` in every manifest; k-grid downsampling with tachyonic-band pinning; phase boundaries from M1 (ε_H=1, ρ_φ=ρ_r, T≈130 GeV). Remove the call to `bake_synthetic` from the run visualization endpoint (synthetic baking stays for fixtures only). Done when: an accuracy test proves no physical value is computed in the browser and a real run renders.

**P4-05 — Visualizer spec completion.** PLISC detector sensitivity curves from Schmitz (arXiv:2002.04615, Zenodo data) served at `/api/detector_sensitivity/{detector}.csv`; `/api/runs/compare?ids=A,B` with phase alignment and the "sync to phase" UI; live-run subscription with drop-not-block backpressure and a `frames_dropped` metric; golden-image tests (pytest-mpl backend, Playwright frontend); WebSocket end-to-end latency under 150 ms on localhost; 10-minute streaming memory soak without growth; `docs/{accuracy_contract,schema_reference,protocol,novelty_note}.md`. Done when: all of these tests pass in CI.

**Gate 2:** V2 recovered within 10% and the freeze moved (or `OPEN-WITH-GAP` recorded with evidence); every cloud adapter passes its simulator cassette test; real-run visualization renders; `physics-verify` green; review subagent clean.

### WAVE 3 — Private beta

**P2-07 — Chemistry depth.** Real SQD with `qiskit-addon-sqd` on Aer, then IBM; Dice on Linux workers; FeMoco toy and dormant QPE template kept. Done when: H₂ SQD within chemical accuracy (1.6 mHa) of FCI on Aer, and on hardware when keys exist.

**P2-08 — Condensed-matter depth.** tenpy DMRG for Hubbard 4×4; quimb 16-site OTOC (Willow echo); IBM Heron digital run; QuEra Aquila analog run. Done when: OTOC within the bench fixture budget against quimb; hardware runs when keys exist.

**P2-09 — HEP depth.** Check the licence of the Farrell et al. SC-ADAPT-VQE code (PRX Quantum 5, 020315, 2024); vendor at a pinned commit if permitted, otherwise reimplement from the paper; Schwinger chiral condensate on Aer and IonQ; Z_N and SU(2) toys; `particle_obs` with units and uncertainties. Done when: condensate within 5% of the MPS reference on Aer.

**P2-10 — Nuclear depth.** block2 references; 12-qubit noisy Aer reproduction of the 0νββ LNV signature (Chernyshev et al., Nature Communications 2026); IonQ run; heavy- and sterile-neutrino effective Hamiltonians; `model_domain` on every result. Done when: the LNV signature reproduces and the badge test passes.

**P2-11 — AMO depth.** bloqade and Pulser emulators; QuEra Aquila run; netket NQS reference. Done when: blockade ground state matches exact diagonalisation within the fixture budget.

**P2-12 — Gravity and statistical mechanics depth.** Sparse SYK and JT on Aer; IQAE and quantum Metropolis on Qiskit; TFD preparation; the learned-Hamiltonian guard remains a blocking test. Done when: a CI run that deliberately breaks the guard fails.

**P2-13 — Hardware campaigns.** For each domain, three reproducible hardware results, each with a classical-reference hash, raw counts, provider job ID, calibration snapshot and mitigation record, within the spend cap (R8). Done when: verdict criterion 1 is met per domain; otherwise `BLOCKED-ON-JAMES:<provider keys>` per domain.

**P2-14 — Bench live.** MQT Bench, SupermarQ and QED-C runners installed and run nightly; leaderboard in Postgres; public leaderboard page in the workbench. Done when: the nightly report publishes.

**P3-08 — Security.** Bandit, CodeQL, dependency review, gitleaks, SBOM with syft, cosign-signed images; patch dry-runs execute in the `patch.dryrun` job class under gVisor (Cloud Run second-generation sandbox) with no network; OWASP ZAP baseline scan against staging; an automated penetration-test pass. External penetration test is `BLOCKED-ON-JAMES:pentest-vendor`. Done when: no high findings from the automated tools.

**P3-09 — Observability.** OpenTelemetry export from API and workers; dashboards as code; alerts for drift events, budget exhaustion, auth failures, lease timeouts and dead letters; incidents feed `/status`. Done when: a game-day test fires each alert in staging (or in CI against a local collector).

**P3-10 — Backups.** Point-in-time recovery enabled, storage replication job, scripted restore drill following `docs/ops/dr-runbook.md`. Done when: a restore drill on a scratch project completes within RTO 4 h with RPO ≤ 24 h (CI-PENDING until the Supabase project secret exists).

**P4-06 — Account pages.** Tenant picker, API-key management (create, scope, revoke; shown once), provider-key vault (Supabase Vault), usage and budget page. Done when: a new tenant, with its own key, runs a QPU-class job end to end on cassettes.

**P4-07 — Scans.** Parameter scans run as jobs, persist, and drive the Research view's heatmap. Done when: the heatmap renders a live scan.

**P4-08 — Quality gates.** axe accessibility checks in CI, Lighthouse budgets, cross-browser Playwright against staging. Done when: all three are required checks and green.

**P4-09 — French (Canada).** Add `fr-CA` beside `en` and `es`; every string translated; locale switcher. Done when: a test fails on any missing key in any locale.

**P5-01 — Live agent providers.** Streaming tool loop on Anthropic (default), OpenAI, Ollama, vLLM, llama.cpp; nightly live determinism check (A4) on the default model within token caps (R8). Done when: the live smoke passes nightly when the key exists.

**P5-02 — Real model installs.** Ollama pulls and Hugging Face downloads with checksums, disk quotas and resumable progress, enabled for self-hosted deployments; the hosted product uses API models. Done when: install, status, uninstall work end to end against a small model in CI.

**P5-03 — Agent memory in Postgres.** Conversations, hypotheses, plans, approvals and run links persisted; conversation history in the chat drawer. Done when: a conversation reloads with its runs after restart.

**P5-04 — Literature beyond the bibliography.** arXiv API search and retrieval, pgvector index of abstracts, citation integrity (A2) against fetched records. Done when: A2 passes on fetched citations.

**P5-05 — Patch workflow.** `propose_patch` → `dry_run_patch` in the sandbox class → draft pull request through a GitHub App (credentials `BLOCKED-ON-JAMES:GITHUB_APP_*` until created) → human merge only. Never an `apply_patch` tool. Done when: an agent-proposed patch produces a draft PR with its test report in a test repository or via cassette.

**P5-06 — Public MCP server.** Streamable-HTTP MCP endpoint with API-key auth exposing every tool, plus `get_visualization`, `render_visualization`, `get_frame`, `get_comparison_alignment`. Done when: an external MCP client test runs and inspects a run.

**P5-07 — Agent across all domains.** Tools to list domains, fetch schemas, validate manifests, start, stream and compare runs in every domain. Done when: the agent configures and runs a chemistry job and an HEP job in tests.

**Gate 3:** a hardware result in every domain (or `BLOCKED-ON-JAMES` per provider); no high findings from automated security tools; agent live checks pass where keys exist; review and security-review subagents clean.

### WAVE 4 — Public beta

**P6-01 — Releases.** Versions aligned; release-please per package; PyPI trusted publishing for every Python package (`BLOCKED-ON-JAMES:pypi-trusted-publisher` until configured); CPU and CUDA images to GHCR. Done when: `pip install qcompass` from a test index (TestPyPI or a local index in CI) installs every package and `list_domains()` returns all eight domains plus `null`.

**P6-02 — Documentation.** Every `mkdocs.yml` navigation target exists; API reference generated from OpenAPI; a user guide per domain; accuracy contract; protocol; runbooks for the drift alarm, key rotation, calibration bump, incident response and restore. Done when: `mkdocs build --strict` and a link checker pass.

**P6-03 — Verdict live.** Monthly `phase3-verdict` workflow active; the UI and docs describe a domain as delivered only when the verdict says `DELIVERED` (R18); artefacts archived, never deleted. Done when: the first live verdict report is committed.

**P6-04 — Preprint and DOI.** Methods note and preprint in `docs/qcompass/paper/`; Zenodo integration for releases (`BLOCKED-ON-JAMES:zenodo` for the account link). Done when: the paper builds to PDF in CI.

**P6-05 — Service levels.** SLOs of 99.5% in beta and 99.9% at GA, error budgets computed from metrics and shown on `/status`. Done when: the error-budget panel renders from real metrics.

**P6-06 — Licensing.** Root `LICENSE` and per-package licence files consistent with R11 (Apache-2.0 for the SDK, core, router, bench and plugins unless a dependency forces otherwise; record the choice), `NOTICE` for vendored code, licence gate required. Done when: the gate is green.

**P7-01 — Billing.** Stripe Checkout, Customer Portal and webhooks updating the tenant tier; metered QPU pass-through for house-account usage; all in Stripe test mode with keys from env (`BLOCKED-ON-JAMES:STRIPE_*` for live). Done when: a test-mode purchase changes a tenant's limits.

**P7-02 — Plans enforced.** Free, Pro ($29/month), Team ($99/month) and Enterprise exactly as on main's pricing page, enforced by P3-05; tax settings configurable per selling entity. Done when: the pricing page buys a plan in test mode.

**P7-03 — Legal pages.** Draft terms of service, privacy policy (PIPEDA, Quebec Law 25, GDPR), acceptable-use policy and enterprise data-processing agreement as pages; bring-your-own-key is the default QPU model so provider resale terms are respected. Pages ship marked "draft pending counsel review" (`BLOCKED-ON-JAMES:counsel-review`). Done when: pages are reachable and linked from sign-up.

**P7-05 — Support.** Help centre in docs, in-app feedback to a `feedback` table, onboarding tutorial, example gallery with one example per domain. Done when: a Playwright test takes a new user from sign-up to a first result unaided.

**P7-06 — Analytics.** Consent-gated product analytics and an activation funnel (sign-up → first run → first scan → first QPU job). Done when: the funnel populates in staging.

**Gate 4:** `pip install qcompass` works from a test index; paid plans work in Stripe test mode; 30 days inside the beta service level once staging is live (CI-PENDING until deployed); review subagent clean.

### WAVE 5 — General availability and ecosystem

**P7-04 — Enterprise.** SAML/OIDC single sign-on through Supabase, audit-log export, dedicated GPU pool configuration, self-hosted deployment for k3s (Helm chart) with local models. Done when: the Helm chart installs on a kind cluster in CI and passes smoke tests; a customer pilot is `BLOCKED-ON-JAMES:enterprise-customer`.

**P7-07 — Launch sequence.** Private-beta, public-beta and GA flags; invite flow for private beta; launch checklist in `docs/build/GA-CHECKLIST.md` derived from the market-readiness gate below. Done when: every item is checked or listed as blocked.

**P8-01 — Manifest4U materials funnel.** QCompass API client and job templates for the materials-discovery funnel stages S1–S6, using chemistry and condensed-matter runs; contracts versioned in `packages/qcompass-core`. Done when: a candidate material flows S1 to S6 in an integration test with recorded runs.

**P8-02 — Particle-to-product thread.** Versioned event contracts (Protobuf or JSON Schema) for QCompass as the quantum-simulation discipline between the Fundamental Physics Engine and Manifest4U; producer side implemented here; consumer contract tests published as a package. Done when: contract tests pass.

**P8-03 — Distributed compute on phones.** `compute/plans/` YAML schema (plan anatomy per INV-090), coordinator service as the `edge` worker class, signed WASM runtime for compute units, threefold redundancy with ⌈N/2⌉+1 agreement and 1% trusted spot checks (INV-092), static-seed-only inputs and no personal data (INV-093), device limits (opt-in, Wi-Fi, idle and charging, ≤5% battery per unit, ≤2 h per day, throttle above 38 °C; INV-091), fallback to server workers and pause above `max_concurrent_failures` (INV-094), CI gate `distributed-compute-check`. Thresholds for using it: >24 h single-core, >10⁶ tasks, or >10⁹ Monte Carlo samples. Done when: a simulated 10⁶-point sweep plan passes the gate; plans with personal-data fields or redundancy 1 without spot checks are rejected.

**P8-04 — Proxima and PHC identity.** Document and test the MCP endpoint for Proxima agents (`docs/integrations/proxima.md` with a working client example); add Login-Process as an OIDC provider option in Supabase Auth configuration and the sign-in page behind a flag. Proxima-side changes are out of scope for this repository (R13): write them as a handoff file `docs/integrations/proxima-handoff.md`. Done when: an MCP client test using a Proxima-style agent configuration runs a job.

**Market-readiness gate (GA):** Science — V2 within 10% (or published gap), S1–S15 strict, three hardware results per marketed domain, methods note public. Product — no fixture reads in production; every domain shows a real Result and visualizer; agent works in all eight domains. Reliability — 99.9% for 30 days; restore drill inside RTO 4 h, RPO 24 h. Security — no high findings; hashed keys; signed images and SBOM; sandboxed dry-runs. Compliance — legal pages published after counsel review. Commercial — Stripe live, plan limits enforced, tax registration done. Support — help centre, tutorial, gallery, status page, incident process. Accessibility and language — axe and Lighthouse green; `en`, `fr-CA`, `es` complete. Distribution — `pip install qcompass` from PyPI, images on GHCR, docs site live.

---

## PART 6 — SECRETS AND ACCOUNTS (names only; values come from James)

Code reads these environment variables; CI reads them from GitHub Actions secrets; workers from Google Secret Manager; tenant provider keys from Supabase Vault. A missing variable means the dependent step is `BLOCKED-ON-JAMES:<NAME>` (R9, R14).

`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_PROJECT_REF`, `SUPABASE_ACCESS_TOKEN`; `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`; `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`; `IBM_QUANTUM_TOKEN`, `IBM_QUANTUM_INSTANCE`; `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`; `AZURE_QUANTUM_SUBSCRIPTION_ID`, `AZURE_QUANTUM_RESOURCE_GROUP`, `AZURE_QUANTUM_WORKSPACE`, `AZURE_QUANTUM_LOCATION`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`; `IONQ_API_KEY`; `IQM_TOKEN`, `IQM_SERVER_URL`; `PASQAL_PROJECT_ID`, `PASQAL_USERNAME`, `PASQAL_PASSWORD`; `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`; `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_TEAM`; `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`; `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`; `QCOMPASS_ENV`, `QCOMPASS_CORS_ORIGINS`, `QCOMPASS_MAX_LIVE_SPEND_USD`.

Never attempt to create accounts, accept terms of service, transfer the repository, configure PyPI or Zenodo, or sign anything. Those belong to James.

---

## PART 7 — CAPABILITY PRESERVATION CHECKLIST (verified at every gate and at the end)

Every item must exist and pass its tests at the end; the final review subagent checks each one against the repository.

UCGLE-F1: M1 Friedmann background; M2 SymPy→JAX potentials and custom potential parser; M3 chiral modes with Bogoliubov tracking, mpmath escalation and diffrax path; M4 anomaly with adiabatic subtraction and V4 cross-check; M5 ULYSSES bridge with labelled fallback; M6 Ω_gw, chirality, LISA/Taiji, PTA, detector networks, CMB tensors; M7 pipeline, precision ladder, uncertainty budget with refusal, bilby/dynesty and Cobaya inference, Hydra/OmegaConf configs, DVC; S1–S15 with V1–V8 citations and Hypothesis property tests; freeze contract; V2 recovery test; Jupyter Book; physics symbolic verification harness; formula variants F1–F7.

Agent (M8): 24 MCP tools in simulator, research, patch and introspection families with one code path for MCP and `/v1/chat` SSE; system prompt built from live tool specs; OpenAI, Anthropic, Ollama, llama.cpp and vLLM providers; model registry with install, status, uninstall; approval tokens and capability envelope including `precision_override`; conversation memory; tool-call audit; patch proposal with sandboxed dry-run and human-review-only merge (no `apply_patch`); bibliography and citation integrity; determinism; A1–A9 audits; agent demo notebook.

QCompass platform: qcompass-core protocols, manifest, provenance, registry, errors, null domain; M11 FCIDUMP, spin JSON, LQCD-HDF5, LatticeGauge, NuclearShell; M12 Azure QRE, QREChem, TFermion; M13 PySCF, block2, quimb, ipie; cosmology adapter with provenance sidecar; chemistry (H₂, LiH, N₂, FeMoco toy, SQD, Dice, FeMoco FT QPE template, S-chem-1..5); condensed matter (Hubbard, Heisenberg, OTOC, Heron, Aquila, S-cm-1..5); HEP (Schwinger, Z_N, SU(2), particle observables, SC-ADAPT-VQE, Schwinger 3+1D FT template, S-hep-1..6); nuclear (0νββ toy, NCSM ⁴He and ⁶Li, effective Hamiltonians, `model_domain`, S-nuc-1..6); AMO (Rydberg blockade, MIS, adiabatic schedules, bloqade, Pulser, netket, S-amo-1..5); gravity (dense and sparse SYK, JT, learned-Hamiltonian guard, S-grav-1..6); statistical mechanics (IQAE, quantum Metropolis, TFD, S-stat-1..5); router with nine adapters (IBM, Braket, Azure, IonQ, IQM, QuEra, Pasqal, local Aer, local Lightning), pricing engine, free-tier ledger, SSL-pinned refresh, calibration drift gate, transforms (AQC-tensor, MPF, OBP, cutting), fault-tolerant surface-code plans, tenant budget hook, A-router-1..6; bench with 16 manifests, particle suite, MQT Bench, SupermarQ, QED-C runners, leaderboard, secret-scrubbed reports, CLI; phase-3 verdict pipeline with monthly workflow; visualizer backend with per-domain frame schemas for all eight domains, baker, Zarr, msgpack WebSocket, SSE, CLI, F1–F7 active terms, accuracy contract, PLISC curves, A/B alignment, live streaming, golden images; TypeScript SDK; auth with tenants and budgets; Prometheus metrics and OpenTelemetry; meta-package; release-please; CPU and CUDA images; mkdocs; preprint.

Workbench: cosmology Configurator, Control and Research views; potential editor; parameter heatmap; SGWB plot; six-panel F1–F7 visualizer with frame export; chat drawer with tool-call cards and model manager; domain selector and eight domain plugins; six generic domain route templates for seven domains; rjsf manifest forms; Result and visualizer panels for every domain; HEP and nuclear observables tables; literature compare; gravity provenance guard and warning banner; model-domain badges; provenance panel; verdict admin page; Supabase sign-in, email verification, password reset, roles, first-admin claim, tenants; runs, results, timelines and tool-call audit persisted; job queue; rate limiting; pricing page and plan limits; status page and incidents; QA checklist page; `en`, `es`, `fr-CA` locales; metrics tile and trace links; Cloudflare Worker deploy; Lighthouse and WCAG checks; DR runbook; GPU scaling note.

Ecosystem: Manifest4U funnel client; particle-to-product event contracts; distributed phone compute plans, coordinator and CI gate; MCP endpoint for Proxima; Login-Process OIDC option.

---

## PART 8 — FINAL REPORT

When every ticket is `DONE`, `OPEN-WITH-GAP` or blocked, post one message containing: the gate results for W0–W5; counts of tickets by status; the full list of `OPEN-WITH-GAP` tickets with their measured gaps; and one consolidated list of every `BLOCKED-ON-JAMES` item (secret names, accounts, sign-offs), grouped so James can clear them in a single sitting. After James supplies anything on that list, resume per R15 and finish the tickets it unblocks.

Begin now with Part 2.
