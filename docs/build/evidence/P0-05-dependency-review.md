# P0-05: dependency review re-run (Gate 0, decision 12)

- On 2026-10-31 the `dependency review` job failed on PR #3 (head `5687964`, run 41217576662): the repository's Dependency graph was off → `BLOCKED-ON-JAMES:dependency-graph`.
- On 2026-11-02 the same job **succeeded** on PR #5 (head `f3a1592`, job 125319490722). Its log lists the reviewed dependency changes (for example `+ psycopg@3.3.6`, `- sqlite-utils@4.2.1`), so the Dependency graph is now enabled.
- The re-run endpoint (`POST /actions/runs/41217576662/rerun-failed-jobs`) answers 403 "Resource not accessible by integration" to this session, so this file is committed only to start a fresh CI run on PR #3. That run reviews W0's whole dependency diff against `main`. PR #5's review covered only the W1 diff.
- Decision 12: W0 merges into `main` with a merge commit once this check is green. The 2026-11-02 sequencing (round 2 → merge → round 3 → rebaseline (a) → Gate 1 → W0 merge) puts the merge after Gate 1.
