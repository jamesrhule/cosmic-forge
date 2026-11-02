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

## 2026-11-02 (round 2 follow-up) — verifier findings on W0-deps (lane W0-PY2)

Branch `build/w0-py2` (from `build/w0-deps` @ `4de96fa`). It fixes the five findings of the W0-deps verifier. The
dependency-review job and its settings are unchanged. `uv.lock` goes from 408 to 404 entries: `qbraid` 0.13.0,
`qbraid-core` 0.6.40, `pyqasm` 1.3.0 and `classy` 3.4.1.0 leave, and no locked version changes (each re-lock was a plain
`uv lock`, no upgrade flags). Evidence: `docs/build/evidence/P0-05-dependency-review.md`, section of the same date.

### Decisions

- **D12 qbraid-core is proprietary, so bloqade-circuit's `qbraid` extra leaves `qfull-amo[bloqade_digital]` (S1 amended).**
  - Licence (R10): the `qbraid-core` 0.6.40 wheel's `dist-info/licenses/LICENSE` is the "qBraid Commercial Software
    License". It allows use only by authorised qBraid customers, for personal, academic and educational purposes; it
    prohibits commercial use and the distribution of modifications. PyPI's `License` field says `Proprietary`. That is
    neither permissive nor weak copyleft, so R11 fails. `qbraid` itself is Apache-2.0 but hard-requires qbraid-core.
  - Chain in the lock: `qfull-amo[bloqade-digital]` → `bloqade-circuit[qbraid]` → `qbraid` → `qbraid-core`. Nothing
    else depended on `qbraid`.
  - Fix: `bloqade-circuit[cirq,qasm2,qasm3,stim]~=0.15.3`.
  - Capability: `bloqade.qbraid` still imports, because it imports `qbraid` only under `TYPE_CHECKING`. No other
    bloqade-circuit module imports it (wheel read). What is lost is the qBraid target's use without a provider: it takes
    a `QbraidProvider` from the `qbraid` package, which a user with a qBraid licence installs themselves. QCompass never
    uses that target.
  - Isolated env (`UV_PROJECT_ENVIRONMENT=<scratch> uv sync --frozen --package qfull-amo --extra bloqade-digital --extra
    dev`): `bloqade`, `.squin`, `.qasm2`, `.analog`, `.visual`, `.lanes`, `.tsim`, `.stim`, `.cirq_utils`, `.pyqrack` and
    `.qbraid` import. `qbraid`, `qbraid_core`, `pyqasm` and PyQt5 are absent. qfull-amo tests: 18 passed, 1 skipped
    (netket `importorskip`); S-amo-3 runs with bloqade there.
