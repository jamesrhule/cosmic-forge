# W0-deps — dependency review on PR #3, fixed in the dependencies

Branch `build/w0-deps` (from `build/w0-consolidate` @ `9a73c62`). Goal: PR #3's `dependency review` job passes because the
dependencies are fixed. The job is unchanged: `fail-on-severity: high`, the same `deny-licenses` list, no `allow-ghsas`, no
`allow-dependencies-licenses`. Evidence and the compare-API evaluation: `docs/build/evidence/P0-05-dependency-review.md`.

`uv.lock` goes from 538 to 408 package entries. Version changes on packages that stay: `cryptography` 46.0.3 → 50.0.2,
`setuptools` 80.10.2 → 84.2.1, `amazon-braket-sdk` {1.88.1, 1.127.7} → 1.127.7, `amazon-braket-default-simulator`
{1.27.0, 1.43.0} → 1.43.0, `azure-quantum` 3.13.0 → 3.12.0 (D4), `cloudpickle` {2.2.1, 3.1.2} → 2.2.1 (3.1.2 was vLLM's).
Every other locked version is unchanged. The lock was made with `uv lock --upgrade-package cryptography --upgrade-package
setuptools --upgrade-package amazon-braket-sdk` from the original lock (no blanket upgrade).

## Decisions

- **D1 How the action decides.** Read from `actions/dependency-review-action` at the SHA the job ran (`2031cfc0…`, v4.9.0):
  - Vulnerabilities: `added` changes in scope `runtime` (the default `fail-on-scopes`) with an advisory of severity ≥ high.
    Removed changes never count, so `package-lock.json`'s 915 removals (and their advisories) are ignored.
  - Licences: each added change's SPDX expression goes to `@onebeyond/spdx-license-satisfies` 1.0.1
    `satisfiesAny(expr, deny)`. That matches only an OR-branch that is exactly one denied licence: `GPL-3.0-only` is
    forbidden, `MIT AND GPL-3.0-only` is not. An expression that does not parse is "unresolved" and also fails the job. A null
    licence with a GitHub source URL is replaced by the repository's GitHub licence.
  - The log hides findings in two places, both through `||=` short-circuits:
    - `printVulnerabilitiesBlock` loops `vulnFound ||= printChangeVulnerabilities(change)`, so it prints only the first
      vulnerable package.
    - `main.ts` computes `issueFound ||= await printLicensesBlock(...)`, so the licence block never runs once a
      vulnerability is found.
    That is why the PR #3 log showed only vLLM, while Braket, cryptography, transformers and virtualenv (high) and block2,
    healpy, igraph and py-bobyqa (denied licences) were also failing. Always judge from the compare API, not the log.
  - This lane's acceptance is stricter (R11): no added package whose expression contains a denied identifier anywhere, unless
    its official licence was read and is not GPL (D8). `scripts/dependency_review_eval.cjs` re-implements the action with
    the same SPDX libraries at the action's locked versions (`spdx-expression-parse` 4.0.0,
    `@onebeyond/spdx-license-satisfies` 1.0.1, `spdx-license-ids` 3.0.20) and adds the stricter scan. Usage is in its header.
    Run on PR #3's original compare, it reproduces the failure (5 vulnerable, plus the 4 forbidden that the log never
    printed).
- **D2 vLLM: the in-process engine leaves; the provider stays.** `ucgle-f1[vllm]` installed `vllm` 0.20.2 (1 critical, 8
  high), which dragged in `transformers` 4.57.6 (4 high), `torch` and the CUDA wheels. Nothing imports `vllm`:
  `m8_agent/models/local_vllm.py` is an HTTP client of a vLLM OpenAI-compatible server at `$VLLM_URL`, using `httpx` (a core
  dependency). A patched release exists (0.32.0), but raising the floor would put vLLM 0.33's pins and caps (`torch==2.14.0`,
  `numba==0.65.0`, `fastapi<0.137`, `setuptools<81`, `transformers>=5.16.1,<5.21`) on the whole universal lock, for a package no code
  imports. The extra stays, empty, so `pip install ucgle_f1[vllm]` still works. `docs/qcompass/optional-backends.md` says
  to run the server separately at ≥ 0.32.0. The provider (PLAN Part 7, P5-01) is unchanged.
