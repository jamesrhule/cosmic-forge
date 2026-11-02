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
| Gate 0 | PASSED-PENDING-MERGE | every Gate 0 condition met @ 5afedb5; merge waits on BLOCKED-ON-JAMES:dependency-graph (or James exempting it) |
| Gate 1 | OPEN |
| Gate 2 | OPEN |
| Gate 3 | OPEN |
| Gate 4 | OPEN |
| Gate 5 | OPEN |

Next ticket: RESUMED 2026-11-02. On any resume, re-read LEDGER Decisions 11–14 first. State:
- [W1-PARAMS] potential-parameter boundary fix is on `build/w1-platform` 9c6bf4c (OPEN-WITH-GAP). e2e-live still fails because the UI's V2 natural default (f ≈ 0.029 M_Pl) doesn't inflate under the physical model → BLOCKED-ON-JAMES:ui-v2-defaults-vs-paper-benchmark (option (a) changes R19 page `/`, beyond decision 13). Completed live runs report η_B = NaN until P1-04.
- Gate 1 verification workflow wf_9b56ec35-e49 was resumed. c1–c4 finished and found new HIGH/MEDIUM/LOW issues (`scratchpad/round2/c1-c4-findings.txt`); the rest is running.
- Round-2 fix workflow wf_9a895793-168 is running: lane DB on `build/w1-sec-db`, lane WORKER on `build/w1-sec-worker`, both from 9c6bf4c, each with an adversarial verifier.
- Then:
  - merge `build/w1-platform`, `build/w1-sec-db` and `build/w1-sec-worker` into `build/w1-foundations`;
  - round 3 for the c5–c7, physics and fresh-eyes findings, plus the e2e-live config and how the UI shows a NaN η_B;
  - R19 rebaseline (a);
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

Open:
- `dependency-graph`: enable Dependency graph (Settings → Code security), or exempt the dependency-review check. This blocks the W0 merge (decision 12) and therefore W1's merge.
- `tag-push-permission`: push tag `ucglef1-v1.0.0` at `73ae381`. The session's git proxy refuses tag pushes.
- `branch-delete-permission`: delete `build/r19-control`, `build/w0-drift-proof`, and the `claude/*` branches once W0 is merged.
- `branch-protection`: required status checks on `main`.
- `supabase-key-rotation`: rotate the Supabase publishable key that was in the git history (P0-07).
- `arxiv-access`: papers 1702.07689, 2007.08029 and 2412.09490, for P1-04's adiabatic subtraction and V4 cross-check.
- `DATABASE_URL`: Supabase Postgres connection string for staging and production, covering the API, the worker and the package stores.
- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`: artefact uploads to `run-artifacts`; workers only.
- `SUPABASE_PUBLISHABLE_KEY`: the verdict routes need it in the deployed API, which `deploy/qcompass-api.yaml` doesn't provide yet.
- `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` and `QCOMPASS_CORS_ORIGINS`: secrets in the GitHub environments `staging` and `production`.
- GitHub environment variables `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` and `VITE_SUPABASE_PROJECT_ID`.
- GCP project setup:
  - an Artifact Registry repo named `qcompass`;
  - Secret Manager entries `DATABASE_URL`, `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`;
  - IAM roles for the service account;
  - L4 GPU quota;
  - `GPU_MIN_INSTANCES` ≥ 1 to run `gpu_*` jobs.
- `supabase-jwt-signing-keys`: only if production Supabase still signs with legacy HS256; the API accepts only asymmetric keys.
- Production data:
  - if any tenant has the slug `dev` or a UUID-shaped slug, rename it, then validate the slug constraint (migration `20261031200000`);
  - agent-memory rows without a `dev` tenant stay unassigned until you choose a tenant for them (`20261031200400`).
- `cosmology-fixture-synthetic-labels`: whether to flag `starobinsky-standard`, `gb-off-control` and `failing-run` as synthetic, and under which R19 rebaseline. Decision 13 covers only `kawai-kim-natural`.
- `ui-v2-defaults-vs-paper-benchmark`: the Configurator's V2 natural default (f = 7e16 GeV, Λ⁴ = 2.5e-7, i.e. f_a ≈ 0.029 M_Pl) does not inflate under decision 11's physical model, so a run of the default config fails. Options:
  - (a) set the V2 default to the paper benchmark in Configurator units (f = 2.118624e19 GeV, Λ⁴ = 2.563334027300118e-9). This needs an R19 rebaseline of `/` beyond decision 13.
  - (b) keep the default and have e2e-live run a config that inflates.
  - (c) keep e2e-live red.
- Custom-potential snippet shape: the Configurator's default custom snippet is a `def V(psi):` function, which its linter requires, but the backend compiles a single expression in φ, so the API refuses the default snippet with 422. Decide which shape is canonical.
- `r19-rebaseline`: any R19 change beyond decision 13's (a) badge and (b) P1-04 results.

Cleared:
- `drift-alarm-workflow` (correction 10)
- `p1-03-default-coupling` (decision 11)
