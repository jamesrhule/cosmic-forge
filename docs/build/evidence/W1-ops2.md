# W1 — Gate 1 round 3B, ops2 lane (deploy, release and docs residuals)

Branch `build/w1-ops2`, based on `15e4e3c`. Lane notes:
`docs/build/lanes/W1-ops2.md` (finding ids, decisions, corrected tests,
BLOCKED-ON-JAMES). Findings: the round-3A OPS verifier's new findings and
residuals (`round3a-result.json`, `ops.verify`).

## How "before" was measured

`git worktree add --detach` of `15e4e3c` in the scratchpad; the new test files
were copied into its `backend/tests/` under a `_r3b_` prefix, together with
this branch's `test_security_gate1_deploy.py` (the corrected harness) and
`backend/tests/data/wrangler_build_output.json`; its `node_modules` was a link
to this branch's install (the same wrangler 4.82.2), and the tests ran with
this branch's venv against the `15e4e3c` workflows, `mkdocs.yml` and scripts.
The scratch checkout was removed afterwards. A failure counts only when it is
the finding's own reason; one test that fails there with `FileNotFoundError`
(the allowlist script does not exist on `15e4e3c`) is listed and not counted.

Versions: Python 3.12.13 (uv-managed venv), uv 0.11.32, bun 1.4.4, node
22.22.0, wrangler 4.82.2, @cloudflare/vite-plugin 1.32.2, jq 1.7, Playwright
1.59.1 with the sandbox Chromium (`PW_CHROMIUM_PATH`), mkdocs 1.6.1 (from
`docs/requirements.txt`), Postgres 16 (the backend harness's own cluster).

## Per finding

| Id | Fix | Test(s) | 15e4e3c (reason) | After |
|---|---|---|---|---|
| SEC-M2-allowlist (MEDIUM, deploy.yml:395) | New `web` step after the download and the `jq` refusal: `node scripts/check_wrangler_deploy_config.mjs "$WRANGLER_CONFIG"` from the fresh checkout. Expected config = wrangler's `unstable_readConfig(wrangler.jsonc)` + the plugin's output step; the build's config, read with `JSON.parse` and with wrangler's parser, must equal it in every key and value; `main` a relative `.js`/`.mjs` regular file in `dist/server`; no symlink or special file in `dist/` | `test_security_gate1_deploy_r3b.py::test_m2_build_config_cannot_pull_runner_files_or_bindings_into_the_upload` (24 cases), `::test_m2_real_build_output_still_deploys_with_its_modules` (positive control), `::test_m2_allowlist_runs_from_the_checkout_after_the_download`, `::test_m2_allowlist_mirrors_the_locked_plugin_with_the_same_wrangler`; corrected `test_security_gate1_deploy.py` (22) | 24/24 cases fail for the bug. Token in the upload (`--dry-run --outdir`): the verifier's case (module `ba8c0f50…-environ`), `base_dir` + `find_additional_modules` + `Text` rule (module `environ`), symlink `dist/server/assets/leak.js` → `/proc/self/environ` (module `assets/leak.js`). The other 21 (extra rule, `text_blobs`, `data_blobs`, `wasm_modules`, `site.bucket`, `assets.directory` absolute and `../../..`, `main` outside `dist/server` and absolute, `upload_source_maps`, R2/KV/D1/service bindings, a route, a var, an `env` section, `__proto__`, a unicode-escaped key, symlinks among the public assets and for a directory): "wrangler ran with the token on this config", the token step ran after only the `jq` step. Step-order test fails: no allowlist step. Positive control passes on both. The mirror test fails with `FileNotFoundError` (no script on `15e4e3c`; not counted) | 24/24 refused before the token step, none in the upload; 27/27 pass |
| c6-guard-case (LOW, deploy.yml:65) | Same first step in `gcp`, `web-check`, `web-build`, `web`: anything but exactly `staging` needs `GITHUB_REF` exactly `refs/heads/main` or matching `refs/tags/qcompass-v*` (bash, case-sensitive), else `exit 1` | `test_security_gate1_deploy_r3b.py::test_production_proceeds_only_from_exact_main_or_release_tag` (12 cases: job `if` evaluated, then the first step run in bash), `::test_every_job_starts_with_the_same_unconditional_ref_check` | 6 must-not-proceed cases fail for the bug: production on `refs/heads/MAIN`, `refs/heads/Main`, `refs/heads/mAIN` (workflow_call), `refs/tags/QCOMPASS-V9.9.9` (push), `refs/tags/Qcompass-v1.0.0`, and `Production` on `refs/heads/MAIN`: "gcp: … on refs/heads/MAIN" (the job `if` admits it and the first step is the secrets check). The 6 legitimate/feature-branch cases pass on both. Structure test: "gcp: the ref check is not the first step" | 13/13 pass |
| c6-pypi-pins (LOW, release-please.yml:58) | setup-uv `version: "0.11.32"` + `checksum` (sha256 of the release's linux x86_64 archive); `uv build … --build-constraints packages/build-constraints.txt --require-hashes`; `\|\| true` removed | `test_security_gate1_release_r3b.py` (5 of 6): `::test_pypi_job_installs_the_pinned_uv_with_its_checksum`, `::test_pypi_build_backend_comes_from_the_hash_lock`, `::test_a_failed_package_build_fails_the_publish_job` (fake `uv` on PATH that fails for `qfull-hep`), `::test_a_clean_build_builds_every_package_under_the_lock`, `::test_publish_pypi_hides_no_failure` | all 5 fail for the bug: "setup-uv installs 'latest (the default)', not an exact uv"; `uv build … --out-dir dist \|\| true` lacks `--build-constraints`/`--require-hashes`; "a package that fails to build must stop the publish (no `\|\| true`)" (the step exits 0); the 11 recorded `uv build` calls carry no constraints; `\|\| true` in the build step | 5/5 pass |
| docs-polyfill (LOW, mkdocs.yml:66) | polyfill.io removed; `mathjax@3` → `mathjax@3.2.2` | `test_docs_site_scripts.py` (4) | 3 fail for the bug: `https://polyfill.io/v3/polyfill.min.js?features=es6` (compromised domain), "script host not allowed: https://polyfill.io/…", the MathJax URL is `mathjax@3` not `mathjax@3.2.2`. `test_docs_pages_embed_no_remote_script` passes on both (guard) | 4/4 pass |
| SEC-L5-wif (routing residual) | Documentation only (`docs/qcompass/deployment.md`, "One deployer per environment"); `BLOCKED-ON-JAMES:gcp-per-environment-deployer` | `test_security_gate1_deploy_r3b.py::test_gcp_credentials_come_from_the_target_environment` (guard: the deployer, WIF provider and project are read only by the `gcp` job, from its target environment) | passes (no code bug; n/a) | pass |
| c6-cuda12-publish (residual) | `publish-docker` matrix `exclude: [{flavour: cuda12}]` + `BLOCKED-ON-JAMES:cuda-image-r11` notice; Dockerfile kept | `test_security_gate1_release_r3b.py::test_cuda12_image_is_not_published_while_r11_is_open` | fails for the bug: "publish-docker pushes ['cpu', 'cuda12']" | pass |
| ci-action-pins (residual) | Every ci.yml action pinned to the commit its major ref resolves to, with `# vX.Y.Z`; `no-cache: true` on every setup-bun | `test_ci_actions_pinned.py` (4) | 2 fail for the bug: "not pinned to a full commit SHA with # vX.Y.Z: - uses: actions/checkout@v4"; "licences: setup-bun restores a cache". `test_one_release_is_one_commit_across_the_pinned_workflows` and `test_jobs_and_dependency_review_settings_are_unchanged` pass on both (guards) | 4/4 pass |

The corrected harness (`test_security_gate1_deploy.py`, 22 tests) passes on
`15e4e3c` and on this branch (lane notes, Corrected tests).

### Repro outputs

Refusal messages on this branch (harness run of single cases):

```text
bundling with a Text rule over /proc/self/environ: exit 1, token step ran False
::error::refusing dist/server/wrangler.json: config.rules: [{"type":"ESModule","globs":["**/*.js","**/*.mjs"]},{"type":"Text","globs":["**/environ"]}] is not [{"type":"ESModule","globs":["**/*.js","**/*.mjs"]}]
::error::refusing dist/server/wrangler.json: config.assets: missing
::error::refusing dist/server/wrangler.json: config.no_bundle: false is not true
an R2 binding: ::error::refusing dist/server/wrangler.json: config.r2_buckets: [{"binding":"B","bucket_name":"other"}] is not []
a key smuggled through __proto__: ::error::refusing dist/server/wrangler.json: config.__proto__: not in the config the build generates
a key spelled with a unicode escape: ::error::refusing dist/server/wrangler.json: config.site: not in the config the build generates
a symbolic link among the public assets: ::error::refusing dist/server/wrangler.json: dist/client/env.txt: symbolic link
main outside dist/server: ::error::refusing dist/server/wrangler.json: main: "../../wrangler.jsonc" is not a relative .js/.mjs path inside dist/server
assets.directory outside dist: ::error::refusing dist/server/wrangler.json: config.assets.directory: "../../.." is not "../client"
```

The old hand-written positive-control config
(`{"name": "x", "main": "index.js", "compatibility_date": "2025-09-24", "no_bundle": true}`)
is refused by the allowlist: `config.name: "x" is not "tanstack-start-app"` and
40 missing keys (each reported for both parsers).

Real build output: `bun run build` on this branch, then
`node scripts/check_wrangler_deploy_config.mjs dist/server/wrangler.json` →
exit 0. The whole `web` job after the download (the `jq` step, the allowlist,
`wrangler deploy --dry-run --outdir`) run on a copy of the real `dist/` (the
workspace path substituted, as on the runner): exit 0, 62 modules in the
upload, none containing the token sentinel.

Expected-config derivation on the real build output: the derived config and
`dist/server/wrangler.json` (44 top-level keys) differ only in `main`
(`@tanstack/react-start/server-entry` before the plugin, `index.js` after),
`no_bundle`, `rules`, `assets.directory` and the dropped `build`/`define`/
empty `unsafe`, exactly the plugin's output step.

Build backend lock, by hand with uv 0.11.32 (`uv build --package
qcompass-core --out-dir <tmp> --build-constraints <file> --require-hashes`):
the generated lock → sdist and wheel built; every hatchling hash replaced
with zeros → `hash mismatch … Computed: sha256:08ecf754…` (also with a warm
cache); an unhashed `hatchling==1.32.4` → "In `--require-hashes` mode, all
requirements must be pinned upfront with `==`, but found: `hatchling`".

uv 0.11.32 archive: `curl -L
https://github.com/astral-sh/uv/releases/download/0.11.32/uv-x86_64-unknown-linux-gnu.tar.gz`
→ sha256 `aab924fd522efd06f1c5f3b93a243864fc453132c94b2dc49f1371b528a4b967`,
equal to the release's `.sha256` file.

MathJax: npm registry — `mathjax` 3.2.2, published 2022-06-08T17:48:38Z,
`license: Apache-2.0`, `dist-tags.latest` 4.1.3; the tarball's sha512 equals
the registry's `integrity`
(`sha512-Bt+SSVU8eBG27zChVewOicYs7Xsdt40qm4+UpHyX7k0/O9NliPc+x77k1/FEsPsjKPZGJvtRZM1vO+geW0OhGw==`)
and it contains `package/es5/tex-mml-chtml.js` (1 173 007 bytes,
`sha384-Wuix6BuhrWbjDBs24bXrjf4ZQ5aFeFWBuKkFekO2t8xFU0iNaLQfp2K6/1Nxveei`).
`cdn.jsdelivr.net` is not reachable from this sandbox (proxy 403). Docs site
built with the locked tools: `15e4e3c` → scripts `bundle.d7400e89.min.js`,
`mathjax@3/es5/tex-mml-chtml.js`, `polyfill.io/v3/polyfill.min.js?features=es6`
(polyfill.io in 6 generated HTML files); this branch → the bundle and
`mathjax@3.2.2/es5/tex-mml-chtml.js` only, polyfill.io in 0 files (nav
warnings unchanged).

### Action pins in ci.yml (resolved 2026-11-02)

`git ls-remote https://github.com/<owner>/<repo>` for the major ref the
workflow used (annotated tags peeled), and the exact tag on the same commit;
commit dates from a depth-1 fetch of each SHA:

| Action | Ref used | Commit | Exact tag | Commit date |
|---|---|---|---|---|
| actions/checkout | v4 (tag) | 11d5960a326750d5838078e36cf38b85af677262 | v4.4.0 (as deploy.yml, release-please.yml) | 2026-07-16 |
| actions/dependency-review-action | v4 (branch) | 2031cfc080254a8a887f58cffee85186f0e49e48 | v4.9.0 | 2026-03-03 |
| astral-sh/setup-uv | v6 (annotated tag d0d8abe6…) | d0cc045d04ccac9d8b7881df0226f9e82c39688e | v6.8.0 | 2025-09-30 |
| oven-sh/setup-bun | v2 (tag) | 0c5077e51419868618aeaa5fe8019c62421857d6 | v2.2.0 (as deploy.yml) | 2026-03-14 |
| actions/upload-artifact | v4 (tag) | ea165f8d65b6e75b540449e92b4886f43607fa02 | v4.6.2 | 2025-03-19 |
| actions/setup-node | v4 (tag) | 49933ea5288caeca8642d1e84afbd3f7d6820020 | v4.4.0 | 2025-04-02 |

`diff` of ci.yml against `15e4e3c` with the `@<sha> # vX.Y.Z` suffixes
reverted to `@vN` and the seven `no-cache: true` lines removed: only the new
header comment (three lines and a blank line) differs.

## R19

Measured by rendering the three R19 pages in Chromium (1440×900, reduced
motion, the readiness checks, `networkidle`, `freezeMotion` and footer mask of
`e2e/cosmology-byte-identity.spec.ts`) from two production builds served by
`wrangler dev`: `15e4e3c` (scratch checkout) and this branch. A scratch
Playwright config wrote the `15e4e3c` renders to the scratchpad, then compared
this branch's renders against them with `maxDiffPixels: 0`: `/`,
`/visualizer`, `/visualizer/kawai-kim-natural` — 3 passed, pixel-identical.
`dist/client` of the two builds is byte-identical; `dist/server` differs only
because three server chunks embed the checkout path (and the hashed chunk
names follow). The branch changes no file under `src/`, `public/`, the build
config or `e2e/__screenshots__`. Visible change on R19 pages: none.

## Suites

Run on this branch's final tree (4 CPUs shared with other lanes).

| Check | Result |
|---|---|
| Backend fast: `cd backend && uv run --frozen pytest -q -m "not slow"` | 756 passed, 3 deselected, 1 xfailed (the parked V2 η_B xfail); 55 of them are this lane's new tests. A first run, with the e2e builds running beside it, had 1 failure: `test_security_gate1.py::test_l3_hung_handler_is_abandoned_and_the_job_fails_with_job_timeout` ("the handler was stopped": under load the handler's child process had not written its `started` file within the 0.5 s limit). That test and the worker are untouched here; it passed 3/3 alone and in the unloaded full rerun quoted here |
| Backend slow: `-m slow` | 3 passed, 757 deselected |
| Frozen audit: `uv run --frozen pytest audit -q -m "not slow"` | 92 passed, 1 deselected |
| Frozen audit: `uv run --frozen pytest audit -q -m slow` | 1 passed, 92 deselected |
| Drift alarm: `dirhash -i '*.pyc' '__pycache__' '.pytest_cache' --algorithm sha256 backend/audit/physics` | `42805c73538df5eb0f9eb109ead9a541253d5371d71eac5ea04be0ffaf8e92dd` = `golden.lock`; `git diff --quiet 15e4e3c HEAD` over `backend/audit/physics`, `golden.lock`, the drift-alarm workflow, `e2e/__screenshots__`, PLAN/LEDGER/PROGRESS, `supabase/migrations`, `src`, `public`: unchanged |
| Packages: `uv run --frozen pytest packages -q --import-mode=importlib` | 350 passed, 7 skipped |
| `bun run lint` | exit 0: 0 errors, the same 15 pre-existing `react-refresh` warnings |
| `bunx prettier --check .` | clean |
| `bunx tsc --noEmit` | clean |
| `bun run test` (vitest) | 22 files, 119 tests passed |
| `bun run build` | built; `dist/server/wrangler.json` passes the allowlist (exit 0) |
| `scripts/check_r19.sh` | 9 PNGs match R19.sha256 (before and after the e2e run) |
| `scripts/gen_sdk_types.sh --check` | SDK types match the API's OpenAPI document |
| `uv lock --check` | exit 0 (557 packages; `uv.lock` unchanged) |
| Playwright chromium: `bunx playwright test e2e/smoke.spec.ts e2e/synthetic-fixture-badge.spec.ts --project=chromium` | 15 passed (4 smoke, 11 synthetic-fixture-badge) |
| ruff on the new test files | `ruff check` clean, `ruff format --check` clean |

Not run here: the workflows themselves (deploy and release-please run only on
`main`/tags; CI-PENDING) and `actionlint` (not available in this sandbox).

## Round 4 correction (R4-FEOPS, `build/w1-r4feops`)

The by-hand build check above covered `qcompass-core` only. Running
publish-pypi's whole loop shows that the seven qfull-* packages could not
build a wheel. Their `[tool.hatch.build.targets.wheel.force-include]` added
`instances/` a second time, and hatchling refuses that ("A second file is
being added to the wheel archive"). Without `|| true`, every release would
have failed and published nothing. The fix, and a packages-suite test that
runs the build step verbatim with the real uv, are in
`docs/build/lanes/W1-r4-feops.md` and `docs/build/evidence/W1-r4-feops.md`.
