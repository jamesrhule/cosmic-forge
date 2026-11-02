# Evidence: W1 round-4 lane R4-FEOPS (`build/w1-r4feops`)

Base `6e0f15d`. Commits, in order:
- `9210c95`: item 4, every package builds;
- `0a64779`: items 1 and 3, the preview and the η_B fixture schema;
- `68bdede`: item 2, the linter;
- `9652976`: item 5, the cryptography floor;
- then these notes.

Lane notes: `docs/build/lanes/W1-r4-feops.md`.

Tools: uv 0.11.32, Python 3.12, bun (`bun.lock`), vitest 4.1.12, Playwright
Chromium 1243 (`PW_CHROMIUM_PATH=/opt/pw-browsers/chromium`).

## Per item: reproduction, test, before → after

| # | Reproduced on `6e0f15d` | New tests | On `6e0f15d` (fails for the bug) | On this branch |
| - | ----------------------- | --------- | -------------------------------- | -------------- |
| 4 | `uv build --package qfull-hep --out-dir <tmp> --build-constraints packages/build-constraints.txt --require-hashes` builds `qfull_hep-0.1.0.tar.gz`, then "A second file is being added to the wheel archive … force-include", exit 1 | `packages/qcompass/tests/test_release_builds.py`, 24 tests: the step builds every workspace package; 11 wheels + 11 sdists; for each package, its wheel ships every tracked file once and its sdist carries the sources | the test file run against a `6e0f15d` tree: 1 passed, 23 errors; every build-dependent test errors in the module fixture with "publish-pypi's build step failed (2); nothing would be published: … ValueError: A second file is being added to the wheel archive at the same path: `qfull_chem/instances/femoco_toy.yaml`" (the step stops at the first qfull package) | 24/24 pass (≈12 s with a warm uv cache) |
| 4 NIT | release-please.yml:5 said images push to `qcompass-runtime:{cpu,cuda12}` | n/a (comment) | n/a | header says cpu only while `BLOCKED-ON-JAMES:cuda-image-r11` is open; OPS2's `test_security_gate1_release_r3b.py` 6/6 pass, unchanged |
| 1 | `samplePotential("natural", D15 default)` spans 5.1262e-9 to 5.1267e-9 (relative span 8.9e-5): a flat line | `src/lib/__tests__/potentialEvaluator.test.ts`, 11 tests: the grid, 7 parameter sets against M2's V(ψ), each kind's default covered, the D15 default is a curve, f/M_PL_GEV = 8.7. `backend/tests/test_potential_vectors.py`, 4 tests: `units.M_PL_GEV` equals the engine's `M_PL_GEV`; the preview vectors are what M2 computes now (rel 1e-12); every kind's Configurator default is covered; the snippet verdicts are the parser's | with the old `potentialEvaluator.ts`, 7 of 11 fail. Examples: natural D15 default "expected 5.059119167498899e-9 to be ≤ 6.74e-20"; hilltop default "expected 5626.7 to be ≤ 5.6e-6"; "expected 0.00008910907161132706 to be greater than 0.99" | 11/11 and 4/4 pass |
| 3 | `RunResultShape` accepts `eta_B: {}` and `{value: null}` without a refusal | `src/lib/__tests__/fixtureSchemas.test.ts`, 5 tests | 2 of 5 fail: "refuses a missing or null number with no refusal reason" and "refuses a blank refusal reason" | 5/5 pass; `syntheticFixtures`, `etaB` and `etaBDisplay` still pass (28 tests across the 4 files) |
| 2 | the linter errors on `def V` with a docstring (the backend accepts it); it passes lambda, if/else, comparisons, `% // << & ~`, brackets, strings, `phi.real`, an uncalled `exp`, and a second line, all of which the backend refuses | `potentialValidator.test.ts` gains 49 tests: one per backend vector (47: 12 accept, 35 refuse), coverage of both verdicts, and the reworded def message | with the old `potentialValidator.ts`, 21 fail, e.g. `accept: "def V(psi):\n    \"\"\"Starobinsky.\"\"\"\n    return …"`, `refuse: "1e-10 * phi\n2 * phi"`, `refuse: "lambda phi: phi**2"`, `refuse: "phi > 0"`, `refuse: "exp"`, `refuse: "def V(psi):\n    return psi\nphi"` | 55/55 pass (the 6 pre-existing tests unchanged) |
| 5 | `uv run --frozen pytest packages -q --import-mode=importlib`: 1 failed, `test_published_group_declares_the_floor[ucgle-f1[<dependencies>]->cryptography]` ("ucgle-f1[<dependencies>] pulls pyjwt -> cryptography but does not declare 'cryptography>=50.0.0' (found lower bound None)"). The same test, run from a `6e0f15d` worktree, fails the same way | existing test | fails (above) | `test_security_floors.py` 30/30 pass; `uv lock --check` green |

The backend-generated vectors are written by
`uv run python scripts/gen_potential_vectors.py`. `--check` exits 0 on this
branch.

### M2's V(ψ) for the Configurator defaults (from the vectors)

