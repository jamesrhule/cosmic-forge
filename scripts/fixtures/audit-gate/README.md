# Audit-gate fixtures

Real output of `bun audit --json` from bun 1.4.4 (the version CI pins), captured byte for byte on
2026-11-02 for `scripts/audit-gate.test.ts`. The `.stdout`/`.stderr` extensions keep Prettier
from reformatting them.

| File                                     | Captured from                                                                                       | Exit |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------- | ---- |
| `bun-1.4.4-4de96fa.stdout`               | the repository at `4de96fa` (130 advisories: 4 critical, 55 high)                                   | 1    |
| `bun-1.4.4-after.stdout`                 | the repository after lane W0-npm's upgrades (18 moderate, 6 low)                                    | 1    |
| `bun-1.4.4-moderate-only.stdout`         | a project whose only dependency is `@protobufjs/utf8` 1.1.0 (one moderate)                          | 1    |
| `bun-1.4.4-clean.stdout`                 | a project whose only dependency is `is-number` 7.0.0                                                | 0    |
| `bun-1.4.4-registry-unreachable.stderr`  | the moderate-only project with the registry set to `http://127.0.0.1:9/` (stdout empty)             | 1    |
| `bun-1.4.4-missing-lockfile.stderr`      | a project with no lockfile (stdout empty)                                                           | 1    |
| `bun-1.4.4-canary.stdout`                | the canary lock (`canary/`, below) against registry.npmjs.org                                       | 1    |
| `bun-1.4.4-canary-empty-registry.stdout` | the canary lock against a local registry that answers the bulk advisory endpoint with HTTP 200 `{}` | 0    |
| `bun-1.4.4-empty-registry.stdout`        | the repository's own lock against that same local registry (byte-identical to the clean output)     | 0    |

bun exits 1 for "found advisories" and for "could not audit", so the gate never trusts the exit
status alone.

`canary/package.json.fixture` and `canary/bun.lock.fixture` are a project whose only dependency is
`minimist` 1.2.5 (GHSA-xvch-5gv4-984h, critical), its lock written by `bun install --lockfile-only`.
It is never installed or built. `scripts/audit-gate.ts` copies the two files to `package.json` and
`bun.lock` in a scratch directory, together with this project's `bunfig.toml` and `.npmrc` when
present, and audits them with the same environment, so the canary asks the registry the main audit
asked. A pass needs at least one advisory for the canary; otherwise the gate exits 2 ("no advisory
data"). The `.fixture` names keep GitHub's dependency graph from reading the canary as a manifest of
this repository (which would add a critical advisory to the dependency review).
