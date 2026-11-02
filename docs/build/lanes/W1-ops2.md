# W1 ops2 lane notes (`build/w1-ops2`, Gate 1 round 3B)

Base `15e4e3c`. Scope: the deploy, release and docs residuals the round-3A OPS
verifier left open (`scratchpad/round2/round3a-result.json`, `ops.verify`),
plus two routing residuals. No backend or frontend source changed. Evidence:
`docs/build/evidence/W1-ops2.md`.

| Id                  | Finding                                                                                                               |
| ------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `SEC-M2-allowlist`  | MEDIUM, deploy.yml:395: the wrangler.json refusal is a 3-key blocklist; a build-written config can pull runner files (incl. `/proc/self/environ`) or bindings into the deploy |
| `c6-guard-case`     | LOW, deploy.yml:65: the production guard compares refs without case (`refs/heads/MAIN`, `refs/tags/QCOMPASS-V…`)       |
| `c6-pypi-pins`      | LOW, release-please.yml:58: publish-pypi (id-token: write) installs uv "latest" and an unpinned hatchling; `\|\| true` hides build failures |
| `docs-polyfill`     | LOW, mkdocs.yml:66: polyfill.io (taken over in 2024) and an unpinned `mathjax@3` on every docs page                    |
| `SEC-L5-wif`        | routing residual: the proposed WIF condition accepts `environment == 'staging'` from any ref in front of one deployer |
| `c6-cuda12-publish` | residual: publish-docker publishes the cuda12 image with NVIDIA's proprietary libraries (R11)                         |
| `ci-action-pins`    | residual: ci.yml uses tag-pinned actions and a cached setup-bun                                                       |

Each finding was reproduced on `15e4e3c` before it was fixed; the new tests
fail there for the finding's reason (evidence file).

## Decisions

- **[SEC-M2-allowlist] Reproduced.** The verifier's case (the real config plus
  `no_bundle: false` and a `Text` rule over `**/environ`, and an `index.js`
  that imports `/proc/self/environ`) passes `15e4e3c`'s refusal step, and
  `wrangler deploy --dry-run --outdir` writes an upload module that contains
  `CLOUDFLARE_API_TOKEN=fake-CLOUDFLARE_API_TOKEN`. Of the 24 planted configs
  and symbolic links in the new test, 3 put the token in the upload on
  `15e4e3c` (that case, `base_dir` + `find_additional_modules` + a `Text`
  rule, and a symlink `dist/server/assets/leak.js` → `/proc/self/environ`)
  and the other 21 reach the token step unrefused (with `assets.directory:
  "../../.."` wrangler set out to upload the whole workspace, `node_modules`
  included, as public assets).
