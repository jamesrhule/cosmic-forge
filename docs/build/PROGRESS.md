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
| Gate 0 | PASSED-PENDING-MERGE | every Gate 0 condition met @ 5afedb5; merge waits on BLOCKED-ON-JAMES:dependency-graph (or James exempting it) |
| Gate 1 | OPEN |
| Gate 2 | OPEN |
| Gate 3 | OPEN |
| Gate 4 | OPEN |
| Gate 5 | OPEN |

Next ticket: W0 merge (waits on dependency-review decision) → W1 (P1-01).

## Gate 0 status (W0 PR #3, head 5afedb5)
- [x] MERGE-MAP accounts for every conflicted file (50/50).
- [x] R16 review: no dropped capability. The first pass found 5 drops (A–E), all restored with tests; a re-check found 1 incomplete (E, aqc_tensor), now fixed (LEDGER "[Gate 0 review]").
- [x] Physics freeze: `physics_dir_hash` reproduces as `42805c73…92dd`; `audit/physics`, `golden.lock` and the drift-alarm workflow are byte-identical to the agent branch.
- [x] Every suite green in CI @ 5afedb5 (run 41216919685), except the one exempt `test_gb_to_zero_decoupling` (correction 1, P1-03).
- [x] Drift alarm green: run 41216310823 (success at 324eb4e); deliberate one-byte drift fails it (run 41216312782). Correction 10; evidence/P0-07.md.
- [x] Cosmology screenshots on three browsers: CI-browser baselines reviewed and locked (R19.sha256); playwright green on chromium/firefox/webkit @ 5afedb5; R19 control vs main in evidence/P0-06-r19-control.md (8/9 pass at 0.001; webkit `/` differs by 1px height plus anti-aliasing, ratio 5.12e-4, no cosmology change).
- [ ] Delete `claude/*` branches: after the W0 merge (R12). Remote branch deletion is refused by the session proxy → BLOCKED-ON-JAMES:branch-delete-permission.
- Also blocked on James (not Gate 0 conditions): tag push (`ucglef1-v1.0.0` at 73ae381), Dependency graph setting (dependency review job), required status checks on `main`, Supabase publishable key rotation.
