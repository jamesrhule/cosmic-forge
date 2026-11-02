# W1 round-4 lane R4-FEOPS (`build/w1-r4feops`)

Base `6e0f15d`. Scope: four findings the round-3B verifiers left for the
frontend and release side (`scratchpad/round2/round3b-result.json`, lanes FE3
and OPS2, `verify.newFindings`). Evidence: `docs/build/evidence/W1-r4-feops.md`.

| # | Id (verifier) | Finding |
| - | ------------- | ------- |
| 1 | FE3, LOW, `src/lib/potentialEvaluator.ts:46` | With Decision 15's natural default the Configurator's V(ψ) preview is a flat line: the browser divides f by 1e17 GeV, not by M_Pl, and draws 1 + cos where M2 uses 1 − cos |
| 2 | FE3, NIT, `src/lib/potentialValidator.ts:83` | The linter's shape rules differ from the backend parser (API3, Decision 17) |
| 3 | FE3, NIT, `src/lib/fixtureSchemas.ts:83` | `RunResultShape` accepts a null or absent η_B value for bundled fixtures |
| 4 | OPS2, MEDIUM, `.github/workflows/release-please.yml:87` (+ NIT `:5`) | publish-pypi fails on every release: no qfull-* package can build a wheel. The header says the cuda12 image is pushed |
| 5 | found by this lane's full `packages` run | `test_security_floors.py::test_published_group_declares_the_floor[ucgle-f1[<dependencies>]->cryptography]` fails on `6e0f15d`: the backend's `pyjwt[crypto]` pulls cryptography without declaring the `>=50.0.0` floor |

Each finding was reproduced on `6e0f15d` first, and each new test fails there
for the finding's reason (evidence file). Item 5 has no new test: the
existing one already fails on `6e0f15d`.

## Decisions