- **[SEC-M2-allowlist] An allowlist derived from the checkout.** A new step in
  the `web` job, after the round-3A `jq` refusal and before the token step,
  runs `node scripts/check_wrangler_deploy_config.mjs "$WRANGLER_CONFIG"` from
  the job's fresh checkout with its locked wrangler (installed with
  `--ignore-scripts`). Nothing from `dist/` is executed.
  - **Expected config.** wrangler's own reader, `unstable_readConfig` over
    `wrangler.jsonc` with `preserveOriginalMain` (the call
    `@cloudflare/vite-plugin` makes), then the plugin's output step as read
    from `node_modules/@cloudflare/vite-plugin/dist/index.mjs` 1.32.2:
    `readWorkerConfig` deletes `alias`, `base_dir`,
    `find_additional_modules`, `minify`, `no_bundle`, `preserve_file_names`,
    `site`, `tsconfig`, `build`, `define`; `outputConfigPlugin` sets `main`
    (the entry chunk's file name), `no_bundle: true`,
    `rules: [{ESModule, ["**/*.js", "**/*.mjs"]}]`, `assets.directory`
    (client output relative to server output, `"../client"`), drops an empty
    `unsafe`, and adds `upload_source_maps: true` only when the build makes
    source maps. Derived this way, the expected config matched the real
    `dist/server/wrangler.json` exactly (all 44 top-level keys), apart from
    `main`.
  - **Comparison.** The build's config is read twice, with `JSON.parse` and
    with `experimental_readRawConfig` (the jsonc parser `wrangler deploy`
    uses), and both must equal the expected config in every key and value at
    every depth: no extra or missing key, arrays equal in order. So `rules`
    is exactly the plugin's, there is no `build`, `base_dir`, `site`,
    `text_blobs`, `data_blobs`, `wasm_modules`, `tsconfig`, `alias`,
    `define`, `env`, `routes` or `upload_source_maps`, every binding list is
    the empty list the repository's `wrangler.jsonc` gives, and `vars` is
    `{}`. A `__proto__` key is an extra key for `JSON.parse`, and for the
    jsonc parser (which assigns it, so it sets the prototype) a non-plain
    object; both refuse it.
  - **Paths.** `main` is the only value the build chooses: it must match
    `^[A-Za-z0-9_][A-Za-z0-9_.-]*(/[A-Za-z0-9_][A-Za-z0-9_.-]*)*\.m?js$` (so
    no absolute path, no `.` or `..` segment, no backslash) and be a regular
    file whose real path is inside `dist/server`. `rules` globs are the
    plugin's relative `**/*.js`, `**/*.mjs` under `base_dir`, which defaults
    to `main`'s directory inside `dist/server`. `assets.directory` must be
    exactly `"../client"`, the plugin's fixed relative value, which resolves
    to `dist/client`; it is the only `..` allowed. `configPath` and
    `userConfigPath` are absolute by construction; they must equal the deploy
    job's own `<checkout>/wrangler.jsonc` (on GitHub-hosted runners both jobs
    use `/home/runner/work/cosmic-forge/cosmic-forge`), and wrangler ignores
    the file's values anyway: `normalizeAndValidateConfig` (wrangler-dist
    `cli.js` line 4099 onwards) takes both from its arguments.
  - **Symbolic links.** Everything under `dist/` must be a regular file or a
    directory (checked with `lstat`, nothing followed); `dist`,
    `dist/server`, `dist/client` and `dist/server/wrangler.json` must exist as
    such.
  - **Why `upload_source_maps` is refused.** A source map comment can name any
    file, and the build does not make source maps today. If it starts to, the
    deploy is refused until the allowlist is extended on purpose.
  - **Round 3A rejected an allowlist** because the plugin writes about 45
    top-level keys that change between versions. Deriving them with
    wrangler's own reader removes that cost: the defaults follow the locked
    wrangler. Only the plugin's output step is mirrored, and
    `test_m2_allowlist_mirrors_the_locked_plugin_with_the_same_wrangler` fails
    on any change to the locked plugin (1.32.2) or wrangler (4.82.2; the
    plugin depends on exactly that version, and there is one copy in
    `node_modules`). A lock bump therefore fails the test, not a deploy,
    until the step and the fixture are checked again.
  - **The round-3A `jq` step stays** as a first layer, and for its `.env`
    check. The old test's structure check finds it by its `jq`/`build` text.
  - **Runtime.** `node` from the runner, the same interpreter
    `./node_modules/.bin/wrangler` already runs on in the token step.
- **[c6-guard-case] A case-sensitive first step in every job.** `gcp`,
  `web-check`, `web-build` and `web` now start with the same step:
  ```bash
  if [ "$TARGET_ENV" != staging ] \
    && [ "$GITHUB_REF" != refs/heads/main ] \
    && [[ "$GITHUB_REF" != refs/tags/qcompass-v* ]]; then
    echo "::error::…"; exit 1
  fi
  ```
  bash's `!=` and `[[ … == pattern ]]` are case-sensitive. It has no `if`, no
  `uses` and no `env`, so it always runs before anything else in the job,
  including the environment jobs' secret checks. Anything other than
  exactly `staging` is held to the production rule, so an odd-cased
  `Staging` from a feature branch also fails closed (no caller sends one:
  `workflow_dispatch` offers `staging`/`production`, release-please passes
  `production`). A failed `gcp` or `web-check` skips the jobs that need it.
  The job-level `if` guard is unchanged.
