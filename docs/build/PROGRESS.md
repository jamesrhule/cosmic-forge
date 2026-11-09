# Build progress

Statuses: DONE | IN-PROGRESS | CI-PENDING | BLOCKED-ON-JAMES:<x> | OPEN-WITH-GAP | OPEN

| Wave | Ticket | Status | Evidence | Notes |
|---|---|---|---|---|
| W0 | P0-01 | DONE | evidence/P0-01.md | three-browser cosmology verified in CI (P0-06, R19 control) |
| W0 | P0-02 | DONE | evidence/P0-02.md | Gate 0 review: 5 drops restored; CI green on PR #3 @ 5afedb5 |
| W0 | P0-03 | DONE | evidence/P0-03.md | fresh clone: frozen install, build, 68 tests, tsc 0 |
| W0 | P0-04 | OPEN-WITH-GAP | evidence/P0-04.md | frozen test_gb_to_zero_decoupling fails (ΔF_GB 5.9e-7) on all baselines; fix owned by P1-03 |
| W0 | P0-05 | DONE | evidence/P0-05.md | all jobs green @ 5afedb5 except dependency review (BLOCKED-ON-JAMES:dependency-graph) |
| W0 | P0-06 | DONE | evidence/P0-06.md, evidence/P0-06-r19-control.md | playwright green on 3 browsers @ 5afedb5; R19 locked |
| W0 | P0-07 | DONE | evidence/P0-07.md | keys moved, R9 degrade, gitleaks clean; tag `ucglef1-v1.0.0` (annotated) at `73ae381` pushed by James's `freeze-tag.yml` (on main since `5da2546`) |
| W1 | P3-01 | DONE | evidence/P3-01.md | backend + package stores on Postgres; no sqlite3 in src (test); DATABASE_URL BLOCKED-ON-JAMES for staging/prod |
| W1 | P3-02 | DONE | evidence/P3-02.md | worker on Postgres queue: lease, heartbeat, janitor, 202 enqueue, streamed module progress; restart-survival + 50 runs on 2 workers tested |
| W1 | P3-03 | DONE | evidence/P3-03.md | results/provenance persisted; byte-identical after restart; artefact upload BLOCKED-ON-JAMES:SUPABASE_SERVICE_ROLE_KEY |
| W1 | P3-04 | DONE | evidence/P3-04.md | JWT/JWKS + hashed API keys, tenant_members, scopes, WS handshake; A8 cross-tenant 404 |
| W1 | P3-05 | DONE | evidence/P3-05.md | PLAN_LIMITS enforced at enqueue (429/402), drift test vs billing.ts, budget hook in API + worker |
| W1 | P3-06 | DONE | evidence/P3-06.md | CORS allowlist, healthz/readyz, size limits, one error envelope, typed OpenAPI |
| W1 | P3-07 | DONE | evidence/P3-07.md | non-root pinned images, HEALTHCHECK, Cloud Run YAML, deploy.yml (WIF + Cloudflare) BLOCKED-ON-JAMES:GCP_*,CLOUDFLARE_* until secrets exist; container smoke in CI; CUDA image lint-only (CI-PENDING) |
| W1 | P4-01 | DONE | evidence/P4-01.md | contract test: 14 @endpoint annotations, 22 fixtures; correction 9 verdict API behind admin role; static verdict 404 |
| W1 | P4-02 | DONE | evidence/P4-02.md | SDK types generated from OpenAPI (CI staleness check); services use SDK when VITE_API_URL set; live Playwright: cosmology + chemistry runs with zero fixture reads (e2e-live job) |
| W1 | P1-01 | DONE | evidence/P1-01.md | N→τ→N <1e-10; drift-catching unit tests |
| W1 | P1-02 | DONE | evidence/P1-02.md | slow-roll limit <1e-6; Radau reheating |
| W1 | P1-03 | DONE | evidence/P1-03.md | Decision 11: physical couplings default; Kawai–Kim natural benchmark (Λ from A_s); A_END_H_END derived; GeV only at the boundary; frozen GB→0 green on default path; known-gap job and --deselect removed |
| W1 | P1-04 | OPEN-WITH-GAP | evidence/P1-04.md | 4th-order adiabatic subtraction (V3 Eq. 3.21 to 1e-9), physical M4 + reheating matching (normalisation 8e-10), mpmath/scipy 1.1e-16. The V4 cross-check as built cannot fail on wrong physics (verifier HIGH); an independent route (V4 Eqs. 12–15 from M6) is owed. η_B refused (UV band; P1-07/P1-08) |
| W2 | P1-05 | OPEN | | |
| W2 | P1-06 | OPEN | | |
| W2 | P1-07 | OPEN | | |
| W2 | P1-08 | OPEN | | |
| W2 | P1-09 | OPEN | | |
| W2 | P1-10 | OPEN | | |
| W2 | P1-11 | OPEN | | |
| W2 | P1-12 | OPEN | | |
| W2 | P1-13 | OPEN | | |
| W2 | P2-01 | OPEN | | |
| W2 | P2-02 | OPEN | | |
| W2 | P2-03 | OPEN | | |
| W2 | P2-04 | OPEN | | |
| W2 | P2-05 | OPEN | | |
| W2 | P2-06 | OPEN | | |
| W2 | P4-03 | OPEN | | |
| W2 | P4-04 | OPEN | | |
| W2 | P4-05 | OPEN | | |
| W3 | P2-07 | OPEN | | |
| W3 | P2-08 | OPEN | | |
| W3 | P2-09 | OPEN | | |
| W3 | P2-10 | OPEN | | |
| W3 | P2-11 | OPEN | | |
| W3 | P2-12 | OPEN | | |
| W3 | P2-13 | OPEN | | |
| W3 | P2-14 | OPEN | | |
| W3 | P3-08 | OPEN | | |
| W3 | P3-09 | OPEN | | |
| W3 | P3-10 | OPEN | | |
| W3 | P4-06 | OPEN | | |
| W3 | P4-07 | OPEN | | |
| W3 | P4-08 | OPEN | | |
| W3 | P4-09 | OPEN | | |
| W3 | P5-01 | OPEN | | |
| W3 | P5-02 | OPEN | | |
| W3 | P5-03 | OPEN | | |
| W3 | P5-04 | OPEN | | |
| W3 | P5-05 | OPEN | | |
| W3 | P5-06 | OPEN | | |
| W3 | P5-07 | OPEN | | |
| W4 | P6-01 | OPEN | | |
| W4 | P6-02 | OPEN | | |
| W4 | P6-03 | OPEN | | |
| W4 | P6-04 | OPEN | | |
| W4 | P6-05 | OPEN | | |
| W4 | P6-06 | OPEN | | |
| W4 | P7-01 | OPEN | | |
| W4 | P7-02 | OPEN | | |
| W4 | P7-03 | OPEN | | |
| W4 | P7-05 | OPEN | | |
| W4 | P7-06 | OPEN | | |
| W5 | P7-04 | OPEN | | |
| W5 | P7-07 | OPEN | | |
| W5 | P8-01 | OPEN | | |
| W5 | P8-02 | OPEN | | |
| W5 | P8-03 | OPEN | | |
| W5 | P8-04 | OPEN | | |

