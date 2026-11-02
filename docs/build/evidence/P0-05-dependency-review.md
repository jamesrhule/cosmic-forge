# P0-05: dependency review re-run (Gate 0, decision 12)

- On 2026-10-31 the `dependency review` job failed on PR #3 (head `5687964`, run 41217576662): the repository's Dependency graph was off → `BLOCKED-ON-JAMES:dependency-graph`.
- On 2026-11-02 the same job **succeeded** on PR #5 (head `f3a1592`, job 125319490722). Its log lists the reviewed dependency changes (for example `+ psycopg@3.3.6`, `- sqlite-utils@4.2.1`), so the Dependency graph is now enabled.
- The re-run endpoint (`POST /actions/runs/41217576662/rerun-failed-jobs`) answers 403 "Resource not accessible by integration" to this session, so this file is committed only to start a fresh CI run on PR #3. That run reviews W0's whole dependency diff against `main`. PR #5's review covered only the W1 diff.
- Decision 12: W0 merges into `main` with a merge commit once this check is green. The 2026-11-02 sequencing (round 2 → merge → round 3 → rebaseline (a) → Gate 1 → W0 merge) puts the merge after Gate 1.

## 2026-11-02 — PR #3's dependency review failed on real findings; fixed in the dependencies (lane W0-deps)

Lane notes: `docs/build/lanes/W0-deps.md`. Branch `build/w0-deps`. The job's configuration is unchanged:

- `fail-on-severity: high`
- the same `deny-licenses` list
- no `allow-ghsas` and no `allow-dependencies-licenses`

### What failed (PR #3, merge commit `964dc4d`, base main `cca2101`)

The job ran now that the Dependency graph is on. It failed with "Dependency review detected vulnerable packages":

- `vllm` 0.20.2: 1 critical, 8 high.

The log printed only vLLM, but the compare (`gh api …/dependency-graph/compare/cca2101…9a73c62`) had more high
advisories:

- `amazon-braket-sdk` 1.88.1: 1 high
- `cryptography` 46.0.3: 4 high
- `transformers` 4.57.6 (via vLLM): 4 high
- `virtualenv` 21.14.5: 4 high

Four packages carried denied licences:

- `block2` 0.5.4 (GPL-3.0-only)
- `healpy` 1.20.1 (GPL-2.0-only)
- `igraph` 1.0.0 (GPL-3.0-or-later)
- `py-bobyqa` 1.5.0 (GPL-3.0-or-later)

The log hid these findings because of two `||=` short-circuits in the action (lane D1):

- `vulnFound ||= printChangeVulnerabilities(change)` prints only the first vulnerable package.
- `issueFound ||= await printLicensesBlock(...)` skips the licence block once a vulnerability is found. `scripts/dependency_review_eval.cjs` re-runs the action's decision offline, using the
action's own SPDX libraries at its locked versions. On that compare it gives
`ACTION VERDICT: FAIL (vulnerable=5, forbidden=4, unresolved=0)`.

### Fixes (each item: lane notes D2–D8, S1, Removals)

