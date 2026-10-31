# Build progress

Statuses: DONE | IN-PROGRESS | CI-PENDING | BLOCKED-ON-JAMES:<x> | OPEN-WITH-GAP | OPEN

| Wave | Ticket | Status | Evidence | Notes |
|---|---|---|---|---|
| W0 | P0-01 | CI-PENDING | evidence/P0-01.md | Chromium screenshots identical; Firefox/WebKit run in CI (P0-06) |
| W0 | P0-02 | CI-PENDING | evidence/P0-02.md | all suites green on merged tree (gb_to_zero exempt); Firefox/WebKit in CI (P0-06) |
| W0 | P0-03 | DONE | evidence/P0-03.md | fresh clone: frozen install, build, 68 tests, tsc 0 |
| W0 | P0-04 | OPEN-WITH-GAP | evidence/P0-04.md | frozen test_gb_to_zero_decoupling fails (ΔF_GB 5.9e-7) on all baselines; fix owned by P1-03 |
| W0 | P0-05 | CI-PENDING | (evidence/P0-05.md at W0 PR) | one CI + CodeQL written; SSR fixed on workerd; lint clean; jobs run on the W0 PR |
| W0 | P0-06 | CI-PENDING | evidence/P0-06.md | 41/41 Chromium on merged tree; firefox/webkit + their baselines in CI |
| W0 | P0-07 | BLOCKED-ON-JAMES:tag-push-permission | evidence/P0-07.md | keys moved, R9 degrade, gitleaks clean; tag created locally at 73ae381, remote refuses tag push |
| W1 | P3-01 | OPEN | | |
| W1 | P3-02 | OPEN | | |
| W1 | P3-03 | OPEN | | |
| W1 | P3-04 | OPEN | | |
| W1 | P3-05 | OPEN | | |
| W1 | P3-06 | OPEN | | |
| W1 | P3-07 | OPEN | | |
| W1 | P4-01 | OPEN | | correction 9: + GET /api/verdict/{id} (Supabase admin role); page fetches it; public/fixtures/verdict/* out of build; DoD + "unauthenticated GET of old static path returns 404" |
| W1 | P4-02 | OPEN | | |
| W1 | P1-01 | OPEN | | |
| W1 | P1-02 | OPEN | | |
| W1 | P1-03 | OPEN | | |
| W1 | P1-04 | OPEN | | |
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
| Gate 0 | BLOCKED-ON-JAMES:drift-alarm-workflow | see "Gate 0 status" below |
| Gate 1 | OPEN |
| Gate 2 | OPEN |
| Gate 3 | OPEN |
| Gate 4 | OPEN |
| Gate 5 | OPEN |

Next ticket: Gate 0 (W0 PR #3 CI) → then W1 (P1-01).

## Gate 0 status (W0 PR #3, head 8e8c8c1)
- [x] MERGE-MAP accounts for every conflicted file (50/50).
- [x] R16 review: no dropped capability. The first pass found 5 drops (A–E), all restored with tests; a re-check found 1 incomplete (E, aqc_tensor), now fixed (LEDGER "[Gate 0 review]").
- [x] Physics freeze: `physics_dir_hash` reproduces as `42805c73…92dd`; `audit/physics`, `golden.lock` and the drift-alarm workflow are byte-identical to the agent branch.
- [~] Every suite green: locally, packages 329 passed/7 skipped, backend all green except the one exempt `test_gb_to_zero_decoupling` (correction 1, P1-03), Vitest 71, Playwright Chromium 41/41. CI on PR #3 pending.
- [ ] Drift alarm green: **BLOCKED-ON-JAMES:drift-alarm-workflow** (the workflow can't install dirhash on the runner; R5 forbids me to edit it; patch in LEDGER → Conflicts).
- [ ] Cosmology screenshots on three browsers: Chromium baselines committed and passing; Firefox/WebKit CI-PENDING (baselines bootstrap from the first CI run's `e2e-screenshots` artifact).
- [ ] Delete `claude/*` branches: after the W0 merge (R12).
- Also blocked on James (not Gate 0 conditions): tag push (`ucglef1-v1.0.0` at 73ae381), Dependency graph setting (dependency review job), required status checks on `main`, Supabase publishable key rotation.