- **D3 Braket extras conflict with ucgle-f1, like `qcompass-router[braket]` already did.** The lane brief's description ("1.88.1
  only in a python≥3.15 s390x fork") was inaccurate. The lock had `amazon-braket-sdk` 1.88.1 on every platform in the forks
  that include ucgle-f1, reached through `qfull-hep[ionq]`, `qfull-nuclear[ionq]` and `bloqade-analog`.
  - Why: the first SDK without GHSA-g697-2xrc-gc46 (insecure pickle deserialization, high; patched 1.117.0) needs
    `amazon-braket-default-simulator>=1.32.0`, which pins `antlr4-python3-runtime==4.13.2`. `hydra-core` 1.3.8, the latest
    stable, pins `4.9.*`. A patched Braket and Hydra can't share an environment.
  - What changed: root `[tool.uv] conflicts` gains six pairs with `ucgle-f1`: `qcompass-router[quera]`, `qfull-hep[ionq]`,
    `qfull-nuclear[ionq]`, `qfull-amo[bloqade-analog]`, `qfull-amo[bloqade-digital]` and `qfull-condmat[analog]`. Floors
    `amazon-braket-sdk>=1.117.0` go in the three extras that name it and in `constraint-dependencies`, which covers
    `bloqade-analog`.
  - Braket environments run without the cosmology backend, as plan-author correction 3 already does for
    `qcompass-router[braket]` (P2-01 owns the separate job, lock fork and qpu image). CI's `UV_SYNC` installs none of these
    extras.
- **D4 `azure-quantum` 3.13.0 → 3.12.0.** 3.13.0, the latest release, requires `cryptography<=46.0.3`, which is exactly the
  vulnerable version (4 high). 3.12.0 has no cryptography cap, and PyPI lists no advisory for it. Once a release lifts the
  pin, `uv lock --upgrade-package azure-quantum` returns to the newest.
- **D5 pre-commit runs as a uv tool, not as a project dependency.** Patched `virtualenv` (≥ 21.14.9: GHSA-vxj4-q4g9-crj7,
  GHSA-c978-59m8-c77v, GHSA-6w3r-xr62-4xcp, GHSA-394h-qwmc-48pf) requires `packaging>=26.3`. Every current `iqm-client`
  (34–36) caps `packaging<25`. With pre-commit in the dev group, the patched virtualenv downgraded `qcompass-router[iqm]` to
  `iqm-client` 20.11, which was measured. pre-commit is a local git-hook manager that CI never runs, and its recommended
  install is an isolated tool, so it leaves the root dev group and `ucgle-f1[dev]`. The replacement is `uvx pre-commit
  install` / `uvx pre-commit run --all-files`, which uses the same `.pre-commit-config.yaml` and creates its own hook
  environments as before. `virtualenv` is no longer in the lock.
- **D6 Security floors as `[tool.uv] constraint-dependencies`.** These are for transitive packages no member declares
  directly, each at the first release that fixes every high or critical advisory found: `cryptography>=50.0.0`
  (GHSA-r6ph-v2qm-q3c2, GHSA-537c-gmf6-5ccf, GHSA-jwv3-5hgf-82ww, GHSA-g6cj-pr64-35w5), `amazon-braket-sdk>=1.117.0`,
  `virtualenv>=21.14.9` (inert today, D5) and `setuptools>=84.1.0` (moderate GHSA-h35f-9h28-mq5c, low GHSA-xmj3-9gf7-h52w).
  They constrain the lock only and add no dependency. First-patched versions come from the GitHub advisory pages and PyPI's
  advisory data.
- **D7 `diskcache` 5.6.3 (moderate GHSA-w8v5-vhqr-4h9v) stays.** No patched release exists (5.6.3 is the latest). It arrives
  through `llama-cpp-python` (`ucgle-f1[llamacpp]`), which `LlamaCppProvider` imports in-process, so it is needed. Moderate
  severity does not fail the job. Recorded, not hidden.