| Item | Fix |
| --- | --- |
| VULN-vllm (GHSA-94f4-hr76-p5j6 critical + 8 high) | `ucgle-f1[vllm]` no longer installs the never-imported engine. The provider is an HTTP client (httpx) of a vLLM server that runs as its own process (≥ 0.32.0, the first release patching all of them). The extra is kept, empty. |
| VULN-transformers (4 high) | gone with vLLM, its only path |
| VULN-cryptography (4 high; first patched 50.0.0) | floor `cryptography>=50.0.0` (`constraint-dependencies`), locked 50.0.2. `azure-quantum` 3.13.0 → 3.12.0, because 3.13.0 pins `cryptography<=46.0.3` |
| VULN-virtualenv (4 high; first patched 21.14.9) | pre-commit runs as a uv tool, so virtualenv leaves the lock. In-lock, the patched virtualenv needs `packaging>=26.3`, which downgraded `iqm-client` 34 → 20. Floor `virtualenv>=21.14.9` kept |
| VULN-amazon-braket-sdk (GHSA-g697-2xrc-gc46 high; first patched 1.117.0) | floors `>=1.117.0` in `qfull-hep[ionq]`, `qfull-nuclear[ionq]`, `qcompass-router[braket]` and `constraint-dependencies`. The six Braket-pulling extras now conflict with `ucgle-f1` (patched Braket needs antlr4 4.13.2, Hydra 1.3.8 pins 4.9.*). Locked 1.127.7 only |
| VULN-setuptools (moderate + low) | floor `setuptools>=84.1.0`, locked 84.2.1 |
| VULN-torch (low) | gone with vLLM |
| VULN-diskcache (moderate GHSA-w8v5-vhqr-4h9v) | no patched release exists. Still needed by `llama-cpp-python`, which `LlamaCppProvider` imports. Moderate does not fail the job. Recorded (D7) |
| LIC-block2 | removed from `qcompass-core[chem]`, `qfull-chemistry[chem]` and `qfull-nuclear[classical]`. DMRG runs as a separate process (P2-06) |
| LIC-igraph | `netket` removed from `qfull-amo[classical]` and `qfull-condmat[classical]`. NQS runs as a separate process (P2-11) |
| LIC-py-bobyqa | `cobaya` removed from `ucgle-f1[infer]` (bilby + dynesty stay). Cobaya runs as a separate process (P1-09) |
| LIC-healpy | `PTAfast` removed from `ucgle-f1[gw]`. Separate process (P1-06) |
| LIC-cosmogw | `CosmoGW` removed from `ucgle-f1[gw]`. Separate process (P1-06) |
| LIC-pyqt5 | `qfull-amo[bloqade_digital]` lists the `bloqade` meta-package's components without bloqade-circuit's `vis` extra |
| LIC-cobaya, LIC-getdist | cobaya is LGPL-3.0-or-later + GFDL docs and getdist is LGPL-3.0-or-later (weak copyleft). Both leave the lock with cobaya (py-bobyqa) |
| LIC-typing-extensions, -docutils, -pytest-regressions, -rfc3987-syntax, -aiohappyeyeballs | scancode false positives, checked on PyPI and, for docutils, in its `COPYING.rst` (lane D8). Not GPL. aiohappyeyeballs left with vLLM |

`uv lock --upgrade-package cryptography --upgrade-package setuptools --upgrade-package amazon-braket-sdk`, run from the
original lock. Entries go 538 → 408, and no other locked version changed (lane notes list every change).

### Acceptance: GitHub's own compare for the pushed head

`gh api "repos/jamesrhule/cosmic-forge/dependency-graph/compare/cca2101995f42d6f5b92264a2b09e6f6a2fdc6b1...ea9c677b1590659423f2ec431f0ae0f1a8cc3314"`
was processed on the first query after the push. It reflects the new lock (`cryptography` 50.0.2, `azure-quantum` 3.12.0,
`amazon-braket-sdk` 1.127.7; no vllm, block2, igraph, cobaya or virtualenv).

The compare holds 462 added and 916 removed changes:

- 395 from `uv.lock`
- 915 removals from the deleted `package-lock.json`

`node scripts/dependency_review_eval.cjs` gives `ACTION VERDICT: PASS (vulnerable=0, forbidden=0, unresolved=0)`:

