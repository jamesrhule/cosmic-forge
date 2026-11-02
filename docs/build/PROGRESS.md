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

Next ticket: RESUMED 2026-11-02. On any resume, re-read LEDGER Decisions 11–22 first. Decision 19: no new lanes after 21:30 UTC on 2026-11-02; the cap resets 2026-11-09 11:00 UTC. State:
- [W1-PARAMS] potential-parameter boundary fix is on `build/w1-platform` 9c6bf4c (OPEN-WITH-GAP). e2e-live still fails because the UI's V2 natural default (f ≈ 0.029 M_Pl) doesn't inflate under the physical model. Decision 15 resolves this: the default becomes the paper benchmark in round 3B, joining rebaseline (a). Completed live runs report η_B = NaN until P1-04, or until the PHYS3 Bogoliubov fix changes that.
- Gate 1 verification workflow wf_9b56ec35-e49 finished (12 agents). Raw results: `docs/build/evidence/gate1-round2/` (c1–c4, c5–c7, physics, fresh-eyes, critic). Headlines beyond c1–c4:
  - physics HIGH: `m3_modes/chiral.py` `_bogoliubov` uses i·√(k/2) instead of i·√(2/k). The whole default-path F_GB (0.6727…), the S1 drift (4.0) and the permanent η_B NaN are this artefact; the frozen GB→0 test passes only by its 1e-9 slack.
  - critic BLOCKERs: the Gate 1 candidate was never assembled or run in CI; e2e-live red; SEC findings open; the Bogoliubov bug.
  - c5: the cosmology domain visualizer card crashes in API mode and has no synthetic label; `/visualizer` lists bundled fixtures in API mode.
  - c6: deploy build/deploy split, release-please permissions, per-service service accounts (needs James), branch guard.
- Round 2 done and merged (`f3a1592`; lanes DB 9a6d853 and WORKER a68c87f, both verified; residuals in LEDGER "[Gate 1 round 2 verification]", carried into round 3B). CI on the merged head: all green except the R19 screenshots (rebaseline (a)) and one round-2 test that clashed with the run state machine (fixed in `754eaf8`).
- W0 dependency review: lane W0-DEPS (wf_f6b045c3-c32) fixed it at `4de96fa`. The changes:
  - vLLM, torch and transformers out of the lock (the provider is HTTP-only);
  - cryptography 50.0.2, setuptools 84.2.1, amazon-braket-sdk ≥1.117;
  - virtualenv out (pre-commit runs as a uv tool);
  - GPL code out of every extra: block2, netket/igraph, cobaya/py-bobyqa, PTAfast/healpy, CosmoGW, PyQt5.

  GitHub's compare against main, evaluated exactly as the action does, gives PASS. `build/w0-consolidate` was fast-forwarded to `4de96fa` and merged into W1 at `3d04cfb` (lock regenerated; only W0's version changes). The verifier found more:
  - HIGH: the npm audit gate is a no-op, and `bun.lock` has 4 critical advisories (TanStack Start XSS, seroval) that dependency review can't see.
  - MEDIUM: qbraid-core's commercial licence (R11).
  - LOW: docs accuracy, and the floors are missing from published extras.

  Follow-up workflow wf_46e8f0ea-ea0 runs lanes W0-NPM (`build/w0-npm`) and W0-PY2 (`build/w0-py2`). W0-NPM must keep R19 pixel-identical, or it stops with BLOCKED-ON-JAMES.
- Round 3A done and merged (`7933f55`, `3737f6a`):
  - PHYS3: Bogoliubov extraction fixed (F_GB 0.6727 artefact → 2.8e-17; S1 drift 4.0 → 1.8e-6); η_B refused with a stated reason until P1-04.
  - OPS: deploy split; release-please least privilege and pins; JWKS stale-if-error.
  - The verifier's HIGH (a raw η_B in V2 rows and scan cells) is fixed at `15e4e3c`.
  - The adapter snapshot's F_GB was pinned to 6 significant digits (`b953127`; it varies across CPUs at 4.7e-8).
  - Notes are folded into the LEDGER (`749cb9b`).
- Round 3B workflow wf_ded45d82-a18 running from `15e4e3c`. Lanes, each with a verifier:
  - FE3 (`build/w1-fe3`): Decisions 15–17 UI, API-mode visualizer, refused-η_B display, M6 placeholder label.
  - API3 (`build/w1-api3`): Decision 17 parser, expression caps and submit-time compile bound, validation MEDIUMs, η_B refused until P1-04.
  - DB3 (`build/w1-db3`): an unforgeable API-run marker, slug squatting, redaction, provenance staging, Decision 14 test method.
  - OPS2 (`build/w1-ops2`): wrangler config allowlist, case-sensitive guard, pinned publish, polyfill.io removal, SHA-pinned ci.yml.
- Then:
  - merge the four round-3B branches (and W0-NPM/W0-PY2 via `build/w0-consolidate`) into `build/w1-foundations`; fold their lane notes;
  - round 3B on the merged head:
    - frontend: c5 API-mode visualizer, badge fail-closed, NaN η_B display;
    - Decision 15: V2 natural default = paper benchmark (f = 2.118624e19 GeV, Λ⁴ = 2.563334027300118e-9); e2e-live runs the default;
    - Decision 16: `"synthetic": true` + badge on starobinsky-standard, gb-off-control, failing-run (results untouched);
    - Decision 17: canonical custom snippet = one sympy expression in φ; API also accepts `def V(<name>): return <expr>` (extract + rename to φ), any other body → 422 naming the canonical form, a test per case; Configurator default snippet + linter switch to the expression form;
    - API validation: critic fix-verify MEDIUMs, η_B gating in validation rows and scans;
    - Decision 14 test method: SF1/SF2/H2/L2 tests that fail before only by TypeError;
    - SF6 engine kwargs;
  - full re-verification on the merged head with CI green (except dependency review);
  - R19 rebaseline (a), which now captures the D13a badge plus Decisions 15–17 in one dispatch;
  - close Gate 1;
  - W0 merge per decision 12.

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
- `actions-dispatch-permission`: the session's GitHub integration gets 403 on `workflow_dispatch` and on re-running jobs. This is optional: authorised R19 rebaselines use CI's own artefacts instead (Decision-by-build 2), and `staging-db.yml` also runs from the deploy job.
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