- **D8 Scancode false positives, each checked on its official page (R10).**

  | Package | Dependency-graph expression contains | Official licence | Where it comes from |
  | --- | --- | --- | --- |
  | `typing-extensions` 4.16.0 | GPL-1.0-or-later | PSF-2.0 (PyPI `License-Expression`) | core |
  | `docutils` 0.22.4 | GPL-1.0-or-later, GPL-3.0-* | Public domain, BSD-2-Clause, BSD-3-Clause. `COPYING.rst` names one GPL file, `tools/editors/emacs/rst.el`, which is not in the wheel (wheel listing checked) | `ucgle-f1[dev]` (myst-nb) |
  | `pytest-regressions` 2.11.0 | GPL-3.0-only | MIT (PyPI licence and classifier) | dev extras |
  | `rfc3987-syntax` 1.1.0 | GPL-1.0-or-later | MIT (PyPI `License-Expression`). It is the dependency of `jsonschema[format-nongpl]`, the non-GPL replacement for `rfc3987` | myst-nb, pulser |
  | `aiohappyeyeballs` 2.7.1 | GPL-1.0-or-later | PSF-2.0 (PyPI); gone with vLLM anyway | — |

  The action does not fail on these AND-expressions (D1). They are permissive, so R11 holds.
- **D9 Licences fetched from GitHub by the action** (null licence in the graph): `pulser-core`/`pulser-simulation`
  (pasqal-io/Pulser: Apache-2.0), `pyzx-param` (rafaelha/pyzx: Apache-2.0), `requests-sigv4` (the repository URL returns 404,
  so the action records it as unlicensed, which does not fail; PyPI says Apache License 2.0). The null-licence `bloqade-core`,
  `bloqade-decoders` and `bloqade-lanes` ship Apache-2.0 `LICENSE` files (wheels read).
- **D10 W1 must re-lock after merging W0.** W1 branches change the root and member `pyproject.toml` files and `uv.lock`.
  After merging this lane:
  - take both sides' `pyproject.toml` changes and re-run `uv lock` (lock files are regenerated, never hand-merged);
  - because `qcompass-worker` depends on `ucgle-f1`, add the six D3 pairs for `qcompass-worker` too, as W1 did for
    `qcompass-router[braket]`;
  - `pyjwt[crypto]` (W1) pulls `cryptography`, and the D6 floor covers it;
  - re-run the compare API for PR #5.
- **D11 npm side: not seen by dependency review, and its gate is a no-op.** Routed, not fixed here.
  - No `package-lock.json` is in the tree; P0-03 deleted it. The PR #3 compare lists only its removals, which the action
    ignores (D1).
  - GitHub's dependency graph does not parse `bun.lock`, so npm packages never reach dependency review.
  - `bun audit` on `bun.lock` reports 130 advisories: 4 critical, 55 high, 53 moderate, 18 low. The critical ones are
    `@tanstack/react-start`/`@tanstack/start-server-core` GHSA-qx66-fv34-fjm8 (reflected XSS in server-function responses)
    and `seroval` GHSA-mv8w-475r-vwqw and GHSA-p6vx-979v-rg4c. The high ones are spread over 17 packages, including `undici`,
    `ws`, `vite`, `zod`, `protobufjs`, `postcss` and `sharp`.
  - CI's `bun run audit:gate` prints "OK — no advisories ≥ high". `scripts/audit-gate.ts` parses only npm's JSON shapes
    (`vulnerabilities`, `advisories`), while `bun audit --json` returns `{ "<package>": [advisory, …] }`. It finds zero
    advisories, so the gate is false-green.
  - Fixing it means upgrading the frontend framework (TanStack Start ≥ 1.168.60, among others) and correcting the gate in
    the same change, then proving R19 on CI's three browsers. That needs the e2e/R19 machinery, and correcting the gate alone
    would turn the `frontend` job red. → routed to the coordinator as a P0-05 defect (the audit gate) for a frontend-deps
    lane. P3-08 owns "no high findings from the automated tools".

## Substitutions

