# Audit-gate fixtures

Real output of `bun audit --json` from bun 1.4.4 (the version CI pins), captured byte for byte on
2026-11-02 for `scripts/audit-gate.test.ts`. The `.stdout`/`.stderr` extensions keep Prettier
from reformatting them.

| File                                    | Captured from                                                                           | Exit |
| --------------------------------------- | --------------------------------------------------------------------------------------- | ---- |
| `bun-1.4.4-4de96fa.stdout`              | the repository at `4de96fa` (130 advisories: 4 critical, 55 high)                       | 1    |
| `bun-1.4.4-after.stdout`                | the repository after lane W0-npm's upgrades (18 moderate, 6 low)                        | 1    |
| `bun-1.4.4-moderate-only.stdout`        | a project whose only dependency is `@protobufjs/utf8` 1.1.0 (one moderate)              | 1    |
| `bun-1.4.4-clean.stdout`                | a project whose only dependency is `is-number` 7.0.0                                    | 0    |
| `bun-1.4.4-registry-unreachable.stderr` | the moderate-only project with the registry set to `http://127.0.0.1:9/` (stdout empty) | 1    |
| `bun-1.4.4-missing-lockfile.stderr`     | a project with no lockfile (stdout empty)                                               | 1    |

bun exits 1 for "found advisories" and for "could not audit", so the gate never trusts the exit
status alone.