## Gates

| Gate | Status |
|---|---|
| Gate 0 | PASSED, MERGED | PR #3 merged into main @ `710fb1d` (2026-11-02 18:12 UTC, merge commit, decisions 12/18); all 14 required checks green |
| Gate 1 | OPEN |
| Gate 2 | OPEN |
| Gate 3 | OPEN |
| Gate 4 | OPEN |
| Gate 5 | OPEN |

Next ticket: PAUSED 2026-11-09 ~14:40 UTC at James's request, once the merges were done. On resume ("continue" / "Review the chat and continue"), re-read LEDGER Decisions 11–22 first. Decision 22 and the daily 21:30 UTC stop apply.

**Merged state**
- `main` is `5da2546`: W0 plus James's `freeze-tag.yml`. Tag `ucglef1-v1.0.0` exists at `73ae381`.
- PR #5 (`build/w1-foundations`) holds:
  - rounds 2–4;
  - P1-04 (OPEN-WITH-GAP);
  - the STAGING lane;
  - R19 rebaseline (a), confirmed green on all three browsers at `6484f70`.
- The four lane merges are `1f67aab`, `c8303ad`, `c90389b` and `4c77f1c`. Local checks before pushing:
  - gitleaks, SDK types, lock, `check_r19`, tsc, prettier and vitest (305) pass, and lint has 0 errors;
  - the adapter tests pass;
  - nothing frozen changed.
- CI on the pushed head is the authority; check it first on resume.