- **S1 `qfull-amo[bloqade_digital]`: `bloqade>=0.32` (meta-package) → its components with the meta-package's own
  specifiers, without bloqade-circuit's `vis` extra:** `bloqade-analog~=0.16.9`,
  `bloqade-circuit[cirq,qasm2,qasm3,qbraid,stim]~=0.15.3`, `bloqade-core~=0.6.8`, `bloqade-lanes~=0.11.9`,
  `bloqade-tsim~=0.1.5`, plus `matplotlib>=3.9.2` and `tqdm>=4.66.5`.
  - Why: `bloqade` 0.36.0 requires `bloqade-circuit[…,vis]`, and `vis` adds PyQt5 (GPL-3.0). No extra of the meta-package
    avoids it.
  - Evidence (R10): the `bloqade` 0.36.0 wheel contains only a README and no code. In the `bloqade-circuit` 0.15.5 wheel,
    `bloqade` is a PEP 420 namespace (no `__init__.py`), so `import bloqade` (the adapter's only import) resolves the same
    way. `bloqade/visual` imports only matplotlib and tqdm, so both are listed directly. PyQt5 is only a matplotlib Qt
    backend, and the `ffmpeg` PyPI package of `vis` is never imported.
  - Licences: bloqade-circuit is Apache-2.0 WITH LLVM-exception; bloqade-core, bloqade-decoders, bloqade-lanes, bloqade-tsim
    and bloqade-analog are Apache-2.0.
  - What is lost: only the Qt interactive window.
- **S2 pre-commit project dependency → `uvx pre-commit`** (D5).

## Removals with replacement

Each GPL package was confirmed on its repository and PyPI page (R10). The repository's GitHub licence:

- block2-preview: GPL-3.0
- python-igraph: GPL-2.0
- pybobyqa: GPL-3.0
- healpy: GPL-2.0
- cosmoGW: GPL-2.0 file, GPLv3 README and PyPI classifier
- PyQt5: GPL v3 on PyPI

Cobaya is LGPL-3.0-or-later with GFDL docs (README, PyPI), and its hard requirement py-bobyqa is GPL. getdist is
LGPL-3.0-or-later. Every adapter keeps its soft import. Every install hint now says the code runs as a separate process and
names the ticket.

| Removed from | Requirement | Why (R11) | Replacement (named) | Capability today |
| --- | --- | --- | --- | --- |
| `qcompass-core[chem]`, `qfull-chemistry[chem]`, `qfull-nuclear[classical]` | `block2>=0.5.3` | GPL-3.0-only, imported in-process as `pyblock2` | separate-process DMRG runner, P2-06 (M13), used by P2-10 for nuclear | `Block2Adapter` / DMRG paths raise `ClassicalReferenceError` naming P2-06; FCI and CCSD(T) via PySCF; nuclear ED ≤ 8 sites. S-chem-2 and S-nuc-4's pyblock2 test skip via `importorskip`, as they always did in CI |
| `qfull-amo[classical]`, `qfull-condmat[classical]` | `netket>=3.21` | hard-requires `igraph` (GPL) | separate-process NQS runner, P2-11 (serves condmat too) | ED ≤ 14 sites (AMO), OTOC ≤ 12 sites; the netket path was never wired; S-amo-4's netket test skips via `importorskip` as before |
| `ucgle-f1[infer]` | `cobaya>=3.5` | hard-requires `py-bobyqa` (GPL-3.0-or-later) | separate-process Cobaya run, P1-09 | `run_posterior(backend="bilby")` (bilby + dynesty, MIT, still in `[infer]`); `backend="cobaya"` raises a RuntimeError naming P1-09 |
| `ucgle-f1[gw]` | `CosmoGW` | GPL | separate process, P1-06 (licence check first, as P1-06 says) | M6 placeholder path; `compute_sgwb`'s CosmoGW branch was itself a placeholder that fell back to it |
| `ucgle-f1[gw]` | `PTAfast` | hard-requires `healpy` (GPL-2.0-only) | separate process, P1-06 | none wired today (only named in the M6 docstring); P1-06 owns the PTA output |
| `ucgle-f1[vllm]` | `vllm>=0.6` | not GPL: vulnerable, and never imported (D2) | the vLLM server as its own process (≥ 0.32.0), reached by the unchanged `VLLMProvider` over HTTP | provider unchanged |
| root `[dependency-groups].dev`, `ucgle-f1[dev]` | `pre-commit` | not GPL: D5 | `uvx pre-commit …` with the same config | unchanged hooks |
| `qfull-amo[bloqade_digital]` | `bloqade>=0.32` | `vis` → PyQt5 (GPL-3.0) | S1 component list | unchanged except the Qt window |

The `gw`, `vllm`, `qfull-amo[classical]` and `qfull-nuclear[classical]` extras stay, empty, as `multifield` did in P0-04. That
way existing install commands keep working. User-facing text updated:

- `block2_adapter.py`, `qfull_chem/classical.py`, `qfull_nuc/classical.py`, `qfull_amo/classical.py`,
  `qfull_cm/classical.py`, `m7_infer/inference.py`
- the READMEs of qcompass-core, qfull-chemistry, qfull-nuclear, qfull-amo and qfull-condmat, and `backend/README.md`
- `docs/qcompass/optional-backends.md` (new section "GPL code: separate process only")

The NVIDIA CUDA wheels that reached the lock only through vLLM/torch left with it. The container images, and their
already-ledgered CUDA/NVIDIA situation, are unchanged.

## Corrected tests

None. No test, assertion, skip, xfail, warning filter, tolerance or fixture changed. The tests that exercise the removed
backends were already `importorskip`-guarded, because CI's `UV_SYNC` never installed `chem`, `classical`, `infer`, `gw` or
`vllm`. They skip as before, and the package suite still reports 7 skipped:

- `qfull_chem/audit/test_s_chem_2.py` (`pyblock2`)
- `qfull_nuc/audit/test_s_nuc_4.py::test_pyblock2_path_documents_install`
- `qfull_amo/audit/test_s_amo_4.py::test_netket_optional_path_documents_install`

No test matched on the install-hint texts that changed (grep for `match=` on them: none).

## BLOCKED-ON-JAMES

None. Every high or critical advisory and every denied licence in PR #3's Python diff is fixed in the dependencies (see the
evidence file for the compare-API result). The npm finding (D11) is routed, not blocked: it needs a frontend-deps lane, not
James.

