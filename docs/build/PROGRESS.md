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
| W0 | P0-07 | BLOCKED-ON-JAMES:tag-push-permission | evidence/P0-07.md | keys moved, R9 degrade, gitleaks clean; tag created locally at 73ae381, remote refuses tag push |
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
| W1 | P1-04 | OPEN-WITH-GAP | evidence/P1-04.md | quadrature cross-check only; adiabatic subtraction + V4 need papers: BLOCKED-ON-JAMES:arxiv-access |
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

Next ticket: PAUSED 2026-11-02 19:45 UTC at James's request ("usage close to running out"). On resume ("continue" / "Review the chat and continue"), re-read LEDGER Decisions 11–22 first. Decision 22 and the daily 21:30 UTC stop apply.

**Merged state**
- `main` is `710fb1d`: W0 merged via PR #3 (Decision 18).
- PR #5 targets `main` from `build/w1-foundations` @ `5176169`. All CI is green except `playwright (chromium · firefox · webkit)`, where only the 9 R19 cosmology screenshots fail. Those are rebaseline (a), blocked on `r19-rebaseline-a-access` (section 3 below).
- `playwright (live API · chromium)` passes: Decision 15's default runs on the live stack with zero fixture reads.

**Pushed lane branches, not yet merged into `build/w1-foundations`** (every fix finished; no uncommitted work). Results: `docs/build/evidence/gate1-round2/round4-p104-staging-partial.txt`.

| Branch | Head | State | Verifier | Notes |
|---|---|---|---|---|
| `build/w1-p104` | `7f08c2e` | P1-04 DONE | interrupted at the pause; re-run | V4 cross-check agrees within the run budget at every precision (fast: 1.37e-9 vs budget 2.45e-3). Reheating normalisation residual 8e-10. mpmath vs scipy 1.1e-16. η_B still refused, since n_L is UV-dominated; routed to P1-07/P1-08 in `docs/build/lanes/W1-p104.md`. Based on `build/w1-api3`. |
| `build/w1-staging` | `d76a0e8` | done | finished: 1 closed, 3 partial, 5 new findings | Decision 20's `staging-db.yml` (migrate + admin seed, degrades with BLOCKED-ON-JAMES markers). |
| `build/w1-r4api` | `5d8978e` | 6/6 fixed | interrupted at the pause | Caps regression and bypass, compile capacity and resource limits, scan caps, SSE ids. Seven Decision-by-build proposals in `docs/build/lanes/W1-r4-api.md`. |
| `build/w1-r4feops` | `f5f53f5` | 6/6 fixed | interrupted at the pause | V(ψ) preview, linter/backend parity, strict fixture schema, every package builds a wheel for publish-pypi. Eight Decision-by-build proposals in `docs/build/lanes/W1-r4-feops.md`. |

The staging verifier's partial items and new findings are in the evidence file and need a fix pass.

**Resume steps, in order**
1. Re-run the three interrupted verifiers. Resume workflow wf_989eae87-acd and wf_58b8618b-37c with `resumeFromRunId`: finished fix agents replay from cache.
2. Number and ledger the Decision-by-build proposals from the lane notes (P1-04, R4-API, R4-FEOPS). The next free number is 7, since 2 is reserved for the rebaseline source.
3. Merge the four branches into `build/w1-foundations`, run the full suites and gitleaks, push, and wait for CI.
4. One fix lane for what is left:
   - the staging verifier's partial items and new findings;
   - add the `staging-db` job to `deploy.yml`, as the STAGING lane notes describe (two deploy tests need adjusting);
   - in `backend/tests/test_staging_db.py`, build the fake legacy JWT at runtime instead of as a literal (its old commit is in `.gitleaksignore`);
   - W0-FIX3's LOW: 404 responses carry no security headers;
   - the `build:dev` mode framing NIT;
   - the DB3 residual LOWs:
     - an API-origin backfill that trusts jobs rows clients inserted before the fix;
     - secrets in string values in `agent_tool_calls`;
     - the dev-guard migration-order NIT;
     - JWKS treating 408/429 as "keys gone";
     - the `Plan.path` comment.
5. Rebaseline (a), as soon as `r19-rebaseline-a-access` clears (Decision-by-build 2):
   - take the 9 CI PNGs from the latest CI run's `playwright-report` artifact, or dispatch `e2e-baselines.yml`;
   - commit them and update `R19.sha256`;
   - ledger the old and new hashes, plus one line per visible difference: the D13a badge on `/`, `/visualizer` and `/visualizer/kawai-kim-natural`, and the D16 badges on two `/visualizer` cards.
6. Final Gate 1 verification on the merged head, with CI green: the R16 review, a security review over auth, the API and the sandbox, a physics review, and a critic. Fix what they find, close Gate 1, and merge PR #5 (merge commit). Then record `BLOCKED-ON-JAMES:branch-protection-w1`.
7. W2 per PLAN.

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

- `tag-push-permission`: push tag `ucglef1-v1.0.0` at `73ae38142ae936fa1aeecf1f842dc34d234369d4`. Neither the session's git proxy nor Dispatch can push tags.
- `r19-rebaseline-a-access`: blocks the authorised rebaseline (a), which Decisions 13, 15, 16 and 22 say I run myself. Either fix is enough:
  - **Option (1), network (recommended).** In the cloud environment's settings (environment menu in the session title bar → Edit → Network access), add `productionresultssa5.blob.core.windows.net` (or `*.blob.core.windows.net`) to Allowed domains and keep "Allow package managers" ticked. https://code.claude.com/docs/en/cloud-environments#network-access. CI's 3-browser playwright job already rendered the new screenshots on its own browsers, and they sit in the `playwright-report` artifact of run 41502033954 (head `a835572`). Downloading it hits a 403 at that host, which stores GitHub Actions artifacts. The artifact expires about 2026-11-09 18:40 UTC; any later CI run uploads a fresh one.
  - **Option (2), GitHub.** Give the session's GitHub integration `actions: write`. Dispatching `e2e-baselines.yml` and re-running jobs both answer 403 today.
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
