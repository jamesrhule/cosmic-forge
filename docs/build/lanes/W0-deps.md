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
  - `main.ts` computes `issueFound ||= await printLicensesBlock(...)`. Once vulnerabilities are found, the licence block is
    short-circuited and never printed. That is why the PR #3 log showed only vLLM: the licence failures (block2, healpy,
    igraph, py-bobyqa) were hidden behind it.
  - This lane's acceptance is stricter (R11): no added package whose expression contains a denied identifier anywhere, unless
    its official licence was read and is not GPL (D8). The evaluator re-implements the action with the same SPDX libraries at
    the action's locked versions (`spdx-expression-parse` 4.0.0, `@onebeyond/spdx-license-satisfies` 1.0.1,
    `spdx-license-ids` 3.0.20) and adds the stricter scan.
- **D2 vLLM: the in-process engine leaves; the provider stays.** `ucgle-f1[vllm]` installed `vllm` 0.20.2 (1 critical, 8
  high), which dragged in `transformers` 4.57.6 (4 high), `torch` and the CUDA wheels. Nothing imports `vllm`:
  `m8_agent/models/local_vllm.py` is an HTTP client of a vLLM OpenAI-compatible server at `$VLLM_URL`, using `httpx` (a core
  dependency). A patched release exists (0.32.0), but raising the floor would put vLLM 0.33's exact pins (`torch==2.14.0`,
  `numba==0.65.0`, `fastapi<0.137`, `setuptools<81`, `transformers<5.21`) on the whole universal lock, for a package no code
  imports. The extra stays, empty, so `pip install ucgle_f1[vllm]` still works. `docs/qcompass/optional-backends.md` says
  to run the server separately at ≥ 0.32.0. The provider (PLAN Part 7, P5-01) is unchanged.
- **D3 Braket extras conflict with ucgle-f1, like `qcompass-router[braket]` already did.** The task's description ("1.88.1
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

The CUDA/NVIDIA wheels that left the lock with vLLM are the ones the ledger already tracks for the images. The images are
unchanged.

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