## 2026-11-02 — lane W0-npm: D11 fixed (the audit gate reads bun; no high or critical advisory left in bun.lock)

Branch `build/w0-npm` from `4de96fa`. Evidence: `docs/build/evidence/P0-05-dependency-review.md`, section "2026-11-02 — npm
side fixed (lane W0-npm)". Earlier sections of this file are unchanged; D11 above is the routing this section closes.

### Decisions

- **N1 The audit gate reads `bun audit --json` and fails closed.** The decision moved to `scripts/audit-gate-lib.ts`;
  `scripts/audit-gate.ts` is the CLI that CI already calls (`bun run audit:gate`, step unchanged).
  - bun 1.4.4 prints one object keyed by package name, each value an array of advisories (`id`, `url` with the GHSA id,
    `severity`, `vulnerable_versions`, …). It exits 0 with `{}` when nothing is found and 1 when anything is found, at any
    severity. It also exits 1, with empty stdout, when it cannot audit at all: no lockfile, registry unreachable (both
    captured). The old gate read npm's shapes only, so bun's object, and the empty stdout, both parsed as "no advisories".
  - Exit codes: 0 pass; 1 one or more high/critical advisories not on the allowlist; 2 the gate cannot decide (output
    that is not exactly bun's shape, exit 1 with no advisories, any exit status other than 0/1, a killed process, a
    malformed `.audit-allowlist.json`). Both non-zero codes fail the CI step.
  - The allowlist format is unchanged (`{ "allowed": [...] }`), matched by GHSA id or bun's numeric id. It does not exist and
    no advisory is exempted.
- **N2 Gate scope: every package `bun audit` checks, production and dev.** The gate was written (`2754ee4`) to run plain
  `bun audit --json`, which covers the whole tree, and fail at high; P0-05's ledger entry kept it as the frontend job's
  audit step. Narrowing it to `--production` would weaken a gate (R4) and would not match "what ships" anyway: vite, the
  TanStack and Cloudflare plugins, tailwind and the router generator, which build the web and server bundles, are in
  `dependencies`. At `4de96fa` 16 of the 17 packages with a high or critical advisory are in the production tree; the
  17th, `brace-expansion`, comes only through eslint/typescript-eslint. Upgrading it cost nothing, so no exemption was
  needed.
