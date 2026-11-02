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

Next ticket: RESUMED 2026-11-02. On any resume, re-read LEDGER Decisions 11–17 first. State:
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

Open:
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
- `r19-rebaseline`: any R19 change beyond rebaseline (a) (the decision 13 badge plus decisions 15–17) and (b) (P1-04 results).

Cleared:
- `dependency-graph` (enabled by 2026-11-02: the dependency review ran on PR #5 job 125319490722 and on PR #3 run 41459720600)
- `drift-alarm-workflow` (correction 10)
- `p1-03-default-coupling` (decision 11)
- `ui-v2-defaults-vs-paper-benchmark` (decision 15: option (a), inside rebaseline (a))
- `cosmology-fixture-synthetic-labels` (decision 16: all three flagged, inside rebaseline (a))
- custom-potential snippet shape (decision 17: canonical sympy expression in φ; `def V(<name>): return <expr>` accepted)