**Resume steps, in order**
1. Confirm CI is green on the PR #5 head. Fix anything red.
2. Number and ledger the Decision-by-build proposals from 7 upward (R4-API 7, R4-FEOPS 8, P1-04's). The lane notes are named in LEDGER "[W1 merges, 2026-11-09]".
3. Round 5 (fix lanes, each with a verifier):
   - **(a) P1-04 physics.**
     - An independent V4 cross-check (ΔQ_A from M6's Ω_gw^± and χ(q), V4 Eqs. 12–15) that can fail on wrong physics.
     - Honest S5/S6 semantics; correct the snapshot if they change.
     - A `uv_band_sensitivity` robust to sign changes.
     - The physical.py docstring NIT, and the P1-04 evidence measured with a committed script.
   - **(b) Caps.**
     - The R4-API MEDIUM: Float cos/log floors are unsound under sympy reductions.
     - The R4-1 and R4-2 partial items, and the sin/cos digits-floor LOW.
     - The R4-FEOPS NITs: linter shape divergences, and the preview NaN for empty fields.
   - **(c) Staging and ops.**
     - STAGING MEDIUMs: libpq-consistent masking, and a failure-path leak test.
     - STAGING LOWs: `https_base` port validation, the different-projects check before creating the user, and the lane-notes wording.
     - Add the `staging-db` job to `deploy.yml`, per the STAGING lane notes (two deploy tests need adjusting).
     - In `test_staging_db.py`, build the fake legacy JWT at runtime.
     - W0-FIX3's LOW: 404 responses get no security headers. Also the `build:dev` framing NIT.
     - DB3 LOWs:
       - an API-origin backfill that trusts jobs rows clients inserted before the fix;
       - secrets in string values in `agent_tool_calls`;
       - the dev-guard migration-order NIT;
       - JWKS treating 408/429 as "keys gone";
       - the `Plan.path` comment.
     - A BLOCKED-ON-JAMES entry for staging environment protection (deployment branches), a setting.
4. Final Gate 1 verification on the merged head, with CI green: the R16 review, a security review (auth, API, sandbox), a physics review and a critic. Fix what they find, then close Gate 1. Gate 1 can pass with P1-04 OPEN-WITH-GAP only if its tests are green and the gap is recorded (R14). Then merge PR #5 with a merge commit and record `BLOCKED-ON-JAMES:branch-protection-w1`.
5. W2 per PLAN.

## Gate 0 status (W0 PR #3, head 5afedb5)
- [x] MERGE-MAP accounts for every conflicted file (50/50).
- [x] R16 review: no dropped capability. The first pass found 5 drops (A–E), all restored with tests; a re-check found 1 incomplete (E, aqc_tensor), now fixed (LEDGER "[Gate 0 review]").
- [x] Physics freeze: `physics_dir_hash` reproduces as `42805c73…92dd`; `audit/physics` and `golden.lock` are byte-identical to the agent branch. The drift-alarm workflow differs only by the two lines correction 10 authorised.
- [x] Every suite green in CI @ 5afedb5 (run 41216919685), except the one exempt `test_gb_to_zero_decoupling` (correction 1, P1-03).
- [x] Drift alarm green: run 41216310823 (success at 324eb4e); deliberate one-byte drift fails it (run 41216312782). Correction 10; evidence/P0-07.md.
- [x] Cosmology screenshots on three browsers: CI-browser baselines reviewed and locked (R19.sha256); playwright green on chromium/firefox/webkit @ 5afedb5; R19 control vs main in evidence/P0-06-r19-control.md (8/9 pass at 0.001; webkit `/` differs by 1px height plus anti-aliasing, ratio 5.12e-4, no cosmology change).
- [ ] Delete `claude/*` branches: after the W0 merge (R12). Remote branch deletion is refused by the session proxy → BLOCKED-ON-JAMES:branch-delete-permission.
- Also blocked on James (not Gate 0 conditions): tag push (`ucglef1-v1.0.0` at 73ae381), Dependency graph setting (dependency review job), required status checks on `main`, Supabase publishable key rotation.

## BLOCKED-ON-JAMES (consolidated; details in LEDGER)

Decision 22 limits this list to four kinds of item:
- secret or key values;
- paid resources;
- account or repository settings only James can click;
- irreversible actions outside the repo.

Every other choice is a Decision-by-build in the LEDGER. Until a value exists, each feature that needs it degrades as R9 says (`BLOCKED-ON-JAMES:<NAME>`, no crash, no insecure default).

### 1. Secret and key values (PLAN Part 6, plus the names Decisions 20 and OPS add)

Each value is entered in the GitHub environment `staging` (now) and in `production` (at GA, with the production Supabase project). Worker values go into GCP Secret Manager too. "Read by" names the code that uses the value today; "—" means a later ticket wires it.

| Name | Where the value comes from | Read by |
|---|---|---|
| `DATABASE_URL` | Supabase → project `qcompass-staging` → **Connect** → Session pooler URI (with the DB password) | API, worker, package stores, `staging-db.yml` |
| `SUPABASE_URL` | Supabase → Project Settings → **Data API** → Project URL | API (JWKS, verdict), worker (artefacts) |
| `SUPABASE_PUBLISHABLE_KEY` (Part 6 `SUPABASE_ANON_KEY`; Decision 20 names the new-style key) | Supabase → Project Settings → **API Keys** → Publishable key (`sb_publishable_…`) | API verdict routes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → **API Keys** → Secret key (`sb_secret_…`) | worker artefact uploads, admin seed |
| `SUPABASE_PROJECT_REF` | Supabase → Project Settings → General → Reference ID (`ndvzxqvetwkapbdansyp` for staging, per Decision 20) | — (deploy tooling) |
| `SUPABASE_ACCESS_TOKEN` | supabase.com → Account → **Access Tokens** | — (CLI tooling) |
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_SUPABASE_PROJECT_ID` (environment *variables*) | the same three Supabase values as above | frontend build |
| `GCP_PROJECT_ID` | Google Cloud console → project picker → Project ID | deploy |
| `GCP_REGION` | the Cloud Run region chosen for the API and workers (staging's Supabase is `ca-central-1`; the nearest GCP region is `northamerica-northeast1`) | deploy |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | IAM & Admin → **Workload Identity Federation** → the provider's full resource name | deploy |
| `GCP_SERVICE_ACCOUNT` (plus the proposed `GCP_API_SERVICE_ACCOUNT` and `GCP_WORKER_SERVICE_ACCOUNT`, `docs/qcompass/deployment.md`) | IAM & Admin → **Service Accounts** → each account's email | deploy |
| `CLOUDFLARE_API_TOKEN` | dash.cloudflare.com → My Profile → **API Tokens** → "Edit Cloudflare Workers" template | deploy (Workers) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard → Workers & Pages → Account ID (right sidebar) | deploy |
| `QCOMPASS_CORS_ORIGINS` | the staging frontend's URL once the first Worker deploy prints it | API |
| `IBM_QUANTUM_TOKEN`, `IBM_QUANTUM_INSTANCE` | quantum.cloud.ibm.com → API key; Instances → the instance CRN | router (IBM) |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | AWS IAM → Users → Security credentials → access key (Braket policy); region of the chosen Braket devices | router (Braket, QuEra) |
| `AZURE_QUANTUM_SUBSCRIPTION_ID`, `AZURE_QUANTUM_RESOURCE_GROUP`, `AZURE_QUANTUM_WORKSPACE`, `AZURE_QUANTUM_LOCATION` | Azure portal → the Quantum workspace → Overview | router (Azure), M12 QRE |
| `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` | Microsoft Entra ID → App registrations → the app → Overview; Certificates & secrets → client secret | router (Azure) |
| `IONQ_API_KEY` | cloud.ionq.com → Settings → **API Keys** | router (IonQ) |
| `IQM_TOKEN`, `IQM_SERVER_URL` | resonance.meetiqm.com → Account → API tokens; the device's server URL | router (IQM) |
| `PASQAL_PROJECT_ID`, `PASQAL_USERNAME`, `PASQAL_PASSWORD` | portal.pasqal.cloud → Projects → project ID; the Pasqal Cloud login | router (Pasqal) |
| `ANTHROPIC_API_KEY` | Anthropic Console → **API Keys** | agent (default provider, P5-01) |
| `OPENAI_API_KEY` | platform.openai.com → **API keys** | agent (OpenAI provider) |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_TEAM` | dashboard.stripe.com → Developers → API keys; Developers → Webhooks → endpoint → Signing secret; Product catalog → the Pro and Team prices' IDs | — (billing ticket) |
| `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY` | GitHub → Settings → Developer settings → GitHub Apps → the app → App ID; "Generate a private key" | — (patch-proposal PRs) |
| `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS` | the tracing backend's OTLP settings (endpoint URL and auth header) | API, worker telemetry |

These are not secrets; the build sets them:
- `QCOMPASS_ENV` (`staging` / `production`), set in the deploy YAML;
- `SUPABASE_PROJECT_REF` for staging, which is known.

### 2. Paid resources (exact item; James decides the price and spend)

- `QCOMPASS_MAX_LIVE_SPEND_USD`: the USD cap on live QPU spend per period. The live provider paths stay disabled until it is set.
- GCP:
  - L4 GPU quota in `GCP_REGION`;
  - `GPU_MIN_INSTANCES` ≥ 1 for `gpu_*` jobs. Each warm L4 Cloud Run instance bills while idle.
- Quantum provider accounts with billing: IBM Quantum, AWS Braket, Azure Quantum, IonQ, IQM, Pasqal. Each provider's live tests and jobs stay on cassettes until then.
- Stripe products and prices for the Pro and Team plans (`STRIPE_PRICE_*` above).

### 3. Account and repository settings only James can click

- `branch-protection-w1` (record after PR #5 merges): add `playwright (live API · chromium)` and `container images (build · smoke)` to `main`'s required checks.
- `production-environment-protection`: the GitHub `production` environment needs:
  - deployment branches and tags limited to `main` and `qcompass-v*`;
  - a required reviewer with "prevent self-review";
  - Cloudflare and GCP values kept as environment secrets.

  See `docs/qcompass/deployment.md`.
- GCP project setup:
  - an Artifact Registry repo `qcompass`;
  - Secret Manager entries `DATABASE_URL`, `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`;
  - a Workload Identity pool and provider limited to this repository and `deploy.yml`;
  - per-service IAM as in `docs/qcompass/deployment.md`.
- Supabase `qcompass-staging` → Authentication → URL Configuration (`supabase-auth-urls`): the Site URL and redirect URLs. The exact URLs are recorded once the staging frontend URL exists.
- PyPI trusted publishing, the `pypi` GitHub environment and Zenodo (PLAN Part 6: James only).
- Lighthouse CI app token `LHCI_GITHUB_APP_TOKEN` and analytics `VITE_POSTHOG_KEY`/`VITE_POSTHOG_HOST`/`VITE_PLAUSIBLE_DOMAIN`: optional. They come from main and are not in Part 6.

### 4. Irreversible actions outside the repo

- `branch-delete-permission`: delete the `claude/*` branches and the merged W0 branches `build/w0-consolidate`, `build/w0-deps`, `build/w0-npm`, `build/w0-py2` and `build/w0-fix3`. The session's proxy refuses remote branch deletion.

### Reclassified under Decision 22 (now Decision-by-build; LEDGER has each)

- `r19-rebaseline` beyond (a) and (b): Decision-by-build with diff images in evidence.
- Licence rulings `camb` and `qrack-chp`, and `cuda-image-r11`: Decision-by-build 3, 4 and 5.
- Production-data renames (`dev`/UUID slugs, unassigned agent memory): Decision-by-build 6. `qcompass-staging` starts empty, so neither case can arise there. The migrations' NOTICE and report stay.

Cleared:
- `tag-push-permission` (2026-11-09: `ucglef1-v1.0.0` exists at `73ae381`, created by `freeze-tag.yml`)
- `r19-rebaseline-a-access` (2026-11-09: James approved `productionresultssa5.blob.core.windows.net` for the session environment; rebaseline (a) done at `6aaee08`)
- `branch-protection` (2026-11-02: `main` requires 14 checks; LEDGER "[James, 2026-11-02, via Dispatch] Blockers")
- `arxiv-access` (2026-11-02: arxiv.org reachable; P1-04 proceeds)
- `supabase-key-rotation` (Decision 20: that key belongs to the Lovable-managed project, which the product no longer uses)
- `supabase-jwt-signing-keys` (Decision 20: `qcompass-staging` uses an asymmetric ECC P-256 key)
- `dependency-graph` (enabled by 2026-11-02: the dependency review ran on PR #5 job 125319490722 and on PR #3 run 41459720600)
- `drift-alarm-workflow` (correction 10)
- `p1-03-default-coupling` (decision 11)
- `ui-v2-defaults-vs-paper-benchmark` (decision 15: option (a), inside rebaseline (a))
- `cosmology-fixture-synthetic-labels` (decision 16: all three flagged, inside rebaseline (a))
- custom-potential snippet shape (decision 17: canonical sympy expression in φ; `def V(<name>): return <expr>` accepted)