- **N3 Upgrades.** Every version was checked on the npm registry: packument, licence, and the registry's advisory
  endpoint queried for each old and new version. The critical advisory and one advisory per overridden or pinned package
  were also read on their GitHub advisory pages (R10). Direct dependencies changed are pinned exactly (R17).

  | Package | `4de96fa` → now | How | High/critical advisories fixed |
  | --- | --- | --- | --- |
  | `@tanstack/react-start` | ^1.167.14 (1.167.39) → 1.168.60 | exact pin | GHSA-qx66-fv34-fjm8 (critical; first patched 1.168.60) |
  | `@tanstack/start-server-core` | 1.167.19 → 1.169.39 | pinned by react-start 1.168.60 | GHSA-qx66-fv34-fjm8 (critical; first patched 1.169.39) |
  | `@tanstack/react-router` | ^1.168.0 (1.168.21) → 1.170.41 | exact pin, the version react-start 1.168.60 pins | none; keeps one router in the tree |
  | `@tanstack/router-plugin` | ^1.167.10 (1.167.22) → 1.168.42 | exact pin, the version start-plugin-core 1.171.49 pins | none; it and router-generator were the last users of zod 3 |
  | `seroval`, `seroval-plugins` | 1.5.2 → 1.7.6 | router-core 1.171.34 asks `^1.6.7` | GHSA-mv8w-475r-vwqw, GHSA-p6vx-979v-rg4c (critical), GHSA-jp82-f5mq-hwhp, GHSA-97r2-qh9m-474h, GHSA-wp97-x4hv-qvhp, GHSA-7rv5-mrxv-xcr9 (first patched 1.6.8; 1.7.6 also clears the moderates up to 1.6.11) |
  | `zod` | ^4.3.6 (4.3.6) and 3.25.76 → 4.6.6 | exact pin; zod 3 left with router-plugin 1.167 | GHSA-mrhx-c7xc-m3w5 (first patched 4.6.6; no 3.x fix exists) |
  | `vite` | ^7.3.1 (7.3.2) → 7.3.7 | exact pin (devDependency) | GHSA-587h-7wmj-h5pm (first patched 7.3.7) |
  | `sharp` | 0.34.5 → 0.35.5 | `overrides` (N4) | GHSA-f88m-g3jw-g9cj, GHSA-rgj7-g3m4-5g8c, GHSA-wq5f-xc86-pv6w (first patched 0.35.5) |
  | `undici` | 7.24.4, 7.25.0 → 7.30.1 | `overrides` (N4) | GHSA-4cwx-7wf7-3272, GHSA-vmh5-mc38-953g, GHSA-vxpw-j846-p89q, GHSA-hm92-r4w5-c3mj, GHSA-rfgv-xxqx-mfg5, GHSA-w293-vg96-wgc3, GHSA-xjj6-f33q-929c, GHSA-4w7w-5xrc-9h26, GHSA-2m5v-pch6-74hx, GHSA-qrxm-fqhp-jwvm (first patched 7.30.1) |
  | `ws` | 8.18.0, 8.20.0 → 8.21.0 | `overrides` (N4) | GHSA-96hv-2xvq-fx4p (first patched 8.21.0) |
  | `brace-expansion` | 1.1.14, 5.0.5 → 1.1.20, 5.0.11 | `bun audit fix --audit-level=high` (lowest safe in range) | GHSA-mh99-v99m-4gvg, GHSA-rgw5-rvv9-x895, GHSA-3jxr-9vmj-r5cp, GHSA-qhr7-859c-m2p7, GHSA-6j4f-fj2g-mc7p |
  | `browserslist` | 4.28.2 → 4.28.7 | same | GHSA-c83g-rgw3-j3cx, GHSA-73wf-gq98-2v4g |
  | `dompurify` | 3.4.1 → 3.4.17 | same | GHSA-mrv2-3pqr-j5jr |
  | `fast-uri` | 3.1.0 → 3.1.7 | same | GHSA-f65p-4m7j-42xc, GHSA-jqff-g426-hqxp, GHSA-7p8r-x3mc-p8w7, GHSA-v2hh-gcrm-f6hx, GHSA-4c8g-83qw-93j6, GHSA-q3j6-qgpj-74h6, GHSA-v39h-62p7-jpjc, GHSA-qw65-cvwx-89v3 |
  | `js-yaml` | 4.1.1 → 4.3.2 | same | GHSA-52cp-r559-cp3m, GHSA-5p4m-2wfm-xmqj, GHSA-2883-xcg3-v3hh |
  | `nanoid` | 3.3.11 → 3.3.18 | same | GHSA-28wg-ghj8-5hjv, GHSA-2v37-7h3g-55p8, GHSA-xwg4-73v4-xw9w |
  | `postcss` | 8.5.9 → 8.5.18 | same | GHSA-6g55-p6wh-862q, GHSA-r28c-9q8g-f849 |
  | `protobufjs` | 7.5.5 → 7.6.1 | same | GHSA-66ff-xgx4-vchm, GHSA-75px-5xx7-5xc7, GHSA-jvwf-75h9-cwgg, GHSA-685m-2w69-288q, GHSA-wcpc-wj8m-hjx6 |
  | `source-map-js` | 1.2.1 → 1.2.2 | same | GHSA-68fv-2mgg-jv7q |

  Newly locked or moved alongside, all MIT unless noted: `@tanstack/*` family (react-start-rsc 0.1.59, start-plugin-core
  1.171.49, router-core 1.171.34, router-generator 1.167.40, start-client-core 1.170.34 and the rest),
  `@tanstack/react-store`/`store` 0.11.2, `unplugin` 3.7.0, `chokidar` 5.0.0, `readdirp` 5.1.1, `srvx` 0.11.22,
  `exsolve` 1.2.0, `fetchdts` 0.1.7, a nested `lightningcss` 1.33.0 (MPL-2.0) under start-plugin-core, `@img/sharp-*`
  0.35.5 (Apache-2.0) with `@img/sharp-libvips-*` 1.3.4 (LGPL-3.0-or-later, weak copyleft, as 1.2.4 was). cheerio and its
  parser tree left with start-plugin-core 1.167. `scripts/licence_gate.py npm node_modules`: 778 packages, 0 violations.
  `src/routeTree.gen.ts` is regenerated by router-generator 1.167.40; only the order of its imports and declarations
  changed.