- **D13 Licence walk of every package reachable from any workspace extra or group (R10, R11).**
  - Method: every registry package in `uv.lock` (395 before, 391 after) was checked against PyPI's per-version JSON
    (`license_expression`, `license`, licence classifiers). Reverse-dependency paths came from every member's base
    dependencies, each extra and each dependency group.
  - Packages whose metadata was empty or not clearly permissive or weak copyleft were checked further: their PyPI wheel's
    licence files, or their repository when no licence file exists.
  - Result: two removals (`qbraid-core` under D12, `classy` under D14). Two packages are kept but flagged for James:
    `camb` (D15) and `pyqrack-cpu`/Qrack (D16).

  | Package | Metadata | Checked licence | Reached from | Verdict |
  | --- | --- | --- | --- | --- |
  | `qbraid-core` 0.6.40 | Proprietary | qBraid Commercial Software License (wheel) | `qfull-amo[bloqade-digital]` | removed (D12) |
  | `classy` 3.4.1.0 | none | none granted (D14) | `ucgle-f1[cosmo]` | removed (D14) |
  | `camb` 2.0.5 | `LicenseRef-LGPLv3-arxiv` | LGPL-3.0-or-later plus conditions (D15) | `ucgle-f1[cosmo]` | kept, flagged |
  | `pyqrack-cpu` 1.89.0 | MIT | MIT wrapper; bundles `libqrack_pinvoke.so` (Qrack, LGPL-3.0; see D16) | `qfull-amo[bloqade-digital]` (hard requirement of bloqade-circuit) | kept, flagged |
  | `azure-core` 1.41.0 | none | MIT (wheel `License-Expression`, LICENSE) | azure extras | permissive |
  | `beliefmatching` 0.2.0 | none | Apache-2.0 (wheel LICENSE) | `qfull-amo[bloqade-digital]` | permissive |
  | `bloqade-circuit` 0.15.5, `kirin-toolchain` 0.22.21 | none | Apache-2.0 with LLVM exceptions (wheel LICENSE) | `qfull-amo[bloqade-digital]` | permissive |
  | `bloqade-core` 0.6.14, `bloqade-decoders` 0.6.1, `bloqade-lanes` 0.11.9 | none | Apache-2.0 (wheel LICENSE) | `qfull-amo[bloqade-digital]` | permissive |
  | `dynesty` 3.1.0 | none | MIT (wheel LICENSE) | `ucgle-f1[infer]` | permissive |
  | `mypy-extensions` 1.1.0 | none | MIT (wheel) | dev extras | permissive |
  | `myst-nb` 1.4.0 | none | BSD-3-Clause (wheel) | `ucgle-f1[dev]` | permissive |
  | `qiskit-addon-dice-solver` 0.0.0.dev0 | Apache-2.0 | a 9.8 kB placeholder wheel, no Dice binary | `qfull-chemistry[dice]` | permissive |
  | `numpy`, `scipy`, `scipy-openblas32` | BSD | bundled libgfortran under GPL-3.0-with-GCC-exception (runtime library exception) | many | permissive, standard bundling |
  | `matplotlib` | PSF-based | bundled FreeType under `FTL OR GPL-2.0-or-later` (FTL chosen) | many | permissive |
  | `gmpy2` 2.3.2, `python-flint` 0.9.0, `progressbar` 2.5 | LGPL-3.0-or-later; MIT AND LGPL-3.0-or-later; BSD or LGPL | as metadata | `ucgle-f1[highprec]`, `[boltzmann]` | weak copyleft |
  | `docutils` 0.22.4 | BSD, GPL, public domain classifiers | D8 | `ucgle-f1[dev]` | permissive (D8) |

  Every other package has a permissive SPDX expression or classifier on PyPI. The 38 long licence texts were scanned in
  full for GPL, AGPL, non-commercial, proprietary and customer-only terms. The only hits are numpy, scipy,
  scipy-openblas32, matplotlib and pandas (the table above, plus pandas' bundled PSF history) and plain "All rights
  reserved" BSD notices.
- **D14 `classy` (CLASS) leaves `ucgle-f1[cosmo]`: no licence is granted.**
  - The PyPI 3.4.1.0 sdist has no licence file and no licence metadata. Its only licence words are a BSD header on a
    vendored generator script, an "All rights reserved" notice in `include/parallel.h`, and a GPLv3 snippet credited in
    `CPU.py`.
  - The `lesgourg/class_public` repository has no LICENSE file and no sidebar licence. Its README says only "You can use
    CLASS freely, provided that in your publications, you cite at least the paper `CLASS II: Approximation schemes`",
    which is a citation request, not a licence. With no grant, R11 cannot be met.
  - Nothing imports classy (only a docstring and a mypy override name it). PLAN P1-06 names CAMB for tensor and TB/EB
    spectra with "classy optional", and has P1-06 verify each licence first. The replacement is CAMB, which stays in
    `[cosmo]`. If James or P1-06 obtains a licence statement from the CLASS authors, classy can return.
- **D15 CAMB stays in `ucgle-f1[cosmo]`, flagged for P1-06 and James.**
  - `LICENCE.txt`: the code is licensed under "the GNU Lesser General Public License as published by the Free Software
    Foundation, either version 3 of the License, or any later version"; the documentation is GFDL-1.3.
  - It adds three conditions:
    - any publication using its results must go to arXiv no later than to a journal;
    - confirmed bugs must be reported;
    - the licence must appear on all copies.
  - The code licence is weak copyleft, and the conditions restrict neither commercial use nor linking. So it is kept
    under R11's weak-copyleft allowance. Nothing imports it yet.
  - Whether the arXiv condition is acceptable for PHC's use is a policy question for James (see the item below).
- **D16 Qrack inside `pyqrack-cpu`: kept, flagged.** `bloqade-circuit` hard-requires `pyqrack-cpu~=1.70`.
  - pyqrack is MIT, and its wheel bundles the Qrack shared library. Qrack's `LICENSE.md` is LGPL-3.0, and its
    `qstabilizer.{hpp,cpp}` headers say "Licensed under the GNU Lesser General Public License V3".
  - But Qrack's README states that "The `QStabilizer` partial simulator 'engine' is adapted from CHP by Scott Aaronson,
    for non-commercial use." `www.scottaaronson.com` is not reachable from this session, so CHP's own terms could not
    be read.
  - By its metadata and source headers it is weak copyleft, so it stays. Removing it would remove bloqade-circuit, the
    whole digital bloqade path (R2).
  - Whether the README note restricts commercial use of the bundled library is a question for James.
- **D17 Security floors reach the published wheels.** Root `[tool.uv] constraint-dependencies` (D6) constrain only the
  workspace lock. Each published requirement group whose locked third-party closure pulls a floored package now declares
  the floor itself. The lock walk found these groups:
  - `cryptography>=50.0.0`:
    - `qcompass[azure]` and `[ibm]`
    - `qcompass-core[azure]` and `[ibm]`
    - `qcompass-router[azure]`, `[ibm]` and `[pasqal]`
    - `qfull-amo[bloqade_digital]` and `[pasqal]`
    - `qfull-chemistry[ibm]`, `qfull-condmat[ibm]`, `qfull-hep[ibm]` and `qfull-nuclear[ibm]`

    They come in through azure-identity, azure-storage-blob and msal (azure-quantum); requests-ntlm and pyspnego
    (qiskit-ibm-runtime); pyjwt[crypto] (pulser via pasqal-cloud); and jwskate (bloqade-lanes via qlam-core).
  - `amazon-braket-sdk>=1.117.0`: newly in `qcompass-router[quera]`, `qfull-amo[bloqade_analog]`,
    `qfull-amo[bloqade_digital]` and `qfull-condmat[analog]` (through `bloqade-analog`, which requires
    `amazon-braket-sdk>=1.78.0`). It is already in `qcompass-router[braket]`, `qfull-hep[ionq]` and `qfull-nuclear[ionq]`.

  Every one of these edges is unconditional in the lock, so the floors add no package to any install. With the floor,
  a resolver cannot pick azure-quantum 3.13.0 (it caps `cryptography<=46.0.3`). It picks 3.12.0, as the lock does, so
  3.13.0 needs no explicit exclusion. A new test, `packages/qcompass/tests/test_security_floors.py`, enforces this:
  - It walks `uv.lock` for every workspace member listed in root `[tool.uv.workspace]` (all of `packages/*` and
    `backend`).
  - It asserts that each pulling group declares the floor, with no marker.
  - It asserts that the walk still finds the known pullers, so it cannot pass by finding nothing.
  - It asserts that the root constraints keep both floors.
  - Removing the floor from `qcompass-core[azure]` makes it fail, as checked.
- **D18 pre-commit pinned (R17).** Every invocation is `uvx pre-commit@4.7.0 …`: the README, the root `pyproject.toml`
  and `backend/pyproject.toml` comments. Neither Taskfile nor CI invokes pre-commit. 4.7.0 is the latest release on
  PyPI (2026-10-12), MIT, with no advisory listed.
- **D19 Offline evaluator scope.** `scripts/dependency_review_eval.cjs` now filters with `c.scope || "runtime"`, exactly
  like the action's `filterChangesByScopes` (`src/filter.ts` at v4.9.0, read). Every change in today's compare has a
  scope (457 added and 674 removed are runtime, 1 added and 242 removed are development), so the verdict does not change.
- **D20 Separate-process wording made exact (R18).** The adapters still soft-import pyblock2, cobaya and CosmoGW
  in-process when present (R2 keeps them). Messages, docstrings, READMEs, pyproject comments and
  `docs/qcompass/optional-backends.md` now say what is true today:
  - no QCompass extra installs the package;
  - the separate-process runner is delivered by P2-06 (DMRG), P2-11 (NQS), P1-09 (Cobaya) or P1-06 (CosmoGW and
    PTAfast);
  - until then, a copy you install yourself is imported into your own process.

  netket and PTAfast are not imported anywhere, and the text now says so. The S-chem-2 README row now says the test
  needs a pyblock2 you installed yourself and is skipped otherwise. `m6_gw/sgwb.py` is unchanged, which avoids conflicts
  with W1-phys3; its behaviour is described in the docs. No test matched on the changed texts. `test_s_cm_4` matches
  "exceeds dense-matrix", which is kept.
- **D21 W1 merge (adds to D10).** W1 adds `pyjwt[crypto]>=2.9` to `ucgle-f1`'s base dependencies, and a `workers/`
  member. After the merge and `uv lock`, `test_security_floors.py` will require `cryptography>=50.0.0` in
  `backend/pyproject.toml` `dependencies`, and in any `workers/` group that pulls it directly. Add the floor there in the
  merge commit rather than weakening the test.

### Removals with replacement (this follow-up)

| Removed from | Requirement | Why (R11) | Replacement (named) | Capability today |
| --- | --- | --- | --- | --- |
| `qfull-amo[bloqade_digital]` | bloqade-circuit's `qbraid` extra (`qbraid` → `qbraid-core`) | qBraid Commercial Software License (customers only, no commercial use) | none needed in QCompass. Users with a qBraid licence install `qbraid` themselves and pass its `QbraidProvider` to `bloqade.qbraid.qBraid` | every bloqade module imports, `bloqade.qbraid` included; qfull-amo tests 18 passed / 1 skipped in the isolated env |
| `ucgle-f1[cosmo]` | `classy` | no licence granted (D14) | CAMB (`camb>=1.5`, still in `[cosmo]`), the PLAN P1-06 primary for CMB tensor and TB/EB spectra | unchanged: nothing imported classy |

### Corrected tests

None. No test, assertion, skip, xfail, tolerance or fixture changed. New: `packages/qcompass/tests/test_security_floors.py`
(23 tests: 20 parametrised groups plus 3 guards). The package suite goes from 341 passed / 7 skipped to 364 passed /
7 skipped, with the same seven skips.

### For James

Neither item blocks this lane or the dependency review. Both are licence-policy rulings:

- CAMB's arXiv condition (D15).
- Qrack's CHP-derived "non-commercial use" note inside `pyqrack-cpu` (D16).

### Ledger entries to fold in (LEDGER.md is not edited by lanes)

- `[P0-05]` S1 amended: bloqade-circuit's `qbraid` extra removed. qbraid-core is proprietary; the replacement is
  "none needed" (D12).
- `[P0-05]` `classy` removed from `ucgle-f1[cosmo]` because no licence is granted; the replacement is CAMB (D14).
- `[P0-05]` Security floors carried into published extras; new test `test_security_floors.py` (D17).
- `[P0-05]` pre-commit pinned at 4.7.0 (D18).
- `[P0-05]` Licence notes for James: CAMB (D15) and Qrack/CHP (D16).