- **[4] Cause and fix.** Reproduced: `uv build --package qfull-hep …
  --build-constraints packages/build-constraints.txt --require-hashes`
  builds the sdist, then hatchling refuses the wheel ("A second file is being
  added to the wheel archive … force-include"). Each qfull-* pyproject listed
  `src/<pkg>/instances` in `[tool.hatch.build.targets.wheel.force-include]`
  on top of `packages = ["src/<pkg>"]`, which already ships every file under
  the package, the instance YAMLs included. The seven force-include tables
  are removed. `[build-system]` (`hatchling>=1.24`, `hatchling.build`) and
  `packages/build-constraints.txt` are unchanged, so OPS2's exact pins stand.
- **[4] The CI check.** No new CI job. `packages/qcompass/tests/test_release_builds.py`
  is in the suite the existing `packages` job runs (`pytest packages`). It
  reads publish-pypi's build step from `release-please.yml` and runs it
  verbatim with the real uv. It runs in a scratch directory, where a
  `packages` symlink resolves the step's relative paths and `UV_PROJECT`
  points uv at the workspace, so nothing is written into the checkout and the
  loop exists in one place only (R20). It checks:
  - 11 wheels and 11 sdists, one per workspace package;
  - each wheel ships every git-tracked file under its `packages` directory,
    each exactly once;
  - each sdist carries its `pyproject.toml` and every tracked file under `src/`.

  The packages job has network access for hatchling's hash-locked download
  and already has uv and Python 3.12. uv also writes a `.gitignore` into the
  out-dir. The publish action uploads `dist/*`, which no dotfile matches, so
  the test ignores dotfiles.
- **[4] Header.** The release-please header now says the Docker image pushes
  to `qcompass-runtime:cpu` only while `BLOCKED-ON-JAMES:cuda-image-r11` is
  open. A paragraph names the new build test.
- **[1] Parameterisation.** The preview now evaluates M2's expressions
  (`compile_potential`) with `Potential.engine()`'s conversions:
  - starobinsky: unchanged, (3/4)M²(1 − e^(−√(2/3)ψ))²;
  - natural: Λ⁴(1 − cos(ψ/f_a)) with f_a = f / M_PL_GEV;
  - hilltop: V0(1 − (ψ/μ)^p) with μ = mu / M_PL_GEV.

  Hilltop had the same 1e17 normalisation as natural, so it is fixed too. The
  verifier's flat-line case now spans 0 to 2.66e-10 M_Pl⁴ over the sweep. The
  old preview's relative span was 8.9e-5.
- **[1] One M_Pl.** `src/lib/configDefaults.json` gains `units.M_PL_GEV`.
  `configDefaults.ts` exports it as `M_PL_GEV`, and the preview reads only
  that. The engine's own constant (`m1_background.background.M_PL_GEV`) is
  frozen physics and stays where it is. `backend/tests/test_potential_vectors.py::test_the_configurator_converts_with_the_engine_s_m_pl`
  asserts that the JSON equals it exactly.
- **[1] Tested against M2.** `scripts/gen_potential_vectors.py` writes
  `src/lib/__tests__/fixtures/potential-preview.m2.json`. It holds V(ψ) from
  `compile_potential(Potential(kind, params))` on the preview's 80-point grid
  for 7 parameter sets: the three Configurator defaults, every other built-in
  set in `benchmarks.json` and `runs/*.json`, and one hilltop with p = 2 and
  μ ≈ 2 M_Pl.
  - `backend/tests/test_potential_vectors.py` recomputes the vectors and
    fails when the file no longer matches M2.
  - `src/lib/__tests__/potentialEvaluator.test.ts` checks the preview against
    them pointwise, to |ΔV| ≤ 1e-9|V| + 1e-15·max|V|. The tolerance allows
    for the digits 1 − cos loses near its zero; any error of sign or units
    is O(1).
- **[1] Display aid, routed to P4-04 (R6).** The client-side V(ψ) preview is a
  Configurator display aid, not a result. It is not on any R19 page (the
  form column is collapsed on `/`). R6's "every number shown as physical is
  computed by the Python engine" is met when previews come from the API. P4-04
  owns that: its Done-when is "an accuracy test proves no physical value is
  computed in the browser". Until then the preview is pinned to M2's values
  by the test above.
- **[2] Shared vectors.** The same generator writes
  `src/lib/__tests__/fixtures/potential-snippets.backend.json`: 47 snippets,
  12 accepted and 35 refused, each with the backend parser's verdict and
  reason (`m2_scalar.potentials._custom_expr`, the parser behind every custom
  potential).
  - The backend test fails when a verdict or reason changes.
  - `potentialValidator.test.ts` requires that the linter raises no error on
    every accepted snippet and at least one error on every refused one.
- **[2] Linter rules added or changed:**
  - a `def V` may have a docstring before its return;
  - the def error now names the accepted shape: "whose body is one `return
    <expr>` (a docstring may precede it)", no longer "one-line";
  - new errors:
    - `lambda`, `if`/`else`, `and`/`or`/`not`, `in`/`is`;
    - comparisons;
    - `% // @ << >> & | ~`;
    - brackets and braces;
    - string literals;
    - uncalled attributes;
    - an allowed function used without a call;
    - a new line outside brackets with no trailing backslash (a second
      statement);
    - unbalanced brackets.
  - The linter stays display-only.
- **[3] Rule.** Without a refusal, the η_B value and uncertainty must be
  finite, as before FE3. With a refusal that is non-empty after trimming
  (`readEtaB`'s test for a refusal), either may be null or absent.
  `src/lib/__tests__/fixtureSchemas.test.ts` covers this.
- **[5] Security floor.** `backend/pyproject.toml` declares
  `cryptography>=50.0.0` next to `pyjwt[crypto]`, with the same comment the
  qfull-* extras carry. Root `[tool.uv] constraint-dependencies` never reach a
  published wheel. `uv lock` changed only ucgle-f1's dependency list (2
  lines); the locked cryptography version is unchanged. The test passes, as
  do 30/30 in that file. This is outside the four routed items, but it made
  the `packages` job red on the W1 head, and the fix is the one the test
  names.
- **R19.** No R19 PNG or hash was touched. In a Chromium before/after render
  of the three R19 pages, every page is byte-identical between `6e0f15d` and
  this branch (evidence).

## Decision-by-build (proposed)

1. **M_Pl reaches the browser through `configDefaults.json`, pinned to the
   engine by a backend test.** *Why:* the engine's `M_PL_GEV` lives in frozen
   physics code (R5) that the browser cannot import. The JSON is the one
   source the frontend reads (R20), and the test makes a difference
   impossible to merge. *Pinned by:*
   `backend/tests/test_potential_vectors.py::test_the_configurator_converts_with_the_engine_s_m_pl`.
2. **The preview follows `Potential.engine()` for natural configs in M2's own
   names.** When the form holds `{f_a, Lambda}` (the Kawai–Kim fixture's
   config), those values are used as they are. Otherwise `{f, Lambda4}` is
   converted, with the Configurator default for a missing key. *Why:* the
   engine accepts both forms; a preview that merged the Configurator default
   `f` into an M2-form config would draw a potential the run does not use.
   *Pinned by:* `potentialEvaluator.test.ts`, case `natural
   {"f_a":8.7,"Lambda":0.0071154324599829784}`.
3. **The hilltop preview gets the same fix** (μ = mu / M_PL_GEV, not
   mu / 1e17). *Why:* it is the same defect; the finding named natural.
   *Pinned by:* `potentialEvaluator.test.ts`, the three hilltop cases.
4. **The preview's ψ sweep stays [-2, 4] M_Pl.** *Why:* the finding is about
   units and sign. A wider or per-kind range is a display choice for the API
   preview (P4-04). With f_a = 8.7 the sweep shows the bottom of the well (0
   to 0.10 Λ⁴), not the slow-roll region near φ* ≈ 15. *Pinned by:*
   `potentialEvaluator.test.ts`, "samples the grid the vectors were computed
   on".
5. **Linter agreement is "no error ⇔ backend accepts", on shape cases only.**
   Warnings (legacy `def V`, an expression without phi) are allowed on
   accepted snippets. The backend's size, magnitude and argument-count bounds
   stay backend-only, because the linter cannot evaluate. One known edge is
   not a vector: `def V(psi): "doc"; return psi` (one line, `;`) is accepted
   by the backend, and the linter flags its `;`. *Pinned by:*
   `potentialValidator.test.ts`, "custom potential linter against the backend
   parser".
6. **A refused η_B in a fixture may still carry a finite value.** The rule
   asked for is one-directional: no number requires a reason. A finite value
   with a non-empty refusal is accepted, and `readEtaB` shows it as refused.
   *Why:* nothing in the plan or the wire contract forbids it, and adding the
   converse would be a rule nobody asked for. *Pinned by:*
   `fixtureSchemas.test.ts`.
7. **The release build check is a packages-suite test, not a CI job.** *Why:*
   the task prefers a test the existing `packages` job runs. Running the
   workflow's own step text keeps one copy of the loop. *Pinned by:*
   `packages/qcompass/tests/test_release_builds.py`.
8. **The generated vector files are in `.prettierignore`,** like the other
   generated files. *Why:* the generator's bytes are its output, and the
   backend test checks their content. *Pinned by:* `bun run prettier`
   (green).

## Corrected tests (old → new)

None. No existing assertion was changed. New tests were added to
`potentialValidator.test.ts`, and the other new tests are in new files.

## Removals

- `[tool.hatch.build.targets.wheel.force-include]` in the seven qfull-*
  `pyproject.toml` files. Replaced by `packages = ["src/<pkg>"]`, which was
  already there and ships the same instance files. `test_release_builds.py`
  checks that every tracked file under the package is in the wheel, once. No
  capability is lost: before this, no wheel could be built at all.

## Remaining

- **Commit message count.** The commit message of `68bdede` says "45 shape
  cases"; the file has 47 (12 accept, 35 refuse). The commit is pushed and
  R12 forbids rewriting it, so the correct count is recorded here.
- **P4-04: previews from the API (R6).** Move the V(ψ) preview to an API
  endpoint, with a range that shows the slow-roll region. That ends the
  client-side evaluation. Until then it is pinned to M2's values.
- **OPS2 evidence.** `docs/build/evidence/W1-ops2.md` gained a one-paragraph
  round-4 correction: its by-hand build check covered `qcompass-core` only.
- **Chromium baselines and rebaseline (a).**
  `e2e/cosmology-byte-identity.spec.ts` still fails in this sandbox's
  Chromium against the committed PNGs:
  - `/`: 17,384 px (0.01);
  - the two visualizer pages: 0.02 and similar.

  This is the pending rebaseline (a) (Decision 13/15/16 badges; ledger task
  "R19 rebaseline (a)"). It is not this lane's doing: the before/after renders
  of `6e0f15d` and this branch are byte-identical on all three pages.