- vulnerable (added, runtime, ≥ high): none. The only advisory left on any added package is `diskcache` 5.6.3, moderate.
- forbidden (the action's `satisfiesAny` against the deny list): none
- unresolved (invalid SPDX): none
- The action looks up 4 licences on GitHub because the graph has none:
  - pulser-core and pulser-simulation (Pulser): Apache-2.0
  - pyzx-param (rafaelha/pyzx): Apache-2.0
  - requests-sigv4: the repository returns 404, so the action records it as unlicensed (not a failure); PyPI says Apache-2.0
- Stricter R11 scan (a denied identifier anywhere in the expression): `docutils`, `pytest-regressions`, `rfc3987-syntax`
  and `typing-extensions`. All four are scancode false positives with verified non-GPL licences (lane D8). Every
  confirmed GPL package is gone.

`ea9c677` is a lane-branch commit. PR #3's job re-runs when this branch is merged into `build/w0-consolidate`.

### npm side (not seen by dependency review; routed)

- There is no `package-lock.json` in the tree. Its 915 removals are ignored by the action, which judges only added changes.
- GitHub's dependency graph does not read `bun.lock`.
- `bun audit` on `bun.lock`: 130 advisories (4 critical, 55 high, 53 moderate, 18 low), across 17 packages with high or
  critical advisories. The critical ones are TanStack Start GHSA-qx66-fv34-fjm8 and seroval.
- CI's `bun run audit:gate` still prints OK. `scripts/audit-gate.ts` does not parse `bun audit --json`'s
  `{package: [advisory]}` shape, so the gate is a no-op.

Routed as a P0-05 defect for a frontend-deps lane (lane notes D11). Upgrading the framework needs R19 proof on CI's browsers.

### Suites on `ea9c677` (uv 0.11.32, Python 3.12.13, bun 1.4.4, node 22.22.0)

| Check | Result |
| --- | --- |
| `uv lock --check` | `Resolved 408 packages`, exit 0 |
| `uv sync --frozen --all-packages --extra dev --extra qcompass --extra viz --group dev` | exit 0 |
| `cd backend && uv run --frozen pytest -q -m "not slow"` | 260 passed, 2 deselected, 1 xfailed (the pre-existing V2 η_B xfail) |
| `cd backend && uv run --frozen pytest -q -m slow --deselect …test_gb_to_zero_decoupling` | 1 passed, 262 deselected, exit 0 |
| drift alarm, the workflow's steps in a fresh `git archive` export (`uv sync --package ucgle_f1`, `uv pip install "dirhash>=0.5"`, `PYTHONPATH=src uv run pytest audit -q -m "not slow"`, dirhash) | 80 passed, 1 skipped, 1 deselected; `42805c73538df5eb0f9eb109ead9a541253d5371d71eac5ea04be0ffaf8e92dd` = `golden.lock` |
| `uv run --frozen pytest packages -q --import-mode=importlib` | 341 passed, 7 skipped. With `-rs`, every skip is an existing optional-backend `importorskip` or skip: pyblock2 ×2 (S-chem-2, S-nuc-4), qiskit_addon_sqd, azure.quantum, bloqade (S-amo-3), netket (S-amo-4), quimb |
| `uv run --frozen ruff check packages` | All checks passed |
| `uv run --frozen python scripts/licence_gate.py python` | 218 packages checked, 0 violations |
| `qfull-amo[bloqade_digital]` in its own env (`uv sync --frozen --package qfull-amo --extra bloqade-digital --extra dev`) | `import bloqade`, `bloqade.squin`, `bloqade.qasm2`, `bloqade.analog`, `bloqade.visual` OK; PyQt5 not installed; qfull-amo tests 18 passed, 1 skipped (netket importorskip) |
| frontend in a fresh `git archive` export + `bun install --frozen-lockfile` | `bun run lint` 0 errors (15 warnings); `bunx prettier --check .` clean; `bunx tsc --noEmit` exit 0; `bun run test` 16 files / 84 tests passed; `bun run build` exit 0; `scripts/check_r19.sh` 9 PNGs match `R19.sha256`; `bun run audit:gate` "OK" (false-green, see above) |

ESLint, run in the lane worktree itself, also lints the TypeScript that jupyter packages install under `.venv/` (the dev extra
installs jupyter-book). CI's frontend job has no `.venv`, which is why the frontend checks ran in a clean export.

## 2026-11-02 — npm side fixed (lane W0-npm)

Lane notes: `docs/build/lanes/W0-deps.md`, section "2026-11-02 — lane W0-npm" (N1–N8). Branch `build/w0-npm` from `4de96fa`.
Tools: bun 1.4.4, node 22.22.0, Playwright 1.59.1 with the sandbox Chromium (`PW_CHROMIUM_PATH=/opt/pw-browsers/chromium`,
build 1243). Firefox and WebKit are not available in this sandbox. Earlier sections of this file are unchanged.

### The gate before and after

| Run | Result |
| --- | --- |
| old `scripts/audit-gate.ts` on `4de96fa`'s `bun.lock` (clean `git archive` export, `bun install --frozen-lockfile`) | exit 0, `[audit-gate] OK — no advisories ≥ high` (false green) |
| new gate on the same export (`bun.lock` sha256 `781ea76d…097a7b`, identical to `git show 4de96fa:bun.lock`) | exit 1, `130 advisories (4 critical, 55 high, 53 moderate, 18 low)`, `FAIL — 59 blocking advisories` (first: `[critical] @tanstack/react-start >=1.143.12 <1.168.60 … (GHSA-qx66-fv34-fjm8)`) |
| new gate on this branch's head (clean export) | exit 0, `24 advisories (0 critical, 0 high, 18 moderate, 6 low)`, `OK — no advisories ≥ high (allowlisted: 0)` |
| `bun audit --json` with no lockfile / with the registry unreachable | exit 1 with empty stdout (captured as fixtures); the old gate read both as OK, the new one exits 2 |

`bun audit --production` on `4de96fa` lists 16 of the 17 packages with a high or critical advisory; the gate covers the
whole tree (lane N2).

### Upgrades and their advisories

Advisory data comes from the npm registry's advisory endpoint (`/-/npm/v1/security/advisories/bulk`, the source `bun audit`
uses), queried separately for each old and each new version: every new version has 0 high or critical advisories. The
affected ranges and first-patched versions of GHSA-qx66-fv34-fjm8, GHSA-7rv5-mrxv-xcr9, GHSA-mrhx-c7xc-m3w5,
GHSA-wq5f-xc86-pv6w, GHSA-2m5v-pch6-74hx, GHSA-96hv-2xvq-fx4p and GHSA-587h-7wmj-h5pm were also read on their GitHub
advisory pages.