- **N4 `overrides` for three packages that miniflare and the Cloudflare plugin pin exactly.** `miniflare` 4.20260410.0
  pins `undici` 7.24.4 and `ws` 8.18.0 and asks `sharp` ^0.34.5; `@cloudflare/vite-plugin` 1.32.2 pins `ws` 8.18.0. No
  miniflare 4.x release has all three patched; the first plugin release whose miniflare does is 1.66.0 (miniflare
  5.20261023.1-beta, wrangler 4.154.0: 85 releases later, moving the build and serve toolchain to a miniflare beta). The overrides set exactly the
  versions miniflare 5.x pins itself (`sharp` 0.35.5, `undici` 7.30.1, `ws` 8.21.0). `sharp` is only `import()`ed lazily
  by miniflare's local Images-binding fetcher, and `wrangler.jsonc` declares no Images binding. `undici` and `ws` stay on
  their major. Remove the overrides when `@cloudflare/vite-plugin` is next upgraded to a release whose miniflare pins
  patched versions.
- **N5 The upgrade switches on `src/start.ts`'s security headers; the CSP was fixed so the app still works.** `setResponseHeaders()`
  in start-server-core 1.167.19 iterated its argument with `Object.entries()`, which yields nothing for the `Headers`
  object `src/start.ts` passes, so at `4de96fa` production sent none of the headers (checked: a `4de96fa` response has
  only `Content-Type`). 1.169.39 iterates the `Headers`, so CSP, HSTS, X-Frame-Options, COOP, Referrer-Policy,
  Permissions-Policy, nosniff and DNS-prefetch-off are sent from this commit on. The CSP as written broke the app:
  - Start streams its bootstrap and dehydrated data as inline scripts, which `script-src 'self' https://plausible.io` blocks,
    so nothing hydrated (every cosmology page rendered blank). Fix: a fresh 128-bit nonce per response, created in the
    middleware, passed through the request context (`cspNonce`) to `getRouter()` (`ssr.nonce`, via `src/lib/csp-nonce.ts`),
    which Start stamps on every script it emits. `'unsafe-inline'` stays absent in production.
  - `@rjsf/validator-ajv8` (`QcompassManifestForm`, every `/domains/$domain/configurator`) compiles each schema with
    `new Function`, so without `'unsafe-eval'` validation fails ("Error compiling schema") and the form never submits
    (`e2e/chemistry-h2-flow.spec.ts` failed until it was added). Production `script-src` therefore keeps `'unsafe-eval'`.
    Removing it needs a validator that does not generate code (an R10 substitution); not done here.
  - `connect-src` gains the origin of `VITE_API_URL` (and its ws/wss twin for the visualization socket) and of a custom
    `VITE_POSTHOG_HOST`, when set, the same way it already took the Supabase origin. Otherwise the live backend would be
    blocked the day it is configured.
  - `upgrade-insecure-requests` is sent only when the request is https. On a plain-http origin (wrangler dev on CI and
    locally) it can only turn same-origin asset loads into https requests the server cannot answer. Chromium exempts
    loopback; Firefox and WebKit could not be checked here.
  The policy moved into `src/lib/csp.ts` (unit tests `src/lib/csp.test.ts`); every other directive is unchanged.
