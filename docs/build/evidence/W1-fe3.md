# Evidence: W1 round 3B, lane FE3

Branch `build/w1-fe3`, based on `15e4e3c`. Lane notes: `docs/build/lanes/W1-fe3.md`.

## Method

- **BEFORE tree.** A scratch `git worktree` of `15e4e3c` (`scratchpad/round3b/fe3-before`; `node_modules` symlinked from this branch, `tsconfig` paths resolving the base tree's own SDK source), removed afterwards.
  - Every new or changed vitest was copied in as `_r3b_<name>`, run with the base tree's own `src/`, then deleted.
  - The backend tests ran with this branch's venv and `PYTHONPATH=<before>/backend/src`, as `_r3b_` copies, then deleted.
- **SF5 BEFORE tree.** The SF5 residual was fixed by round 2 (`19943a9`), so its tests were also run on a scratch worktree of `19943a9^` (`f9a482d`), then removed.
- **"Fails for the bug's reason"** means the failing assertion is the defect itself, not an import or API-shape error. Where a test calls a function this branch adds (`listRunFixtureSummaries`, `readEtaB`), it is reported as such and does not count as the regression test.
- **Test sources.** Vitest files are under `src/lib/__tests__/` unless noted; the backend test is `backend/tests/unit/test_run_result_wire_flags.py`.

## Per item

| Item | Regression tests | On 15e4e3c | Reason (the failing assertion) | After |
|---|---|---|---|---|
| D15 default | `configDefaults.test.ts` (2 corrected); `test_frontend_potential_configs.py::test_configurator_defaults_come_from_the_json`; e2e-live cosmology test | fail | `expected 70000000000000000 to be 21186240000000000000`; backend `{'f': 7e+16, …} == {'f': 2.11862…}`; the old default fails in the worker: `ValueError trajectory covers τ ≥ -0.0013 only; M3 needs τ ≥ -5.0` (scratch `fe3/d15_default.py` through `RunPipeline`, which is what the worker runs; the new default COMPLETES with η_B refused) | pass; e2e-live: the DEFAULT config completes |
| D16 flags + badge | `syntheticFixtures.test.ts` (Decision 16 block, 5 tests); `cosmologyFixtureBadges.test.ts` "the /visualizer loader badges…"; `synthetic-fixture-badge.spec.ts` (Decision 16 block, 4 tests) | fail | `failing-run.json carries eta_B, F_GB, audit, validation, spectra: expected undefined to be true` (×3); loader `expected ['kawai-kim-natural'] to deeply equal ['gb-off-control', …]` | pass (vitest; Playwright chromium 19/19) |
| D17 snippet + linter | `potentialValidator.test.ts` (6); `test_configurator_custom_snippet_is_accepted_and_computes_main_s_potential`; `test_main_s_two_statement_custom_default_is_refused_naming_the_expression_form` | fail (6/6 vitest; accepted-test fails) | `expected '# Custom inflaton potential V(psi).\n…' not to match /\bdef\b|\breturn\b/`; legacy `def V(x): return …` produced an error (`expected false to be true` for warning-only); backend `ValueError: customPython must be one expression in phi (invalid syntax, line 4)` for the default | pass; the two-statement refusal passes on both trees, as it should (coverage kept) |
| η_B refusal (backend) | `test_run_result_wire_flags.py::test_refused_eta_b_carries_its_reason_on_the_wire` | fail | `assert None == 'ΔN_L depends on the scale-factor normalisation (residual 9); …'`: the reason is not on the wire | pass |
| η_B refusal (UI) | `etaBDisplay.test.tsx` "the Configurator's live run status…", "the run list…"; e2e-live cosmology test | fail | `expected 'qc_refusedcompletedη_B = NaN' to contain 'η_B not published — ΔN_L …'`; `/qa` list: `TypeError: Cannot read properties of null (reading 'toExponential')` | pass; e2e-live shows `η_B not published — <reason>` for the live run |
| M6 placeholder | `test_run_result_wire_flags.py::test_sgwb_spectrum_carries_the_m6_placeholder_flag`; `etaBDisplay.test.tsx` "the run plot says…", "is labelled 'placeholder frequencies'…" | fail | `assert None is True` (no flag on the wire); `expected '' to contain 'placeholder frequencies'`; axis `expected 'a10^-1910^-18f [Hz]…' to contain 'placeholder frequencies'` | pass; the unflagged (fixture) cases pass on both trees |
| c5 MED /visualizer | `visualizerApiMode.test.tsx` (first 3); e2e-live "cosmology visualizers…" | fail | `listVisualizationSummaries()` `expected [ {…}×7 ] to deeply equal []`; `Unable to find … [data-testid="visualizer-api-index"]`; `Unable to find … "No cosmology runs yet"` | pass |
| c5 MED cosmology card | `visualizerApiMode.test.tsx` "maps the API's VisualizationResponse…" | fail | `Unable to find … "visualizer-coming-online"`, plus unhandled `TypeError: Cannot read properties of undefined (reading '0')` (`tl.tau_range[0]`, the crash) | pass; e2e-live renders the card with the synthetic-bake label |
| c5 LOW Live toggle | `visualizerApiMode.test.tsx` "streamVisualization is NOT_IMPLEMENTED…", "the six-panel surface shows no stream toggle" | fail | the stream read the bundled JSONL (`UPSTREAM_FAILURE` wrapping the fixture read, not `NOT_IMPLEMENTED`); `expected <button …> to be null` (the "Start live stream" toggle rendered) | pass |
| c5 LOW Storage/DB for bundled ids | `visualizerApiMode.test.tsx` (3 "no Postgres or Storage reads…") | fail | `expected ['kawai-kim-natural'] to deeply equal []` (Storage read); `expected ['run_results'] to deeply equal []` (Postgres read); `listRuns` `['kawai-kim-natural','qc_real_1']` | pass |
| c5 LOW domain routes | `visualizer/__tests__/domainFrames.test.ts` (corrected); scratch backend repro | fail | `expected '/api/runs/chemistry/r/visualization' to be '/api/qcompass/domains/chemistry.molec…'`. Backend repro (`fe3/_fe3_test_viz_paths.py`): old path **404** for all 8 domains, new path **200** with `synthetic: true` for all 8 | pass |
| c5 LOW home badge rule | Decision recorded; `synthetic-fixture-badge.spec.ts` "home F1 summary badges a flagged run's couplings and drops it once edited"; `visualizerApiMode` (API: `getRunFixtureSummary` → null, no badge source) | n/a (rule) | The base tree badged only `kawai-kim-natural`'s couplings | pass |
| PHYS LOW fail-open | `cosmologyFixtureBadges.test.ts` "fails closed…" | fail | `expected null to match object { synthetic: true, couplings: null }` | pass |
| CRITIC B3 | `e2e/live/workbench-live.spec.ts` "cosmology visualizers list real runs with zero fixture reads" | n/a (new coverage; on 15e4e3c `/visualizer` lists the 7 bundled cards, which the test forbids) | — | pass (local live stack, below) |
| WORKER NIT ids | `streamReconnect.test.ts` "an event that committed late…", "the SDK's SSE parser keeps each event's own id" | fail | `expected [0.1, 0.3, 0.3] to deeply equal [0.1, 0.3, 0.2]` (0.2 lost, 0.3 repeated); parser dropped `id:` | pass |
| SF5 residual | `streamReconnect.test.ts` "awaitRun rejects with STREAM_ABORTED", "streamRun rejects … never marks the run completed" | pass (fixed by round 2) | On `19943a9^`: `expected ServiceError: run qc_cut has no result ye… to match { code: 'STREAM_ABORTED' }`; `promise resolved "undefined" instead of rejecting` | pass |

`cosmologyFixtureBadges.test.ts` "every bundled cosmology run fixture is listed…" fails on 15e4e3c with `listRunFixtureSummaries is not a function`. That is a new-function test, not counted as a regression test. `etaB.test.ts` (unit tests of the new `readEtaB`) was not run on 15e4e3c, because the module does not exist there.

## Live stack (e2e-live, as CI's job runs it)

`LIVE_API_PORT=8891 LIVE_WEB_PORT=5412 LIVE_WEB_ORIGIN=http://127.0.0.1:5412 PW_CHROMIUM_PATH=/opt/pw-browsers/chromium bunx playwright test -c playwright.live.config.ts`. `scripts/live_stack.py` started its own Postgres 16 cluster through the backend harness, with uvicorn API and `qcompass_worker`; `scripts/e2e_live_serve.sh` built with `VITE_API_URL` and served on workerd. The ports differ from CI's only to avoid other agents on this machine.

```
✓ 1 the API and worker are up on Postgres (65ms)
✓ 2 cosmology: Configurator run completes with zero fixture reads (5.7s)
✓ 3 cosmology visualizers list real runs with zero fixture reads (2.9s)
✓ 4 chemistry: H2 manifest run completes with zero fixture reads (3.6s)
4 passed (1.5m)
```

- The cosmology test runs the DEFAULT config at `fast`. The stored run's potential params are `{f: 2.118624e19, Lambda4: 2.563334027300118e-9}`, status `completed`. `run_result.eta_B.refusal` is set and the value is the stored `"NaN"`. The page shows `η_B not published — <that reason>`. There were zero `/fixtures/` requests.
- A first run of the same suite had one failure: the new potential assertion used `toEqual` on the whole object, and the stored config also carries `customPython: null`. The run itself had completed. The assertion now checks `kind` and `params`; the suite was re-run in full (above).

## R19 (Chromium, measured)

Method:
- Both trees' default (no-flag) production builds served on workerd: 15e4e3c on :5420, this branch on :5421.
- Screenshots taken with the byte-identity spec's procedure (1440×900, `reducedMotion`, full page, footer masked, motion frozen; scratch `fe3/r19/shoot.mjs`), then a pixel diff (`fe3/r19/compare.py`).

| Page | Size | Differing pixels | Region |
|---|---|---|---|
| `/` | 1440×2478 | 0 | — |
| `/visualizer` | 1440×900 | 11 554 (0.89 %) | y 233–254, x 586–1178: the two new D16 badges on the `starobinsky-standard` and `gb-off-control` cards (first row; it already held `kawai-kim-natural`'s badge, so nothing moves) |
| `/visualizer/kawai-kim-natural` | 1440×900 | 0 | — |

- **Decision 15's values are not visible on `/` in this render.** The form column renders collapsed at 1440×900 in both trees, as in the committed Chromium and Firefox baselines, and the cost badge and validity light are unchanged.
- **Decision 17's snippet is not visible on any R19 page.** Neither render's page text contains the old or the new snippet.
- **The D13a badge** (home F1 summary, kawai-kim card and header) is already on 15e4e3c, unchanged here.
- `scripts/check_r19.sh` passes: the committed baselines are untouched; this lane does not touch `e2e/__screenshots__/**` or `R19.sha256`.

## Suites (this branch, code at `102671f`; later commits are docs only)

Tool versions: bun 1.4.4 (`bun.lock`), uv 0.11.32 with `uv.lock` (557 packages), Python 3.12.13, Postgres 16 (harness), Playwright Chromium 1243 at `PW_CHROMIUM_PATH=/opt/pw-browsers/chromium`.

| Check | Command | Result |
|---|---|---|
| Backend fast | `cd backend && uv run --frozen pytest -q -m "not slow"` | 705 passed, 3 deselected, 1 xfailed (the parked V2 η_B xfail), exit 0 |
| Backend slow | `cd backend && uv run --frozen pytest -q -m slow` | 3 passed, 706 deselected, exit 0 |
| Frozen audit, fast (drift-alarm step) | `cd backend && PYTHONPATH=src uv run --frozen pytest audit -q -m "not slow"` | 92 passed, 1 deselected, exit 0 |
| Frozen audit, slow | `cd backend && uv run --frozen pytest audit -q -m slow` | 1 passed (`test_gb_to_zero_decoupling`), exit 0 |
| Drift-alarm dirhash | `dirhash -i '*.pyc' '__pycache__' '.pytest_cache' --algorithm sha256 backend/audit/physics` | `42805c73538df5eb0f9eb109ead9a541253d5371d71eac5ea04be0ffaf8e92dd` = `golden.lock`: freeze intact |
| Packages | `uv run --frozen pytest packages -q --import-mode=importlib` | 350 passed, 7 skipped, exit 0 |
| Lint | `bun run lint` | 0 errors, 15 warnings (15 on 15e4e3c: none new) |
| Format | `bunx prettier --check .` | clean |
| Types | `bunx tsc --noEmit` | exit 0 |
| Vitest | `bun run test` | 27 files, 156 tests passed |
| Build | `bun run build` | exit 0 |
| R19 hashes | `scripts/check_r19.sh` | 9 PNGs match `R19.sha256` (baselines untouched) |
| SDK | `scripts/gen_sdk_types.sh --check` | "SDK types match the API's OpenAPI document." |
| Lock | `uv lock --check` | ok |
| Playwright, fixture builds (chromium) | `E2E_PORT_DEFAULT=5410 E2E_PORT_DOMAINS=5411 bunx playwright test --project=chromium e2e/{smoke,synthetic-fixture-badge,visualizer-domain,chemistry-h2-flow,gravity-provenance-guard,domain-shell-coming-online}.spec.ts` | 38 passed (smoke 4, synthetic-fixture-badge 15 incl. the 4 new Decision 16 tests, visualizer-domain 9, chemistry-h2-flow 1, gravity-provenance-guard 3, domain-shell-coming-online 6) |
| Playwright, live API (chromium) | `bunx playwright test -c playwright.live.config.ts` (ports above) | 4 passed |

Not run here: `e2e/cosmology-byte-identity.spec.ts` against the committed baselines. It already differs on 15e4e3c because of the D13a badge, and only rebaseline (a) changes that; the measured R19 delta of this lane is in the table above. Firefox and WebKit were not run locally.