| Package | Old → new | High/critical advisories fixed |
| --- | --- | --- |
| `@tanstack/react-start` | 1.167.39 → 1.168.60 | GHSA-qx66-fv34-fjm8 (critical, reflected XSS; patched 1.168.60) |
| `@tanstack/start-server-core` | 1.167.19 → 1.169.39 | GHSA-qx66-fv34-fjm8 (critical; patched 1.169.39) |
| `seroval` | 1.5.2 → 1.7.6 | GHSA-mv8w-475r-vwqw, GHSA-p6vx-979v-rg4c (critical); GHSA-jp82-f5mq-hwhp, GHSA-97r2-qh9m-474h, GHSA-wp97-x4hv-qvhp, GHSA-7rv5-mrxv-xcr9 (patched 1.6.8) |
| `zod` | 4.3.6 and 3.25.76 → 4.6.6 | GHSA-mrhx-c7xc-m3w5 (patched 4.6.6) |
| `vite` | 7.3.2 → 7.3.7 | GHSA-587h-7wmj-h5pm (patched 7.3.7) |
| `sharp` | 0.34.5 → 0.35.5 (override) | GHSA-f88m-g3jw-g9cj, GHSA-rgj7-g3m4-5g8c, GHSA-wq5f-xc86-pv6w (patched 0.35.5) |
| `undici` | 7.24.4, 7.25.0 → 7.30.1 (override) | 10 highs, incl. GHSA-2m5v-pch6-74hx (patched 7.30.1) |
| `ws` | 8.18.0, 8.20.0 → 8.21.0 (override) | GHSA-96hv-2xvq-fx4p (patched 8.21.0) |
| `brace-expansion` | 1.1.14, 5.0.5 → 1.1.20, 5.0.11 | 5 GHSAs (10 entries) |
| `browserslist` | 4.28.2 → 4.28.7 | GHSA-c83g-rgw3-j3cx, GHSA-73wf-gq98-2v4g |
| `dompurify` | 3.4.1 → 3.4.17 | GHSA-mrv2-3pqr-j5jr |
| `fast-uri` | 3.1.0 → 3.1.7 | 8 GHSAs |
| `js-yaml` | 4.1.1 → 4.3.2 | GHSA-52cp-r559-cp3m, GHSA-5p4m-2wfm-xmqj, GHSA-2883-xcg3-v3hh |
| `nanoid` | 3.3.11 → 3.3.18 | GHSA-28wg-ghj8-5hjv, GHSA-2v37-7h3g-55p8, GHSA-xwg4-73v4-xw9w |
| `postcss` | 8.5.9 → 8.5.18 | GHSA-6g55-p6wh-862q, GHSA-r28c-9q8g-f849 |
| `protobufjs` | 7.5.5 → 7.6.1 | 5 GHSAs |
| `source-map-js` | 1.2.1 → 1.2.2 | GHSA-68fv-2mgg-jv7q |

With them: `@tanstack/react-router` 1.168.21 → 1.170.41 and `@tanstack/router-plugin` 1.167.22 → 1.168.42 (the versions
Start 1.168.60 pins), and the rest of the TanStack family (lane N3). `bun install --frozen-lockfile` on a clean export:
no changes.

### R19 (no rebaseline; `e2e/__screenshots__/**` and `R19.sha256` untouched)