| kind | params (API units) | V over ψ ∈ [-2, 4] M_Pl [M_Pl⁴] |
| ---- | ------------------ | ------------------------------- |
| starobinsky | M = 1.3e-5 | 5.53e-14 … 2.15e-9 |
| natural | f = 2.118624e19 GeV, Λ⁴ = 2.563334027300118e-9 | 1.09e-14 … 2.66e-10 (f_a = 8.7) |
| natural | f_a = 8.7, Λ = 0.0071154324599829784 (M2 names, Kawai–Kim fixture) | identical to the row above |
| natural | f = 7e16 GeV, Λ⁴ = 2.5e-7 (benchmarks, gb-off-control) | 1.35e-11 … 5.00e-7 |
| hilltop | V0 = 1e-7, mu = 1e16 GeV, p = 4 | -9.00e4 … -1.44e-4 (μ = 0.0041 M_Pl) |

The old preview had drawn the natural default as
Λ⁴(1 + cos(ψ/211.9)) ≈ 2Λ⁴, flat to 9e-5.

## R19: Chromium before/after render

Two production builds (`bun run build`, default flags) were made: `6e0f15d`
(a worktree) and `68bdede` (this branch with items 1–3; item 5 touches no
frontend file). Each was served on workerd (`wrangler dev`, ports
4520/4521). The byte-identity spec's procedure was then run with a script
(`scratchpad/r19tools/shoot.cjs`):
- Desktop Chrome at 1440×900 with reduced motion;
- the spec's ready text, then `networkidle`;
- motion frozen and the footer masked;
- a full-page screenshot.

The script then compares the two renders pixel by pixel in a canvas.

| Route | Size | Differing pixels | sha256 (before = after) |
| ----- | ---- | ---------------- | ----------------------- |
| `/` | 1440×2478 | 0 | `c7241c10d5655712fba80905314fb61a2736d2b84281fd4ddddf451f0b796265` |
| `/visualizer` | 1440×900 | 0 | `5a5f8000df12f5486393264f237645105be7893d386f045b8338ee1d61154510` |
| `/visualizer/kawai-kim-natural` | 1440×900 | 0 | `2f3c3daa23b692379932d6b2c869162815eea81db0b49ff4e8e93df42e2e88b0` |

All three pages are byte-identical, and the render of `/` shows the
Configurator with its form column collapsed, as the spec expects.
`scripts/check_r19.sh`: "R19 baselines locked: 9 PNGs match R19.sha256". No
file under `e2e/__screenshots__/` changed.

`e2e/cosmology-byte-identity.spec.ts` against the committed Chromium PNGs
fails in this sandbox: `/` 17,384 px (ratio 0.01), `/visualizer` 17,940 px
(0.02), `/visualizer/kawai-kim-natural` 8,775 px (0.01). The renders of
`6e0f15d` and this branch are byte-identical, so the base fails the same
way. The difference is the pending rebaseline (a) (Decisions 13, 15, 16: the
synthetic badges are on these pages, and the committed PNGs predate them).
It is not this lane's doing.

## Full suites (this branch)

| Check | Result |
| ----- | ------ |
| `bun run lint` | 0 errors, 15 warnings (pre-existing, e.g. `src/lib/auth.tsx` react-refresh) |
| `bunx prettier --check .` | all files formatted |
| `bunx tsc --noEmit` | clean |
| `bun run test` (vitest) | 34 files, 304 tests passed |
| `bun run build` | built (inside `scripts/e2e_serve.sh` and for the R19 render) |
| Playwright Chromium: `smoke`, `synthetic-fixture-badge`, `cosmology-regression`, and `cosmology-byte-identity`'s first test (`PW_CHROMIUM_PATH=/opt/pw-browsers/chromium E2E_PORT_DEFAULT=4530 E2E_PORT_DOMAINS=4531 bunx playwright test --project=chromium …`) | 23 passed. The 3 byte-identity screenshots fail as described above (pending rebaseline (a); identical on `6e0f15d`) |
| `scripts/check_r19.sh` | 9 PNGs match R19.sha256 |
| Backend fast: `cd backend && uv run --frozen pytest -q -m "not slow"` (at `68bdede`; `9652976` changes only a dependency declaration and the lock entry, no installed package) | 880 passed, 3 deselected, 1 xfailed |
| Packages: `uv run --frozen pytest packages -q --import-mode=importlib` | at `68bdede`: 403 passed, 7 skipped, 1 failed (item 5, pre-existing on `6e0f15d`). At `9652976`: 404 passed, 7 skipped (including the 24 `test_release_builds.py` tests, with the real uv) |
| `uv lock --check` | current (423 packages) |
| `scripts/gen_sdk_types.sh --check` | "SDK types match the API's OpenAPI document." |
| `uv run python scripts/gen_potential_vectors.py --check` | exit 0 |
| `uv run --frozen ruff check` on the new Python files | clean |
| gitleaks (`gitleaks git . --redact --no-banner --exit-code 1`), before each push | no leaks found |