- **[c6-pypi-pins] Pinned code in the job that can mint the PyPI token.**
  - `astral-sh/setup-uv` stays at v3.2.4 (`caf0cab7…`); v6 turns its cache
    on by default on hosted runners. It now gets `version: "0.11.32"` (CI's
    `UV_VERSION`, the images' uv) and `checksum:
    aab924fd522efd06f1c5f3b93a243864fc453132c94b2dc49f1371b528a4b967`, the
    sha256 of `uv-x86_64-unknown-linux-gnu.tar.gz` from the 0.11.32 release.
    Checked by downloading the asset and its published `.sha256`; v3.2.4's
    `validateChecksum` throws on a mismatch.
  - `uv build … --build-constraints packages/build-constraints.txt
    --require-hashes`. `packages/build-constraints.in` (`hatchling`) →
    `packages/build-constraints.txt` by `uv pip compile --generate-hashes
    --python-version 3.12 --exclude-newer 2026-10-19`: hatchling 1.32.4,
    packaging 26.3, pathspec 1.1.1, pluggy 1.7.0, tomlkit 0.15.2,
    trove-classifiers 2026.9.21.13, 12 hashes. All eleven published packages
    declare `requires = ["hatchling>=1.24"]` and `build-backend =
    "hatchling.build"`. Checked with uv 0.11.32: `qcompass-core` builds
    (sdist and wheel); with one hatchling hash changed the build is refused
    ("hash mismatch"), also with a warm cache; with an unhashed
    `hatchling==1.32.4` it is refused ("all requirements must be pinned
    upfront with `==`" under `--require-hashes`). The packages' own
    `[build-system]` is unchanged.
  - `|| true` removed: a package that fails to build fails the job before
    the publish step, so no partial set is published.
  - `uv python install 3.12` is unchanged: with uv pinned it resolves to
    3.12.13, checked against uv's own embedded checksums.
- **[docs-polyfill]** `extra_javascript` is now only
  `https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js`. Checked on
  the npm registry: 3.2.2 is the newest 3.x (`latest` is 4.1.3, a new major
  not taken), published 2022-06-08, Apache-2.0; the tarball's sha512 matches
  the registry's `integrity`, and it contains `es5/tex-mml-chtml.js`
  (1 173 007 bytes). jsdelivr itself is not reachable from this sandbox. The
  polyfill was for IE11; MathJax 3's es5 build needs none. A site built with
  the locked docs tools (mkdocs 1.6.1) loads only the theme bundle and that
  URL; `15e4e3c`'s build loads polyfill.io on 6 pages.
- **[SEC-L5-wif] Documentation only.** `docs/qcompass/deployment.md` now has
  "One deployer per environment": one deployer account per environment
  (preferably one project each), the provider's attribute mapping and exact
  attribute condition (repository id; staging only through `deploy.yml`;
  production only from `refs/heads/main` or `refs/tags/qcompass-v*` with
  that ref's own `deploy.yml`), and `roles/iam.workloadIdentityUser` bindings
  keyed on `attribute.environment`. No new secret name is needed:
  `GCP_SERVICE_ACCOUNT`, `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_PROJECT_ID`
  are already secrets of each GitHub environment, read by the `gcp` job from
  its environment (`test_gcp_credentials_come_from_the_target_environment`
  pins that). The proposed `GCP_API_SERVICE_ACCOUNT` and
  `GCP_WORKER_SERVICE_ACCOUNT` are per environment in the same way.
- **[c6-cuda12-publish] Skipped, not deleted.** `publish-docker`'s matrix
  keeps `flavour: [cpu, cuda12]` and adds `exclude: [{flavour: cuda12}]`, so
  only the cpu image is pushed, and the job writes a
  `BLOCKED-ON-JAMES:cuda-image-r11` notice to the release summary. Re-enabling
  is deleting the `exclude`. `docker/Dockerfile.cuda12` stays (R2), and
  `deploy.yml` still builds it into the environment's private Artifact
  Registry for `qcompass-worker-gpu`: James's own Cloud Run project, not a
  distribution, so not changed (stated in the question).
  `test_security_gate1_release.py::test_what_each_job_publishes_is_unchanged`
  still passes because it reads `matrix.flavour`, which is kept; the new
  `test_cuda12_image_is_not_published_while_r11_is_open` checks the
  effective matrix. That old test is not weakened or edited.
- **[ci-action-pins] Pinned to what the tags pointed at.** Each action is
  pinned to the commit its major ref resolves to today (`git ls-remote`,
  annotated tags peeled), so CI runs exactly what it ran before:
  `actions/checkout` v4 → v4.4.0 `11d5960a326750d5838078e36cf38b85af677262`
  (the same pin as deploy.yml and release-please.yml);
  `actions/dependency-review-action` v4 (a branch) → v4.9.0
  `2031cfc080254a8a887f58cffee85186f0e49e48`; `astral-sh/setup-uv` v6 →
  v6.8.0 `d0cc045d04ccac9d8b7881df0226f9e82c39688e`; `oven-sh/setup-bun` v2 →
  v2.2.0 `0c5077e51419868618aeaa5fe8019c62421857d6` (as deploy.yml);
  `actions/upload-artifact` v4 → v4.6.2
  `ea165f8d65b6e75b540449e92b4886f43607fa02`; `actions/setup-node` v4 →
  v4.4.0 `49933ea5288caeca8642d1e84afbd3f7d6820020`. Commit dates (from a
  shallow fetch of each SHA) 2025-03-19 to 2026-07-16, all at least two weeks
  old. Every `oven-sh/setup-bun` step also gets `no-cache: true`: the same
  bun version is installed, but it is downloaded instead of restored from a
  cache that CI jobs running `bun install` lifecycle scripts can save into
  (deploy.yml already does this; one shape per concern). Job ids, job names,
  steps, `with:` values and the dependency-review settings are otherwise
  byte-for-byte unchanged; a diff with the pins and `no-cache` lines removed
  leaves only the new header comment.

## Corrected tests (old → new, proof)

- **[SEC-M2-allowlist] `backend/tests/test_security_gate1_deploy.py`, the
  positive control's config.**
  - Old: `_CLEAN = {"name": "x", "main": "index.js", "compatibility_date": "2025-09-24", "no_bundle": True}`,
    with `test_m2_clean_build_output_deploys` asserting
    `code == 0 and token_step_ran` and `"deployed" in output` for it.
  - New: `_CLEAN` is the real `dist/server/wrangler.json` from `bun run build`
    (`backend/tests/data/wrangler_build_output.json`, the build checkout path
    written as `${WORKSPACE}`); the assertions are unchanged.
  - Proof the old one is wrong: the finding requires the deploy job to
    refuse every config except the one the build generates. The old `_CLEAN`
    is a hand-written four-key config the build never produces (`name` `x`,
    no `assets`, `rules` or binding lists; the real one has 44 top-level
    keys), so a correct fix must refuse it. With the old `_CLEAN` the
    allowlist refuses it on this branch for exactly that reason
    (`config.name: "x" is not "tanstack-start-app"` and 40 missing keys). The
    real config passes on `15e4e3c` and on this branch, so coverage is kept,
    and raised: the seven planted cases now sit on the real config, and the
    positive control now runs the allowlist step as well as the dry run.
- **[SEC-M2-allowlist] Same file, the harness `_run_after_handover`.** No
  assertion changed. The workspace now holds what the deploy job's fresh
  checkout holds besides `node_modules` (`wrangler.jsonc` and
  `scripts/check_wrangler_deploy_config.mjs`, each copied when the commit has
  it) and an empty `dist/client` with an `index.html` (the real config's
  assets directory); `${WORKSPACE}` in the planted config becomes the
  workspace path; two optional parameters, `outdir` (the dry run's
  `--outdir`) and `plant` (adds files after `dist/` is written), serve the
  new tests. Proof: without the checkout's files the new step cannot run, so
  the old harness would refuse every config, including the real one, for a
  reason that is not the policy; the step order, the env handling and the
  dry-run substitution are unchanged. The file's 22 tests pass on this
  branch, and also on `15e4e3c` with the corrected harness (the planted
  `build`/`containers`/`unsafe`/`.env` cases are refused there by the `jq`
  step, as before).

## Removals with replacement

- **[docs-polyfill]** `https://polyfill.io/v3/polyfill.min.js?features=es6` →
  nothing. It polyfilled ES6 for old browsers; MathJax 3's `es5` build is
  self-contained. `mathjax@3` → `mathjax@3.2.2` (same file).
- **[c6-cuda12-publish]** The cuda12 leg of `publish-docker` →
  `exclude`d until `BLOCKED-ON-JAMES:cuda-image-r11` is answered. The image
  is still built from `docker/Dockerfile.cuda12` by `deploy.yml` (GPU worker)
  and can be published again by deleting the `exclude`.
- **[c6-pypi-pins]** `|| true` after `uv build` → none (a failed build fails
  the job).

## Routed to later tickets

- **[ci-action-pins] Other workflows.** `e2e-baselines.yml`
  (`actions/checkout@v4`, `oven-sh/setup-bun@v2`), `phase3-verdict.yml`
  (`actions/checkout@v4`, `astral-sh/setup-uv@v3`,
  `actions/upload-artifact@v4`) and `codeql.yml` (`actions/checkout@v4`,
  `github/codeql-action/{init,analyze}@v3`) are still tag-pinned; this lane
  was scoped to ci.yml. `ucglef1-drift-alarm.yml` (`actions/checkout@v4`,
  `astral-sh/setup-uv@v3`) is frozen (R5) and needs a plan-author correction
  like correction 10 to be pinned.
- **[ci-action-pins] uv cache in CI.** ci.yml's `setup-uv` steps keep
  `enable-cache: true` (the uv package cache, keyed on `uv.lock`); turning it
  off changes CI's behaviour beyond pinning. Same cache-poisoning class as
  the bun cache, lower reach (uv installs from `uv.lock`); for the CI
  hardening ticket.
- **[c6-pypi-pins] Build and publish in separate jobs.** PyPA's recommended
  shape builds in a job without `id-token: write` and hands the dists over.
  It adds a job, which `test_security_gate1_release.py`'s per-job permission
  table would have to list; left for the release ticket. With uv and the
  build backend pinned and hashed, the code that runs next to the OIDC token
  is now fixed by the lock.
- **[docs-polyfill] Subresource integrity for MathJax.** mkdocs 1.6.1's
  `extra_javascript` cannot carry an `integrity` attribute; a theme override
  (`custom_dir` with a `main.html` script tag) could. The hash of
  `es5/tex-mml-chtml.js` from the npm tarball is
  `sha384-Wuix6BuhrWbjDBs24bXrjf4ZQ5aFeFWBuKkFekO2t8xFU0iNaLQfp2K6/1Nxveei`.
- **[c6-cuda12-publish]** Unchanged from round 3A: CI never builds the CUDA
  image, and the licence gate never sees the cuda12 extra; both belong with
  James's R11 answer.

## BLOCKED-ON-JAMES

- **[c6-cuda12-publish] `BLOCKED-ON-JAMES:cuda-image-r11`.** The question, as
  in `docs/qcompass/deployment.md` ("The CUDA image and R11"): may
  `ghcr.io/jamesrhule/qcompass-runtime:cuda12` be published? It is built
  from `nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04` (NVIDIA's CUDA runtime
  and cuDNN libraries under NVIDIA's CUDA and cuDNN licence agreements) and
  adds, from `uv.lock` through ucgle_f1's `cuda12` extra, jax-cuda12-plugin
  and jax-cuda12-pjrt 0.12.0.1 (Apache-2.0) and 13 `nvidia-*-cu12` wheels
  (PyPI licence `LicenseRef-NVIDIA-Proprietary`). R11 allows only permissive
  or weak-copyleft code in distributed container images. Yes: record the
  exception to R11 and delete the `exclude` in `publish-docker`. No: the
  public cuda12 image stays unpublished. The private GPU worker image that
  `deploy.yml` builds for James's own Cloud Run is not a distribution and is
  left as it is unless James says otherwise.
- **[SEC-L5-wif] `BLOCKED-ON-JAMES:gcp-per-environment-deployer`.** GCP IAM,
  James's (R13): one deployer service account per environment (preferably
  one project per environment), each GitHub environment's existing
  `GCP_SERVICE_ACCOUNT`, `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_PROJECT_ID`
  set to that environment's values, and the provider mapping, attribute
  condition and `workloadIdentityUser` bindings exactly as in
  `docs/qcompass/deployment.md`. No new secret name; the proposed
  `GCP_API_SERVICE_ACCOUNT` and `GCP_WORKER_SERVICE_ACCOUNT` (round 3A) are
  set per environment the same way.
- Still open from round 3A and unchanged here:
  `BLOCKED-ON-JAMES:production-environment-protection`,
  `BLOCKED-ON-JAMES:GCP_API_SERVICE_ACCOUNT`,
  `BLOCKED-ON-JAMES:GCP_WORKER_SERVICE_ACCOUNT`.