- **N6 Router 1.170 changes the app had to follow.** `ErrorComponentProps.error` is now `unknown`: the four error components
  take `ErrorComponentProps` and print `error instanceof Error ? error.message : String(error)` (the same text for an
  `Error`). `RouteMatch.globalNotFound` was renamed `_notFound`: the root `head()` reads `_notFound`. Without that,
  `tsc` fails and a global 404 would silently lose its title and `noindex`.
- **N7 R19.** Not one rebaseline; `e2e/__screenshots__/**` and `R19.sha256` are untouched. Proof in the evidence file:
  - zero-tolerance before/after renders of the three routes with the spec's own steps;
  - the real cosmology spec, which gives the same per-route pixel counts against the committed (CI-browser) baselines at
    `4de96fa` and now.
  The only variation is a pre-existing ±1-level anti-aliasing flip of 8 pixels on `/visualizer/kawai-kim-natural`, which
  `4de96fa` itself produces.
- **N8 Residual advisories (none blocks the gate).** 18 moderate, 6 low, in `@babel/core`, `@humanfs/node`,
  `@opentelemetry/core`, `@vitest/mocker`/`vitest`, `brace-expansion`, `esbuild`, `fast-uri`, `fflate`, `katex`, `minimatch`,
  `postcss`, `postcss-selector-parser` and `protobufjs`. Several have in-range fixes (`bun audit fix --dry-run` lists them);
  the rest wait on their dependents (`@opentelemetry` 0.208 pins core 2.2.0, `wrangler` pins esbuild 0.27.3, `katex` 0.18
  is outside `^0.16`). Left for P3-08 ("no high findings") so this lane stays minimal.

### Removals with replacement

- `npm audit --json` fallback in `scripts/audit-gate.ts` → a fail-closed error (exit 2). There has been no
  `package-lock.json` since P0-03, so `npm audit` could only answer ENOLOCK, which the old parser also read as OK.
  `bun audit` is the only auditor that reads `bun.lock`, and CI pins bun 1.4.4.
- `CSP_DIRECTIVES` constant in `src/start.ts` → `buildCsp()` in `src/lib/csp.ts` (same directives, plus N5).

### Tests

No test, assertion, skip, tolerance or fixture expectation was weakened, and no screenshot baseline changed. Added:
- `scripts/audit-gate.test.ts`: 19 tests over real bun 1.4.4 output in `scripts/fixtures/audit-gate/`. They cover parsing
  the 130-advisory `4de96fa` report, failing on high and on critical, passing on moderate-only and clean output, passing on
  the upgraded lock, the allowlist, and failing closed on unreachable registry, missing lockfile, truncated/non-JSON/npm-shaped
  output, unknown severity, exit 1 with `{}`, exit 2/127 and a killed process.
- `src/lib/csp.test.ts`: 8 tests.

`vitest.config.ts` now also includes `scripts/**/*.test.ts`, and `tsconfig.json` type-checks `scripts/**/*.ts`. Both are
additions; neither removes anything.

### For James / CI to confirm

- Firefox and WebKit could not run here. The CI `playwright` job is the check for R19 on those two browsers and for N5's
  headers there.
- N5 also sends `X-Frame-Options: DENY` and `frame-ancestors 'none'` in dev, as `src/start.ts` always intended. If the
  Lovable editor previews the dev server in an iframe, that preview will refuse to load; decide whether dev should keep
  them.
- PostHog/Plausible scripts beyond the listed hosts are untested (no keys here).

### BLOCKED-ON-JAMES

None.