1. **Zero-tolerance before/after.** I served the default production build of `4de96fa` and of this branch's head with
   `wrangler dev`. I rendered `/`, `/visualizer` and `/visualizer/kawai-kim-natural` in Chromium with the byte-identity
   spec's own steps and options (1440×900, reduced motion, ready check, `networkidle`, `freezeMotion`, footer mask, full
   page). Then I compared the decoded RGBA of each PNG pixel by pixel, with no threshold and no anti-aliasing allowance.
   The last six rounds alternated the two builds.
   - `/`: all 11 captures of `4de96fa` and all 6 of the head are the same PNG (`358c1a75…`), 0 differing pixels.
   - `/visualizer`: likewise, `5118e9dd…`, 0 differing pixels.
   - `/visualizer/kawai-kim-natural`: both builds produce `2ca2b031…` (`4de96fa` 12 of 22 captures, head 2 of 6) and
     `3bdbd1fc…` (`4de96fa` 9 of 22, head 4 of 6). `4de96fa` also produced `f2da…` once. The variants differ from
     `2ca2…` in at most the same 8 pixels, by one colour level each. Those pixels are anti-aliased corners, at
     (471–473, 113–114) on the phase-space panel and (868–871, 686–689) on the `n_B` node. A matched pair from the
     interleaved rounds (`4de96fa` round 1, head round 1) has 0 differing pixels on all three routes. This is a
     pre-existing per-run rasterisation flip in the WebGL panels, which `4de96fa` shows on its own, not a change.
2. **The real spec against the committed baselines.** `bunx playwright test e2e/cosmology-byte-identity.spec.ts
   --project=chromium` fails locally at `4de96fa` and on this branch with identical numbers: 11297, 15221 and 7697
   differing pixels for `/`, `/visualizer` and kawai. The committed baselines come from CI's browsers (`2b59c0f`), and the
   sandbox's Chromium and fonts lay text out differently. Identical failure counts before and after are further evidence
   that nothing moved. The pass/fail verdict on the committed baselines is CI's `playwright` job (three browsers).
3. `scripts/check_r19.sh` before and after the run: `R19 baselines locked: 9 PNGs match R19.sha256`.

The first build after the upgrade was not identical. Every page rendered blank, because the upgrade began sending
`src/start.ts`'s CSP, which blocked Start's inline hydration scripts. The nonce fix (lane N5) restored the renders above.
Artefacts (PNGs, hash table, the 8-pixel diff image, the proof spec and the comparator) are in the lane's scratch
directory and were not committed.

### Suites on this branch's head (clean `git archive` export + `bun install --frozen-lockfile`)

| Check | Result |
| --- | --- |
| `bun run lint` | 0 errors, 15 warnings (as at `4de96fa`) |
| `bunx prettier --check .` | All matched files use Prettier code style |
| `bunx tsc --noEmit` | exit 0 (now also type-checks `scripts/`) |
| `bun run test` | 18 files, 111 tests passed (was 16 / 84; +19 gate tests, +8 CSP tests) |
| `bun run build` | exit 0 |
| `bun run build && SSR_SMOKE_PORT=4790 scripts/ssr_smoke.sh` | 200 `/`, `/pricing`, `/status`; no Worker errors |
| all-domains build + `scripts/ssr_smoke.sh all-domains` | 35 routes, all 200; no Worker errors |
| `bun run audit:gate` | exit 0 (above) |
| `scripts/check_r19.sh` | 9 PNGs match `R19.sha256` |
| `python3 scripts/licence_gate.py npm node_modules` | 778 packages checked, 0 violations |
| `bunx playwright test --project=chromium` (whole suite, 49 tests; `E2E_PORT_DEFAULT=4610`) | 46 passed, 3 failed. Smoke 4/4, synthetic-fixture-badge 8/8, cosmology regression and the domain-list test pass, and `chemistry-h2-flow` passes (it failed until `'unsafe-eval'`, lane N5). The 3 failures are the cosmology-byte-identity screenshots against the CI-browser baselines (11297 / 15221 / 7697 px). `4de96fa` in the same sandbox gives the same 46 passed and the same 3 failures with the same pixel counts. `check_r19.sh` passes before and after the run; `check_e2e_restarts.sh` passes |
| `cd backend && uv run --frozen pytest -q tests/test_lovable_contract.py tests/integration/test_domain_parity.py` | 56 passed (the backend tests that read the frontend's fixtures and `src/types/domain.ts`; `tests/test_frontend_contract.py` exists only on W1) |
