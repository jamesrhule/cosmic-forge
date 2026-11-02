# Build ledger

## Decisions

- **[PLAN-AUTHOR CORRECTION 7, James 2026-10-31] R19: prove identity, then lock the baseline.**
  - (a) Control run: branch `build/r19-control` from main, cherry-picking only the Workers SSR-fix commits (hand-applied minimal equivalent where they conflict, with the hunks listed here), pushed with `[e2e-baselines]` so CI's three browsers render main's own cosmology PNGs. Compare them with Playwright's comparator (`maxDiffPixelRatio` 0.001) against `build/w0-consolidate`'s PNGs. Ratios go per route and per browser into `docs/build/evidence/P0-06-r19-control.md`; any route over 0.001 lists each visible difference and why it is not a cosmology capability or physics change, or gets fixed. Gate 0 cannot close without that file. `build/r19-control` is deleted afterwards.
  - (b) Lock: `e2e-baselines.yml` becomes `workflow_dispatch` only. `e2e/__screenshots__/R19.sha256` holds the SHA-256 of every cosmology-byte-identity PNG, and the playwright job fails on any mismatch. `R19.sha256` is James-only; any change is `BLOCKED-ON-JAMES:r19-rebaseline`.
  - (c) The WebGLGate fallback (`e99783f`) stands, plus one unit test that the three gated panels still mount an R3F Canvas when `detectWebGL()` is true.
- **[PLAN-AUTHOR CORRECTION 8] R7 synthetic labels in W0.** Every file under `public/fixtures/{amo,chemistry,condmat,gravity,hep,nuclear,statmech}/runs/` gets top-level `"synthetic": true`. Domain run-list rows and the run detail header show a "Synthetic fixture — not a computed result" badge when the flag is set. One vitest fails if any file in those seven directories lacks the flag; one e2e sees the badge on one run page per domain. Cosmology routes and `public/fixtures/{runs,visualizations,artifacts}/` are untouched (R19). The full fixture rework stays in P4-03/P4-04.
- **[PLAN-AUTHOR CORRECTION 9] Verdict data behind auth in W1.** P4-01 adds `GET /api/verdict/{id}` on the compute API, authorised by the same Supabase admin role as the page. The page fetches from it, and `public/fixtures/verdict/*` is removed from the build output in the same PR. P4-01 DoD gains: "an unauthenticated GET of the old static path returns 404". (This supersedes the P0-06 open item (b) "W3 security review".)
- **[PLAN-AUTHOR CORRECTION 10] Drift alarm.** I'm authorised to apply exactly the two-line patch recorded under Conflicts to `.github/workflows/ucglef1-drift-alarm.yml`; nothing else in that file changes, and the hash/compare logic stays byte-for-byte. Proof is a deliberate-drift run: a scratch branch with one byte changed under `backend/src/ucgle_f1/` must fail. Both run URLs go into `evidence/P0-07.md`, then the scratch branch is deleted. This clears `BLOCKED-ON-JAMES:drift-alarm-workflow`.
- **[JAMES DECISION 11, 2026-10-31] P1-03 default coupling.**
  - **Field and units.** φ is the inflaton (Kawai & Kim 2017, arXiv 1702.07689, Eq. 2: "an axion field φ (identified as the inflaton)"). Internal units are reduced-Planck (M_Pl = 2.44e18 GeV = 1), the convention M2's Starobinsky potential already assumes. GeV appears only at the API/UI boundary, converted with that M_Pl.
  - **Published benchmark (follows the paper).** V = Λ⁴(1 ± cos φ/f_a), with f_a = 8.7 M_Pl and Λ fixed by A_s = 2.207e-9 at N_e = 60 (m = Λ²/f_a ≈ 5e-6 M_Pl).
  - **Parameterisation.** UCGLE-F1's own coupling parameters stay (xi, theta_grav, f_a, M_star, M1, S_E2). `couplings.py`'s docstring records the mapping to the paper's normalisation, so the V2 comparison is like for like: −(1/16)ξ_KK R²_GB + (1/16)ϑ RR̃, with ξ_KK = −δ ln[2e^φ η⁴(ie^φ)], δ = −1, and ϑ = γφ, γ = 1.
  - **Default.** `coupling_model="physical"` becomes the default.
  - **Fixture.**
    - `public/fixtures/runs/kawai-kim-natural.json` is re-parameterised to M2's keys and the paper's values.
    - Its result fields (eta_B, F_GB, spectra, validation rows) are not re-invented. They stay as they are until P1-04 can compute them, under decision 13.
    - The three adapter tests that pinned the old fixture are updated to the new parameterisation, not deleted (R4).
  - **Gate test.** The frozen `test_gb_to_zero_decoupling` must be green on the default path. The `--deselect` and the known-gap job are removed in the same PR.
- **[JAMES DECISION 12, 2026-10-31] W0 merge.** As soon as the dependency-review check is green on PR #3, merge it with a merge commit (not squash), so the ledgered history survives. Then rebase PR #5 onto main and move its base. PR #5 merges only when Gate 1 passes.
- **[JAMES DECISION 13, 2026-10-31] R7 on the cosmology fixture, and two authorised R19 rebaselines.**
  - **Synthetic label.** `kawai-kim-natural.json` carries results the pipeline never computed: η_B 6.1e-10 ± 5.4e-11 and five "match" validation rows. It is treated like the domain fixtures: `"synthetic": true`, plus the badge on the cosmology run views and on the home-page summary that shows its numbers.
  - **Rebaselines.** This changes the R19 pages, so exactly two rebaselines are authorised:
    - (a) the badge, now;
    - (b) replacing the fixture's result fields with real pipeline output, once P1-04 makes η_B computable.
  - **Procedure for each.**
    - Dispatch `e2e-baselines.yml` on the branch.
    - Update `R19.sha256` from the bot's PNGs.
    - Ledger the old and new hashes, with one line per visible difference from the diff images.
  - No other change to those PNGs is authorised.
- **[JAMES DECISION 14, 2026-10-31] Gate 1 security findings.**
  - **Method.** The approach stands:
    - one regression test per finding, which fails on 3d2355a and passes after the fix;
    - DB policy changes as new migrations, whose down migrations restore main's version;
    - no existing migration edited.
  - **Gate 1 conditions.** Both HIGH findings must be closed before Gate 1. The medium and low findings are Gate 1 conditions too, unless the fix needs a secret James hasn't provided. In that case the finding is recorded as BLOCKED-ON-JAMES with the exact secret name.
  - **Resume point.** When the weekly limit stops the build, PROGRESS.md is the resume point. On resume, re-read Decisions 11–14 first.
- **[JAMES DECISION 15, 2026-11-02] `ui-v2-defaults-vs-paper-benchmark` → option (a).** Decisions 11–14 stand.
  - The Configurator's V2 natural default becomes the paper benchmark in Configurator units: f = 2.118624e19 GeV, Λ⁴ = 2.563334027300118e-9. The default config then inflates, and e2e-live runs it.
  - This joins rebaseline (a): one rebaseline captures the badge, the new default values and decision 16 together. The total stays at two, (a) and (b).
- **[JAMES DECISION 16, 2026-11-02] `cosmology-fixture-synthetic-labels` → yes.**
  - `starobinsky-standard`, `gb-off-control` and `failing-run` carry hand-written results. They get `"synthetic": true` and the same badge as `kawai-kim-natural`, under the same rebaseline (a).
  - Their result fields are not re-invented.
- **[JAMES DECISION 17, 2026-11-02] Custom-potential snippet shape.**
  - The canonical shape is the backend's: a single sympy expression in φ.
  - The API also accepts a `def V(<name>): return <expr>` snippet. It extracts the single return expression and renames the parameter to φ, so configs saved from main's Configurator keep working (R2).
  - Any other function body is a 422 that names the canonical form. There is a test for each case.
  - The Configurator's default snippet and its linter switch to the expression form. If the default snippet is visible on an R19 page, that change joins rebaseline (a) too.
- **Order of work (James, 2026-11-02).** Round 2 → merge → round 3 → rebaseline (a) → Gate 1 → W0 merge, per PROGRESS.md. On resume, re-read Decisions 11–17 first.

- **[P0-05] Production Worker SSR.** There were four defects, all fixed:
  1. The chat store generated a random id at module scope, which Workers forbid ("Disallowed operation called within global scope").
  2. `loadFixture` used `require()` in ESM SSR, so every server fixture read hit `http://localhost:8080`. Server reads now go through the static-assets binding `env.ASSETS`, declared in `wrangler.jsonc`, with a request-origin fallback under `vite dev`.
  3. The domain routes' loaders returned plugin objects, which can't be serialised.
  4. `package.json` `"sideEffects": false` let Rollup drop `register-all` and every domain registration (plus `@/lib/i18n` init) from production bundles, so every `/domains/*` route 404'd in production even with flags on. It's now an explicit list: `*.css`, `./src/lib/domains/*.ts`, `./src/lib/i18n.ts`.
  `scripts/ssr_smoke.sh` checks a wrangler-served production build in CI.

- **[PLAN-AUTHOR CORRECTION 1]** Gate 0 passes with exactly one pre-existing failure: `backend/audit/physics/test_parity_hypothesis.py::test_gb_to_zero_decoupling`, recorded `OPEN-WITH-GAP` and owned by P1-03. It must be green by Gate 1. If P1-03's couplings don't fix it, P1-04 and P1-07 own it as a solver-precision defect. No other failure is exempt.
- **[PLAN-AUTHOR CORRECTION 2]** Freeze scope: only `backend/audit/physics/` and `backend/audit/golden.lock` are frozen (R5). `backend/audit/agent/` (A1–A9) is editable under R4 like any other test. A7 was re-run on the merged tree: 11/11 pass (evidence/P0-04.md), so no W0 fix is needed.
- **[PLAN-AUTHOR CORRECTION 3]** Optional backends must stay testable (R2). P1-06 pins GWBird and PyTransport 3.0 as git sources at fixed commits in `[tool.uv.sources]` if their licences pass the gate. This supersedes the P0-04 manual-install replacement, which stands only until P1-06. P2-01 adds a separate CI job and lock fork for `qcompass-router[braket]` without the backend, and builds the qpu worker image without Hydra/omegaconf so Braket runs in production.
- **[PLAN-AUTHOR CORRECTION 4]** Production SSR returns 500 on Cloudflare Workers ("Disallowed operation called within global scope"). P0-05 owns the fix in W0: a production build served by wrangler must render `/` without a 500, verified in CI.
- **[PLAN-AUTHOR CORRECTION 5]** Durability (R15): every lane commits and pushes its own `build/w0-*` branch at least every 30 minutes. The frontend lane was told to commit and push now; the router and viz lane branches are pushed.
- **[PLAN-AUTHOR CORRECTION 6]** Router drift gate, P2-03: drifting candidates are excluded and the router picks the next-best backend. `CalibrationDrift` is raised only when no non-drifting candidate meets the request. P2-03 adds the test. This supersedes router-lane D4 (which blocks only when the chosen backend drifts).

- **[P0-04]** `uv.lock` resolution: `amazon-braket-sdk>=1.115` pins `antlr4-python3-runtime==4.13.2`, while `omegaconf` (used by `ucgle_f1.m7_infer.hydra_cfg`) pins `4.9.*`. Declared `[tool.uv] conflicts` between package `ucgle-f1` and `qcompass-router[braket]`, so the lock has two forks. These can't share an environment, and CI installs without `braket`. This uses uv's experimental package-conflict feature.
- **[P0-04]** Root `[tool.uv.sources]` declares every member `{ workspace = true }`; `[tool.uv] dev-dependencies` moved to `[dependency-groups].dev`.

- **[P0-01] Interim second CI file.** Main's `ci.yml` kept; the agent branch's `ci.yml` kept verbatim as `.github/workflows/ci-python.yml` until P0-05 merges them into one CI.
- **[P0-01] Chemistry Result.** The agent branch's run-detail content now lives in `src/components/results/chemistry/ChemistryResult.tsx`, dispatched by `DomainResult` for `chemistry.molecular`. It maps main's payload (`classical_reference_hartree`, `energy_hartree`) — or the qfull fields (`classical_energy`, `quantum_energy`, `classical_method`) when present — onto the energy-comparison card.
- **[P0-01] Main's 6A router tests preserved** verbatim in `packages/qcompass-router/tests/lineage_6a/` (with main's conftest) for P0-02.
- **[Baseline] Screenshot method.** Production SSR does not serve locally (see BASELINE.md); cosmology screenshots are taken from `vite dev`, Chromium 1440×900, animations off, after the auth button settles, with a main-vs-main determinism control.

**[P0-02 router lane]** (from `docs/build/lanes/P0-02-router.md`)

- D1 Agent API is canonical: `RoutingDecision.transforms_applied: list[TransformRecord]` (no
  `transform_records`), `CalibrationCache.drift_score -> dict[str, float]`, `Router.decide(req, *, circuit,
  transforms, transform_parameters)`.
- D2 6A compatibility in `providers/base.py`: `BackendInfo.kind/fidelity_estimate/queue_time_s_estimate`
  optional, filled by `BackendInfo.with_priors(kind)` from `KIND_FIDELITY_PRIOR`/`KIND_QUEUE_PRIOR_S`
  (6A values); `JobHandle.submitted_at` defaults to aware-UTC now; `list_backend_infos()` defaults to a
  6A-style `list_backends()` override; `estimate_cost_for(backend, shots) -> float | None` hook (None =
  use seed). Aliases `AzureQuantumAdapter`, `IBMRuntimeAdapter`, `IonQNativeAdapter`, `QueRaAdapter`,
  `default_adapters` — the same classes, not copies.
- D3 Router: budget=0 prefers `local_lightning` above 25 qubits (6A); budget=0 + real hardware allowed
  only when a ledger free tier covers an available non-simulator backend, else `BudgetExceeded`
  (`BUDGET_EXCEEDED`, message names `require_real_hardware`); free-tier = ledger coverage when a tier lists
  the backend, else the seed flag; runtime heuristic 1 ms/shot (6B).
- D4 Drift gate applies to the **chosen** backend (agent placement), using `assert_no_drift` (6B relative
  two-qubit drift > 3.0) plus the v1 day-table `check_drift`. 6B raised for any drifting candidate; a
  drifting backend that would not be chosen no longer blocks routing (tested).
- D5 Stale downgrade (6B): with a calibration cache, stale candidates rank after fresh ones only when a
  fresh one exists.
- D6 Auto transforms (6B): explicit `transforms=` win; otherwise depth (`transforms._common.circuit_depth`,
  QASM gate lines) above the smallest non-local `device_typical_depth_max` applies `cutting`+`obp`;
  `Router(auto_transforms=())` disables.
- D7 Live pricing never runs in tests: only with an injected `client_factory` or
  `QCOMPASS_PRICING_LIVE=1` (R8). Without either, `refresh_live` seeds the cache (agent behaviour). Live
  failures write nothing and never raise. Default client = `ssl_pin.client(ca_bundle=...)`, which builds
  `httpx.HTTPTransport(verify=ssl_pin.pinned_context(...))` (CERT_REQUIRED, hostname check; `False` refused).
- D8 `pricing_stub.lookup` order: exact provider+backend → key `<provider>_<backend>` → key `<backend>`
  if same provider → (backend empty only) key `<provider>` or the provider's first entry. 6A's key
  `<backend>` lookup did not check the provider; the provider check is stricter.
- D9 One pricing formula: `pricing_stub.estimate_entry(raw, shots) -> (usd, breakdown)`, used by
  `estimate`, `LivePricing`, `PricingEngine` and the router (three copies removed). It adds 6A's Azure
  shapes (`per_1q_shot_usd`/`per_2q_shot_usd` × shots, `hqc_per_circuit × hqc_overage_usd`) that the agent
  formula ignored.
- D10 Transforms: one runner `transforms/_common.run_addon_transform` (soft import, depth before/after,
  runtime, notes); `TransformRecord` gains `depth_before`, `depth_after`, `runtime_ms`. 6B addon entry
  points kept (`cut_wires`/`cut_circuit_wires`, `trotter_circuit`, `backpropagate`, AQC
  `generate_ansatz_from_circuit`+`MaximizeStateFidelity`+`optimise`); called with the circuit only.
- D11 Coordinator request for P0-04 (done here): every `datetime.utcnow()` in qcompass-router replaced
  with `datetime.now(UTC)` (calibration `_utcnow()`, `budget.py` `period_start` default
  `lambda: datetime.now(UTC)`); calibration timestamps are aware UTC end to end (naive inputs and legacy
  naive rows read as UTC, stored with `+00:00`). `asyncio_default_fixture_loop_scope = "function"` added to
  `[tool.pytest.ini_options]` in `packages/qcompass-router/pyproject.toml`. No warning filters added.

**[P0-02 router lane] seed reconciliation:** `packages/qcompass-router/fixtures/pricing_seed.yaml` (router branch) deleted; its `free_tiers` and `device_typical_depth_max` blocks merged into `src/qcompass_router/fixtures/pricing_seed.yaml`. Prices already present in the package seed win (only difference: `braket_rigetti_ankaa` keeps `per_task_usd: 0.30`; the router-branch seed had none). Free-tier backend lists add the package's names (`ibm_eagle`, `iqm_garnet`, `iqm_deneb`) next to the router-branch ones; every free-flagged seed entry is listed by a tier (tested). The three router-branch CSVs (`ibm_torino`, `ionq_forte`, `iqm_garnet`) moved unchanged to `src/qcompass_router/fixtures/calibration_seed/` (they now ship in the wheel); `load_calibration_seed` reads `.yaml` or `.csv` (`name.csv` selects CSV; bare name prefers YAML — `ionq_forte` has both).

**[P0-02 viz lane]** (from `docs/build/lanes/P0-02-viz.md`)

**L2 — agent `CosmologyFrame` flat/`CosmologyModeBlock` fields → router-branch structured shape.**
Same-named fields had different types across branches (e.g. `modes`, `B_plus`, `lepton_flow`).
The router shape is canonical because it matches `src/types/visualizer.ts`; `CosmologyModeBlock`
is replaced by `_ModeSample` list. Agent-only fields kept: `HepFrame.particle_obs`,
`NuclearFrame.model_domain`, `ChemistryFrame.slater` (Sankey matrix), `GravityFrame`,
`StatmechFrame`, `VisualizationTimeline` (+ new `synthetic`, `formula_variant`).

**L3 — phase vocabulary.** Router vocabulary is canonical (`gb_window`, `sphaleron`, …). The
agent's `leptogenesis` epoch maps to `sphaleron` in `formulas_at_phase` (`_PHASE_ALIASES`).
Gravity (`ground→quench→thermalize→measure`) and statmech (`warmup→equilibrium→measure`) added.

**L4 — POST `/visualization/render` with no body.** Agent: synchronous `bake_synthetic`, 200.
Router: 202 `{"status":"queued"}`. Unified: 202 queued **and** the synthetic bake runs as a
background task when a viz root is configured (both behaviours kept). With a provenance body:
agent behaviour, 200 + bake info.

**L5 — server viz root / GET source.** Agent server baked synthetic JSON into
`~/.qcompass/viz` on every miss and set `VIZ_ARTIFACTS` process-wide in `create_app`. Unified:
root = `create_app(viz_root=)` → `$VIZ_ARTIFACTS` → none; baked snapshot served when present,
otherwise `total` synthetic frames (flagged `synthetic: true`, R7) without writing to disk; no
global env mutation. `bake_synthetic` / CLI `bake` still default to `~/.qcompass/viz`.

**L6 — GET `max_frames` default.** Agent default 256, router default none. Router semantics kept
(frontend contract); the M8 `/api/qcompass/.../visualization` route keeps its own 256 default.
SSE keeps the agent's `adaptive_decimate` cap (≈128 frames) unless `max_frames` is given.

**L7 — Zarr writer.** Agent `_write_zarr` used the zarr‑2 API (`zarr.open`/`create_dataset`) and
silently produced nothing on zarr 3. Replaced by router `bake_timeline` (zarr v3), now also called
by `bake_synthetic` (`zarr_path` populated; still soft-fails to `None`).

**L8 — seeds.** Router used `hash(run_id)` (salted per process → nondeterministic across
processes). Replaced by `fixtures.stable_seed` (crc32).

**L9 — CLI.** Router Typer CLI (`serve`, `bake` zarr-only, `demo`) merged into the agent argparse
CLI: `bake` (JSON + Zarr, `--formula-variant`), `demo`, `serve`, `check` (now 8 domains).

**[P0-02 fe lane]** (from `docs/build/lanes/P0-02-fe.md`; per-panel decisions are in its table)

- **LF4 — no invented values.** `getManifest` offline stand-in `frame_count` 60 → 0. ShellOccupation's hard-coded
  `energy < -4` colour threshold removed. Flat ⟨σᶻσᶻ⟩ matrices are not relabelled as g²; bare bond strengths are
  not paired with sites.
- **LF5 — stream protocol** (see above): `"__done__"` sentinel handling removed, replaced by the envelope `end`/`error`.
- Not changed (noted for later tickets): `services/qcompass/visualizer.ts#getVisualization` still synthesises an
  8-frame `progress` timeline when a run fixture has no embedded timeline (main behaviour, used by the cosmology
  card) — an R7 concern for P4-03/P4-04. `lib/domains/types.ts` keeps a separate generic `VisualizationFrame`/
  `VisualizationTimeline` (domain-agnostic `{tau, data}` envelope, a different concept from the panel frames).
- **[P0-02 fe lane → P0-05]** Same plugin-returning loader (not serialisable over SSR) is still in `routes/domains/$domain/{runs,runs.$id,configurator,research}.tsx`; P0-05 fixes it with the SSR work.

- **[P0-03]** One JS lockfile: bun (`bun.lock`, text format via `bunfig.toml` `saveTextLockfile = true`). pnpm's `minimumReleaseAge: 1440` (minutes) supply-chain guard is ported as bun `minimumReleaseAge = 86400` (seconds). `package.json` `workspaces` lists `packages/ts/*` and `apps/*`. Docs, Taskfile and READMEs now say bun.
- **[P0-03]** The lockfile carried 374 tarball URLs on a private Lovable npm mirror (`europe-west[14]-npm.pkg.dev/lovable-core-prod/sandbox-npm-cache/`), which return 403 outside Lovable. The URLs are rewritten to `""` (default registry); integrity hashes are unchanged, so the same bytes resolve.

- **[P0-05] One CI.** `.github/workflows/ci.yml` now holds every PR job: `secrets` (gitleaks 8.28.0, pinned and checksum-verified, full history), `dependency-review` (PRs; high severity and R11 licence deny-list), `licences` (`scripts/licence_gate.py` over the uv and bun install trees), `frontend` (eslint, prettier --check, tsc, SDK tsc, vitest, build, audit gate), `ssr-worker` (production build on workerd, default and all-domains), `e2e` (Playwright on three browsers, P0-06), `lighthouse`, `backend` (fast tests + audits, `uv lock --check`), `backend-slow`, `packages` (import boundaries, tests + per-domain audits, ruff). `codeql.yml` covers Python and JS/TS (security-extended). No path filters: a required check that is skipped never reports. `ucglef1-drift-alarm.yml`, `phase3-verdict.yml` and `release-please.yml` are unchanged.
- **[P0-05] Gate 0 exception in CI.** `backend-slow` deselects exactly `audit/physics/test_parity_hypothesis.py::test_gb_to_zero_decoupling` (plan-author correction 1). The non-required `known-gap` job still runs it every time so the gap stays visible. P1-03 removes the deselect. No other test may be deselected.
- **[P0-05] Required checks: BLOCKED-ON-JAMES:branch-protection.** Making jobs required on `main` is a repository setting, which R13 forbids me to change. James: Settings → Branches → `main` → require status checks: `secrets (gitleaks)`, `dependency review`, `licence gate`, `frontend (lint · format · types · vitest · build · audit)`, `production SSR on workerd`, `playwright (chromium · firefox · webkit)`, `lighthouse budgets`, `backend (ucgle_f1 tests + audits)`, `backend (slow audits)`, `packages (qcompass-* + qfull-*)`, `codeql (python)`, `codeql (javascript-typescript)`, and the drift alarm. Leave out `known gap: …`.
- **[P0-05] Lint.** `eslint --fix` and Prettier fixed 827 issues. Hand fixes: conditional hooks in `src/routes/qa.tsx` (hooks moved above the production 404 early return), and stale `react/no-danger` disable comments naming a rule the config doesn't load. `.prettierignore` now excludes `docs/build/` (PLAN.md R1), `public/fixtures/` (data contracts), the Python trees and generated Supabase types. Ruff on `packages`: 165 safe autofixes plus hand fixes (dead conditional, an unused variable in each of qfull-amo and qfull-gravity, a re-raise-only handler, nested if, `contextlib.suppress`). Intentional broad excepts on plugin/optional-backend soft-fail paths carry a `noqa` with the reason. Package suite after: 329 passed, 7 skipped.

- **[P0-07]** Freeze tag target = `73ae381`. `golden.lock` names the tag, not a SHA; `73ae381` is the commit that wrote `physics_dir_hash`, and its `backend/audit/physics` reproduces the hash exactly. The tag push was refused by the session's git proxy → `BLOCKED-ON-JAMES:tag-push-permission` (command in evidence/P0-07.md).
- **[P0-07]** Missing Supabase variables degrade through `unconfiguredClient` (R9) instead of throwing. The Lovable-generated `client.ts`, `client.server.ts` and `auth-middleware.ts` were edited; a Lovable regeneration would overwrite them, so keep that in mind if the project is re-synced from Lovable.
- **[P0-07]** `BLOCKED-ON-JAMES:supabase-key-rotation` — publishable key in history at `3a08f14`.

- **[P0-05, CodeQL on PR #3]** 12 high `py/path-injection` alerts in `cosmic_forge_viz/{server,baker}.py` and `m8_agent/qcompass_routes.py`. They were real: request `run_id`/`runId` became file names under the artifacts roots unchecked. Fix: one guard module, `ucgle_f1/_paths.py` (`safe_component`: a single component `[A-Za-z0-9][A-Za-z0-9._-]{0,127}` with no `..`; `safe_join`: realpath containment, symlink escapes refused). It's applied at every route (400; WS closes 1008) and inside `bake_synthetic`/`_load_source` as defence in depth. Tests: `backend/tests/test_path_guards.py`.
- **[P0-05] BLOCKED-ON-JAMES:dependency-graph.** `dependency review` fails with "Dependency review is not supported on this repository. Please ensure that Dependency graph is enabled". That's a repository setting (R13). James: Settings → Security → Code security → enable "Dependency graph". The job stays as written, red until then. The licence gate and `audit:gate` cover the same ground meanwhile.

- **[P0-05, CodeQL JS]** `js/remote-property-injection` in `src/lib/visualizer/domainFrames.ts` `particleObs`: `__proto__`/`constructor`/`prototype` keys from run payloads are now skipped (test added). `js/polynomial-redos` in the SDK `QcompassClient` constructor: the trailing-slash regex is replaced by a loop.
- **[P0-05] Lighthouse** started `vite preview`, which can't serve the Cloudflare Worker build (the same 500 as BASELINE). `.lighthouserc.json` now starts `wrangler dev` on the production build (ready pattern "Ready on"). Budgets are unchanged.

- **[Gate 0 review]** An independent R16 review of `fc4cd52` against the three sources found five drops that nothing recorded. Each is now restored, with tests in `packages/qcompass-router/tests/test_gate0_restorations.py` and `backend/tests/viz/test_cli_compat.py`:
  - **A. `ProjectBudget`:** `member_user_ids` is accepted again (alias of `members`, also a read property), `remaining_usd` is back, and `monthly_cap_usd` defaults to 0.0 (`UserBudget` too). `period_start` accepts `None` (6A). `extra="forbid"` is kept.
  - **B. `Router`:** the `pricing` property is back. The 6B default `pricing=PricingEngine(ledger=...)` is restored, so routing reads a fresh live or cached price when one exists. It still never fetches live on its own (D7). The `seed_path=` keyword is accepted again but only for the package seed; another path raises `ValueError` (extends S2: the package seed is the single price source, R20).
  - **C. `from qcompass_router import apply_transforms`** is exported again.
  - **D. `cosmic-forge-viz`:** `serve --reload`, `bake --seed`, and the 6B form `bake DOMAIN RUN_ID --out STORE` (Zarr-only, explicit seed) work again; the flag form is unchanged.
  - **E. Transforms:** module-level `apply(circuit, **kwargs)` is restored in `cutting`, `obp`, `mpf` and `aqc_tensor` with 6B semantics: every kwarg, including the named ones (`max_subcircuit_width`, `threshold`, `order`, `target_fidelity`), is forwarded to the addon call (`aqc_tensor`: to `optimise(objective, **kwargs)`, as on 37086b7) and recorded in `TransformRecord.parameters`, which must stay scalar. The agent-lineage `apply_<name>(circuit, *, <named>)` entry points also forward extra `**addon_kwargs`. **Correction:** an earlier version of this entry said "aqc_tensor never forwarded kwargs on 6B", which was false; the re-review caught it and it is fixed.
- **[Gate 0 review] Accepted as-is:** the router-branch URL `/visualizer/$domain/$id` returns 404 (the fe lane's deliberate LF2 retarget; its short domain names have no 1:1 map to the full ids). `pricing_stub.lookup` provider check (D8) stays stricter, which is documented.

- **[P0-05] SEO files.** Static `public/robots.txt` and `public/sitemap.xml` were invalid: the robots `Sitemap: /sitemap.xml` and every sitemap `<loc>` were relative, and both specs require absolute URLs. Lighthouse flagged `robots-txt`. Replacement: Worker routes `src/routes/robots[.]txt.ts` and `src/routes/sitemap[.]xml.ts` render them per request from the request origin (`src/lib/seo.ts`; same entries and rules).
- **[P0-05] `/login` is crawlable.** robots.txt disallowed `/login` while the Lighthouse budget asserts SEO ≥ 0.9 on `/login` (is-crawlable failed; score 0.54). The page has a title and description and nothing private. The policy changes rather than the budget: `/login` is no longer disallowed, while `/qa`, `/api/`, `/auth/` and `/reset-password` still are. Local Lighthouse (desktop) on the wrangler build: `/` perf 0.83 · a11y 0.92 · bp 1 · seo 1; `/visualizer` 0.89 · 1 · 1 · 1; `/login` 0.95 · 1 · 1 · 1. `/` performance is below the 0.85 **warning** budget (non-failing). Recorded here as an open performance item; not hidden.

**[P0-06 e2e lane]** (from `docs/build/lanes/P0-06-e2e.md`)

- **D1 One config, three browsers, production runtime.** The root `playwright.config.ts` has `chromium`, `firefox` and `webkit`
  projects. Its webServer runs `scripts/e2e_serve.sh`, which builds the PRODUCTION Worker bundle twice and serves each on workerd
  (`wrangler dev`). `vite preview` cannot serve the Worker build, and `vite dev` isn't the production runtime.
- **D2 Flags: two production builds, not one.**
  - `dist-e2e/default` (no `VITE_QCOMPASS_*`, served at `DEFAULT_URL` :4310) is what users get today. It's used for the cosmology
    specs, smoke, the default-build 404s and the flag-off reachability checks.
  - `dist-e2e/domains` (every `VITE_QCOMPASS_*` flag including AUTH, served at `DOMAINS_URL` :4311) is used for the domain specs.
  - A spec picks its server with `test.use({ baseURL })` or an absolute URL (`e2e/urls.ts`).
  - Why not one all-flags build: the cosmology baselines must reflect the default posture (R19), and the "flag off → not
    reachable" checks need a default build.
- **D3 Snapshots.**
  - Baselines live at `e2e/__screenshots__/<project>/<spec>/<name>.png`. Chromium baselines are committed and verified by eye:
    real content, no error pages.
  - The build-stamped footer (commit SHA + build date) is masked. Animations are frozen, the viewport is fixed at 1440×900 and
    reducedMotion is on.
  - These baselines come from the production build, so they differ from the `vite dev` R19 re-anchor images only by dev-only
    chrome (the "dev build" pill and the Control/Research/qa links, which exist only in dev). The rendered cosmology content is
    the same.
  - Firefox/WebKit baselines don't exist yet. The config sets `updateSnapshots: "missing"`, which writes them on the first CI run,
    but that run still reports those three tests as failed ("A snapshot doesn't exist … writing actual"). See "Open items" for
    the one-time step.
- **D4 Chromium binary.** The repo pins `@playwright/test` 1.59.1, but the sandbox's preinstalled Chromium is a different
  revision. Setting `PW_CHROMIUM_PATH` swaps the executable. CI doesn't set it and uses the browsers `playwright install` fetched.
- **D5 "Coming online" vs disabled domain.** In this app a domain whose flag is off is not registered, so `resolveDomain` returns
  a 404 and the domain is never shown. The coming-online state belongs to *enabled* domains with no dedicated renderer (condmat,
  amo, statmech). `domain-shell-coming-online.spec.ts` asserts both: the coming-online shell and card on the domains build, and a
  404 with no card on the default build.
- **D6 Gravity guard fixture.** The negative fixture (`e2e/fixtures/gravity-learned-no-warning.json`, `"synthetic": true`, R7)
  deliberately violates the fixture contract. It is served by request interception and is NOT shipped under `public/fixtures`,
  where `backend/tests/test_lovable_contract.py` would rightly reject it.

**[P0-06 e2e lane] App fixes found by the specs:**

1. **Run detail pages were unreachable.** `routes/domains/$domain/runs.tsx` was the parent of `runs.$id.tsx` and had no
   `<Outlet/>`, so `/domains/<id>/runs/<run>` always rendered the runs list. It's renamed to `runs.index.tsx` (route
   `/domains/$domain/runs/`). The FE lane fixed the same bug for the visualizer. `src/routeTree.gen.ts` was regenerated.
2. **The configurator queued a run but stayed on the form.** It now navigates to `/domains/$domain/runs/$id` after `startRun`,
   which is the PROMPT 4 v2 DoD ("submitting … displays the fixture's provenance panel").
3. **The verdict "admin gate" was client-side only.** Any visitor could pick `tenant-admin` in the TenantPicker (QCompass auth
   strip) and see the report. `/admin/verdict` now also requires the verified Supabase `admin` role (`hasRole("admin")` from
   `@/lib/auth`, backed by RLS-protected `public.user_roles`).
4. **The 404 head wasn't in the SSR HTML.** `NotFoundComponent` set `document.title` and robots imperatively, and the managed
   head overwrote both after hydration. In production `/nope` had title "UCGLE-F1 Workbench" and no noindex, so the existing
   `smoke.spec.ts` failed. The root `head()` now emits the 404 title and `robots: noindex, nofollow` whenever any match is
   `notFound`.

- **[P0-06] Open items carried forward:**
  - (a) R7: `public/fixtures/*/runs/*.json` are synthetic (fake providers) but carry no `"synthetic": true` and no UI label. This is an R7 gap and needs its own change (it touches every run fixture and the result views). It is tracked to P4-03/P4-04, which own fixtures, and listed under Gate 0 notes.
  - (b) `/fixtures/verdict/sample-verdict.yaml.json` is a public static asset. The page gate now requires the Supabase admin role, but the data file itself is unauthenticated. Server-side authorisation belongs with the verdict service work (W3 security review).

- **[P0-06, CI on PR #3] No-WebGL crash.** On Firefox in CI (no WebGL), `/domains/condmat.lattice/visualizer/hubbard-4x4` and `/domains/amo.rydberg/visualizer/rydberg-mis` threw an uncaught "Error creating WebGL context". The 3D panels (`LatticeWithBondColors`, `AtomArray3D`, `OrbitalOccupation3D`) rendered an R3F `<Canvas>` unconditionally. Fix: one shared `src/lib/webgl.ts` (`detectWebGL`, moved from `panel-phase-space.tsx`, plus a `useWebGLAvailable` hook) and `panels/WebGLGate.tsx`, which shows an honest "needs WebGL" panel instead of crashing. The assertion `expect(errors, "no uncaught exceptions").toEqual([])` is unchanged.
- **[P0-06] Screenshot baselines come from CI's browsers.** The Chromium baselines rendered in this sandbox (a different Chromium build) failed on CI, and Firefox/WebKit had none. `.github/workflows/e2e-baselines.yml` regenerates `e2e/__screenshots__` on CI's chromium/firefox/webkit when a commit message on a `build/**` branch contains `[e2e-baselines]`, and commits them back. Every regenerated PNG is then inspected by eye (real content, no error page) before the next CI run enforces it. The workflow never runs on `main`. Tolerance (`maxDiffPixelRatio: 0.001`) is unchanged.

- **[Correction 7b, implemented]** `e2e-baselines.yml` is now `workflow_dispatch` only and refuses `main`. `e2e/__screenshots__/R19.sha256` pins the SHA-256 of the 9 reviewed cosmology PNGs (chromium/firefox/webkit × `/`, `/visualizer`, `/visualizer/kawai-kim-natural`). `scripts/check_r19.sh` (`sha256sum --check --strict`, plus a check that no unpinned cosmology PNG exists) runs in the CI playwright job before and after `playwright test`, so a run with `updateSnapshots: "missing"` can't silently re-baseline. `.github/CODEOWNERS` assigns `R19.sha256` and the cosmology baseline directories to @jamesrhule; making that review required is part of `BLOCKED-ON-JAMES:branch-protection`.
- **[Correction 7c, implemented]** `src/components/visualizer/panels/__tests__/webgl-gate.test.tsx`: with `HTMLCanvasElement.getContext` returning a context, `detectWebGL()` is true and `AtomArray3D`, `LatticeWithBondColors` and `OrbitalOccupation3D` each mount the (stubbed) R3F `<Canvas>`. With no context, each shows the "needs WebGL" fallback and no Canvas. 6 tests.
- **[Correction 8, implemented]** `"synthetic": true` is added to all 22 run fixtures in the seven domain dirs (only that key added; formatting kept). `SyntheticBadge` ("Synthetic fixture — not a computed result") shows on run-list rows and in the new run detail header (`data-testid="run-detail-header"`, label as plain text so it doesn't duplicate the coming-online heading). Tests: `src/lib/__tests__/syntheticFixtures.test.ts` (7, one per dir) and `e2e/synthetic-fixture-badge.spec.ts` (one run page per domain plus a run-list check). The visualizer's existing synthetic-timeline label (fe lane) is unchanged. Backend contract test 54/54; the wire model already allows `synthetic`.

- **[Correction 10 follow-up] Drift-alarm environment.** With the authorised patch, `dirhash` installs. The next unchanged step, `uv run pytest audit`, then failed with "Failed to spawn: pytest": the workflow's `uv sync --package ucgle_f1` installs only `ucgle_f1` and its own default groups, and P0-04 had moved dev tools to the workspace root's group. Fixed in the package, not the workflow: `backend/pyproject.toml` gains `[dependency-groups].dev`, which `uv sync`/`uv run` install by default. It has pytest, pytest-asyncio, hypothesis, httpx2 and dirhash, plus what the A7 audit needs: `qcompass-core`, `qfull-chemistry`, and the `viz` extra's packages, listed individually because a self-reference `ucgle-f1[qcompass,viz]` trips the declared braket conflict. Reproduced locally with the workflow's exact steps in a fresh env: 80 passed, 1 skipped, 1 deselected; dirhash `42805c73…92dd`. The workflow file has no further changes.

- **[Corrections 7a/10, Gate 0] BLOCKED-ON-JAMES:branch-delete-permission.** The session's git proxy refuses remote ref deletion (`git push origin --delete …` → "the remote end hung up", three tries), as it refuses tag pushes, and the GitHub tools here have no branch-delete call. Branches waiting for deletion: `build/r19-control` (correction 7a; evidence written), `build/w0-drift-proof` (correction 10, after its run URL is recorded), and the two `claude/*` branches (Gate 0, after the W0 merge). James: `git push origin --delete build/r19-control build/w0-drift-proof claude/ucgle-f1-agent-simulator-agRxR claude/provider-adapters-routing-33xCz`, the last two only after PR #3 merges.

- **[P0-06, CI on PR #3 @ 04ccba3] wrangler dev crash.** 26 Firefox/WebKit failures were one event: the default-build `wrangler dev` (port 4310) exited mid-suite with an empty `✘ [ERROR]`, and every later default-build test got "connection refused". The R19 lock check passed: 9 PNGs matched before and after. Fix: `scripts/e2e_serve.sh` supervises each server and restarts it on exit, logging each restart to `dist-e2e/RESTARTS`. `scripts/check_e2e_restarts.sh` runs in the CI playwright job (`if: always()`) and **fails the job if any restart happened**, so the suite still reports every spec but a crash is never hidden. Wrangler logs (`~/.config/.wrangler/logs/`) and `RESTARTS` are uploaded with the report for diagnosis. No test or tolerance changed.

- **[W1 start] W1 stacks on W0.** R12 says branch from latest `main`, but W0 (PR #3) can't merge yet: its only red required check is dependency review, which is `BLOCKED-ON-JAMES:dependency-graph`. R14 says blocked work never stops the build, so W1 starts from `build/w0-consolidate` @ `65e08d0`. The integration branch is `build/w1-foundations`; the lanes are `build/w1-physics` (P1-01…P1-04) and `build/w1-platform` (P3-01…P3-07, P4-01, P4-02). Once W0 merges, `build/w1-foundations` is rebased by merge (no history rewrite) onto `main`, and its PR targets `main`.

- **[W1 physics lane]** Folded from `docs/build/lanes/W1-physics.md`; per-ticket evidence in `evidence/P1-01.md`…`P1-04.md`.
  - P1-01 and P1-02 DONE. P1-03 and P1-04 OPEN-WITH-GAP.
  - Defects fixed:
    - **M1 background:** at `atol=1e-12`, densities below atol drifted (ρ_r 25% off a⁻⁴ after 5 e-folds). It now integrates ln ρ.
    - **M2 custom potentials:** V′ and V″ were identically 0 (symbol mismatch).
    - **Inflaton:** the N-form is singular when φ oscillates through V=0, so it integrates in cosmic time.
  - The two drifts the alarm missed (`M_PL_GEV`, `dphi` −3→−4) now fail `backend/tests/unit/test_m1_conformal.py`.
  - **P1-03:** physical couplings (GB/CS tensor action) are opt-in via `RunPipeline(coupling_model="physical")`. M3 gains an optional tensor sound-speed term `k²(1+C)+Ak+B` (C unset = old behaviour, exact). Under "physical", all 33 frozen physics audits pass, including `test_gb_to_zero_decoupling`. Superseded by JAMES DECISION 11: `coupling_model="physical"` is the default (P1-03).
  - **Why physical isn't the default:** it fails 3 adapter tests on the published V2 fixture `kawai-kim-natural.json` (R19, not editable). That fixture's potential parameter names aren't recognised by M2, and f = 7e16 GeV can't drive inflation, which suggests the coupled field is a spectator. → **BLOCKED-ON-JAMES:p1-03-default-coupling**: decide inflaton vs spectator, the units of f and Λ⁴, and the fixture parameterisation. Until then the Gate 1 condition "test_gb_to_zero_decoupling green" isn't met on the default path.
  - **P1-04:** only the mpmath(dps30)-vs-scipy cross-check is implemented (disagreement 0.0 on the audit configs). Kamada et al. 4th-order adiabatic subtraction and the V4 cross-check aren't implemented: the papers are unreachable (arXiv is blocked from the sandbox), and the work needs an M3/M4 representation change (M3 omits −a″/a). η_B ≈ 0 today (ΔN_L = 0 with default couplings, 1.6e-58 with physical).
  - **BLOCKED-ON-JAMES:arxiv-access**: either allow arxiv.org in the environment's network policy, or put PDFs of arXiv:1702.07689, 2007.08029 and 2412.09490 in the repo (licence permitting) or the session.

**[W1 platform lane: P3-06, P4-01, P3-04]** (from `docs/build/lanes/W1-platform.md`)

- **P3-06 error envelope:** `{"detail": {"code", "message", "errors"?}}`. The `ServiceError` `{code, message}` shape sits under FastAPI's `detail` key. That keeps the A8 assertions (`resp.json()["detail"]["code"]`) and FastAPI conventions, and gives one shape for every error (R20).
- **P3-06 `QCOMPASS_ENV`:** defaults to `production`, so an unset environment never relaxes CORS (or, in P3-04, auth).
- **P3-06 readiness:** each store (`ConversationStore`, `AuthStore`, `ScanRegistry`, `RunRegistry`) gains `ping()`. The probe is written against that interface so it survives the P3-01 move to Postgres and the P3-02 queue.

- **P4-01 verdict auth:** correction 9 needs a verified Supabase admin. JWT verification lives in `m8_agent/supabase_auth.py` as the shared module P3-04 builds on, not a one-off. Roles are read through PostgREST with the caller's token, so RLS decides; the service-role key is never used. Only asymmetric algorithms are accepted (ES256/RS256).
- **P4-01 run shape:** `GET …/runs/{id}` returns `qcompass_core.wire.DomainRunResult`, the frontend's type, built from the provenance sidecar (manifest plus terminal status in `payload`). P3-03 replaces the sidecar source with the persisted `RunResult`. An empty `classical_reference_hash` is returned as recorded (`""`), not dropped.
- **P4-01 domain ids:** paths accept full `DomainId`s and short names; responses use the full id.
- **P4-01 literature:** the backend serves its own copy (`m8_agent/data/literature/`); the frontend keeps its fixtures for offline mode, and `test_frontend_contract.py` asserts the two are identical.
- **Local lint hygiene:** `**/.venv` added to the eslint and prettier ignores. A root uv environment held 35k vendored JS files that eslint walked.

- **P3-04 principal model:** one `require_scope` dependency covers HTTP and WebSocket and accepts either credential type. A Supabase user with a non-member tenant, and any cross-tenant resource, gets 404 so tenant and resource existence don't leak; a key pointed at another tenant via the header keeps the existing 403 `TENANT_MISMATCH` (A8). Legacy `/api/runs` (start, get, audit, stream), `/api/approvals`, `/api/models` and `/mcp/tools` now require a principal: they start compute or mutate state, and a public SaaS can't leave them open. `/api/benchmarks` stays public, as A8 pins.
- **P3-04 storage:** implemented on the current SQLite stores' interfaces (`api_keys`, `tenant_members`, scans `tenant_id`). P3-01 ports these tables to Postgres with RLS.

**Behaviour fixes:**

- `admin.verdict.tsx`: a failed verdict fetch now shows an error instead of an endless "Loading…".
- `POST /api/approvals` `scopes`: comma string → list, matching its documented contract.

**BLOCKED-ON-JAMES (platform):**

- None yet.

**[W1 platform lane: P3-01, partial]** (from `docs/build/lanes/W1-platform.md`)

- **[P3-01] Build on main's tenancy schema.** `api_keys`, `scans` and `tenant_budgets` reference `public.tenants`; membership uses `public.tenant_members` (role enum `owner/admin/member/viewer`; `owner` gets admin scopes and is reported as `admin` by `/api/qcompass/tenants`). The external tenant id (header, `Token.tenant_id`, artifact paths) is the tenant **slug**; a UUID is accepted too. P3-04's `extra_scopes` on members is dropped, since main's `tenant_members` has no scopes column; roles alone decide scopes.
- **[P3-01] Local and CI Postgres harness with a Supabase-compat shim** (`ucgle_f1/db/supabase_shim.sql`): applied only where no `auth` schema exists. `pg_cron`'s `create extension` becomes a no-op where it isn't installable. Real Supabase projects are never shimmed.
- **[P3-01] Test safety:** tests never use a pre-existing `DATABASE_URL`; only `TEST_DATABASE_URL` or a cluster they start themselves (R13).
- **[P3-01] Down migrations deprecate, never drop:** tables and their indexes are renamed `_deprecated_*_<version>` (R13).
- **[P3-01] Migration tracking** uses the Supabase CLI's `supabase_migrations.schema_migrations`, so `supabase db push` and the runner agree.
- **[P3-01] New dependency:** `psycopg[binary]>=3.2` (LGPL-3.0, weak copyleft, R11; licence gate 0 violations).
- **[P3-01] BLOCKED-ON-JAMES:DATABASE_URL** (the Supabase Postgres connection string) for staging and production. If it is missing, routes return 503 `BLOCKED-ON-JAMES:DATABASE_URL` and `/readyz` reports not ready.
- **[P3-01] Status DONE** (part 2 moved the package stores to Postgres; no `sqlite3` in `backend/src` or `packages/*/src`, test-enforced). Drift-alarm risk stands: its agent audits need Postgres via the harness's local cluster; any fix to that workflow is James-only.


**[W1 platform lane: P3-01 part 2, P3-02, P3-03, P3-05]** (from `docs/build/lanes/W1-platform.md`)

- **[P3-01] Package stores take an injected SQLAlchemy `Engine`.** Packages can't import `ucgle_f1` (boundary guard), so `qcompass_core.db.engine_from_env()` resolves `DATABASE_URL` with the same rules as `ucgle_f1.db.engine` (psycopg 3 URL rewrite, `BLOCKED-ON-JAMES:DATABASE_URL` when missing, no fallback). The two are kept in step by hand; the backend cannot depend on `qcompass-core` (it is an optional extra), so one shared module is not possible without moving the backend's engine. The API and worker always inject their own engine.
- **[P3-01] Pricing cache and free-tier ledger keep their offline modes for the standalone library.** They were never SQLite (JSON files, in memory). With an engine they are Postgres (`router_pricing_cache`, `router_free_tier_ledger`); without one, `pip install qcompass-router` still works offline. Calibration and the leaderboard have no non-DB mode any more (their SQLite files are gone).
- **[P3-01] Free-tier ledger accounts:** `house` (PHC's provider accounts, service-only) or `tenant:<uuid>` (a tenant's own account, tenant RLS). `consume` is an atomic SQL decrement so two workers can't double-spend a tier.
- **[P3-01] Bench leaderboard is publicly readable** (RLS `anon` select), since P2-14 publishes it on a public page; only the service role writes.
- **[P3-01] One test database per process:** `ucgle_f1.db.pytest_plugin.scratch_database()` is shared by the backend's autouse fixtures and `packages/conftest.py`'s `pg_engine`, so a combined run starts one cluster.
- **[P3-02] Service role per transaction.** `claim_next_job`/`complete_job` (main) and the new `heartbeat_job`/`reap_expired_jobs` check `auth.role() = 'service_role'`. The API and worker connect with the privileged `DATABASE_URL` and set `request.jwt.claims = {"role":"service_role"}` locally in each queue transaction, as PostgREST does for the service key.
- **[P3-02] `complete_job` is redefined** (create or replace) to touch only `running` jobs and to clear `locked_until`; the down migration restores main's body. Without this a stale worker could mark a cancelled or dead-lettered job `succeeded`.
- **[P3-02] Retries are for lost leases only.** A handler exception fails the job at once (deterministic input errors don't improve on retry); a worker that dies loses its lease and the janitor requeues until `max_attempts`, then dead-letters with a `system_incidents` row.
- **[P3-02] Events in Postgres, polled.** Workers write `public.job_events`; streams poll every 0.2 s. No LISTEN/NOTIFY and no broker (R20; Part 4 forbids Redis etc.). The `result` event is a marker; the stream hydrates the body from `run_results`.
- **[P3-02] Job kinds without compute yet** (`scan`, `viz.bake`, `qpu.submit`, `qpu.poll`, `patch.dryrun`) are accepted by the queue and fail with the owning ticket's id (P4-07, P4-04, P2-01, P3-08/P5-05). Nothing is faked (R7).
- **[P3-02] Worker package:** `workers/qcompass_worker` is a uv workspace member (`qcompass-worker`, depends on `ucgle_f1[qcompass]` and the `qcompass` meta-package). It inherits the `ucgle-f1` vs `qcompass-router[braket]` conflict, now declared for it too (correction 3: P2-01 builds the qpu image without Hydra).
- **[P3-02] Submit validates the envelope only** (`Manifest.model_validate`, 422 `INVALID_INPUT`); domain validation (`prepare`) runs in the worker. A duplicate client-supplied `runId` is 409 `CONFLICT`. A run without a bound tenant (in-process MCP tool use) is recorded under the dev tenant slug `dev`.
- **[P3-02] `RunPipeline.run(cfg, on_module=None)`**: optional callback after each module's existing timing line. Physics unchanged; the physics lane owns the rest of `pipeline.py`.
- **[P3-03] Non-finite floats** are stored as `"NaN"`/`"Infinity"` strings (jsonb has none); pydantic reads them back as floats.
- **[P3-03] Artefacts:** `run-artifacts/<run_id>/provenance.json` via the Storage REST API with `SUPABASE_SERVICE_ROLE_KEY`; missing key → the row records `BLOCKED-ON-JAMES:SUPABASE_SERVICE_ROLE_KEY`.
- **[P3-05] One limits table, checked for drift.** `ucgle_f1.plans.PLAN_LIMITS` copies `src/lib/billing.ts`; a backend test parses the TS file and fails on any difference. A generated shared file would need the backend image to read the frontend tree; the drift test keeps one source of truth (the pricing page) without that.
- **[P3-05] Limits are checked inside the enqueue transaction** with the tenant row locked, so two concurrent submits can't both pass.
- **[P3-05] "Concurrent jobs" = queued + running jobs** of the tenant. "Runs per month" = `public.runs` rows created since the first of the UTC month.
- **[P3-05] Codes:** `PLAN_RUNS_PER_MONTH_EXCEEDED`, `PLAN_CONCURRENT_JOBS_EXCEEDED` (429); `PLAN_GPU_REQUIRED`, `PLAN_TIMELINE_BYTES_EXCEEDED`, `BUDGET_EXCEEDED` (402). Added to both `ServiceErrorCode` literals (Python and TS) and `api_errors.HTTP_STATUS_FOR_CODE` (plus `CONFLICT: 409` for duplicate run ids).
- **[P3-05] Budget hook in both processes:** the old inline hook registration in the API lifespan became `auth.install_budget_hook()`, also called by the worker, which binds each job's tenant while it runs.
- **[P3-05]** `src/services/qcompass/runs.ts::startRun` swallowed every API error and returned a fixture run id; a plan-limit or budget refusal now propagates. `src/services/qcompass/http.ts::apiFetch` threw a bare `Error`; it now throws the same `ServiceError` as `src/lib/apiClient.ts`.
- **[P3-03]** `SUPABASE_SERVICE_ROLE_KEY` (with `SUPABASE_URL`) for artefact uploads to `run-artifacts` in staging/production. Until then provenance rows record the block; no data is lost.


**[W1 platform lane: P4-02, P3-07]** (from `docs/build/lanes/W1-platform.md`)

- **[P4-02] Generator:** `openapi-typescript` 7.13.0 (MIT, exact pin in `package.json`/`bun.lock`; the tool PLAN Part 4 names). `scripts/dump_openapi.py` writes `build_app().openapi()` with sorted keys (deterministic; env-independent, tested); `scripts/gen_sdk_types.sh` writes `packages/ts/qcompass-frontend-sdk/{openapi.json,src/generated/openapi.ts}` and `--check` fails CI (backend job) when either is stale. Both generated files are excluded from prettier/eslint so CI compares bytes.
- **[P4-02] `--default-non-nullable false`:** a defaulted property is not required. FastAPI request bodies may omit defaulted fields (`ChatRequest.provider`), and the API's `required` lists say what it requires.
- **[P4-02] Hand-written SDK types only where OpenAPI has no schema:** free-form request bodies (`POST …/runs` and `POST …/scans` take `dict`; the manifest problem is per-domain), SSE event payloads, and visualization frames (the API types frames as JSON objects). Every response type is an alias of a generated schema.
- **[P4-02] One data source per build:** `DATA_SOURCE = "api"` when `VITE_API_URL` is set, else `"fixtures"` (`src/config/features.ts`). In API mode services call the SDK through `src/lib/sdk.ts` and never fall back to a fixture after an error; errors reach the UI as `ServiceError` (P3-05/P3-06 envelope, unchanged shape). `loadFixture`/`loadJsonlFixture` refuse data fixtures in API mode (client and SSR, `src/lib/fixtureGuard.ts`); the only allowed path is the static F1–F7 formula reference (`formulas/`).
- **[P4-02] One HTTP client (R20):** `src/services/qcompass/http.ts`'s own `fetch` and `src/lib/apiClient.ts`'s own `fetch`/SSE parser are replaced by the SDK client; `apiFetch`/`apiSse` remain as the untyped escape hatch for routes outside the OpenAPI document (cosmic_forge_viz manifest/timeline), on the same client, headers and error mapping.
- **[P4-02] SDK SSE over `fetch`:** `EventSource` can't send `Authorization` and only delivers unnamed events; the API sends named events (`status`, `progress`, `end`). `parseSse` follows the event-stream rules (tested).
- **[P4-02] Workbench cosmology runs go through the platform route** `POST /api/qcompass/domains/cosmology.ucglef1/runs` (validate, enqueue, 202), not the agent route `POST /api/runs`, which requires an approval token and the A6 agent ids. The Configurator follows the run's SSE stream and shows its status and the engine's η_B (`data-testid="workbench-run-status"`); the domain run page follows a queued/running run until it ends (`data-testid="run-status"`). Neither appears before a run is started, so the R19 screenshots are unaffected.
- **[P4-02] Per-environment flags:** `deploy/web/{staging,production}.env` (public `VITE_*` flags), `VITE_API_URL` from each environment's Cloud Run API URL (P3-07).
- **[P4-02] Live e2e:** separate Playwright config `playwright.live.config.ts` (testDir `e2e/live`, ignored by the main config) and CI job `e2e-live` with a `postgres:16.4` service. `scripts/live_stack.py` starts uvicorn + `python -m qcompass_worker` on the backend's test harness database (`TEST_DATABASE_URL` or a throwaway cluster), with `QCOMPASS_ENV=dev` + `QCOMPASS_DEV_ALLOW_ANONYMOUS=1` (test-only; P3-07's `test_deploy_config.py` proves no image/deploy file sets them). Cosmology uses the V2 defaults at precision `fast` (the smallest real config the pipeline supports; ~12 s), chemistry H2/STO-3G classical FCI.
- **[P4-02] Contract mismatches the generated types exposed, fixed:** `assistant.sendMessage` sent `conversation_id`/`model_id` (the API's `ChatRequest` is camelCase → 422); `qcompass/scans` expected an array from `GET /api/qcompass/scans` (the API returns `{scans: ScanEnvelope[]}`); `startScan` posted no `kind` (422). The HEP visualizer panel's literature compare read `/fixtures/literature/…` directly with the wrong shape; it now uses the literature service (API in live mode).
- **[P3-07] One Python environment, two targets per Dockerfile** (`--target api` → `qcompass-api`, `--target worker` → `qcompass-worker`; PLAN Part 4 "one worker image, class by `--classes`"). The last stage stays `api`, so release-please's untargeted `qcompass-runtime:{cpu,cuda12}` builds keep serving the API.
- **[P3-07] Pins:** CPU base `python:3.12.15-slim-bookworm@sha256:6a0e06f5…` (3.12.16 was published 2026-10-28, under two weeks old); uv `astral/uv:0.11.32@sha256:df4cae8f…` (Docker Hub copy of the official image; same uv as CI); CUDA base `nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04@sha256:8aef630a…`. Dependencies: `uv sync --frozen --no-dev --all-packages --extra qcompass --extra viz` from `uv.lock`.
- **[P3-07] CUDA image Python 3.12.13** (uv-managed python-build-standalone): the Debian-built 3.12.15 can't run on Ubuntu's older glibc, and 3.12.13 is the newest 3.12 the pinned uv can install. `jax-cuda12-plugin[with-cuda]==0.12.0.1` (the locked jax version) is added on top of the lock because it is CUDA-only.
- **[P3-07] No system packages:** every locked dependency ships a manylinux or pure-Python wheel (the one sdist, `antlr4-python3-runtime` 4.9.2, is pure Python) and no installed shared object needs the system `libgomp`, so the old `apt-get` compiler/BLAS layers are gone.
- **[P3-07] Worker `/healthz`:** `ucgle_f1.worker.serve_health` serves `GET /healthz` on `$PORT` (or `--health-port`): 200 while the loop turns or a job runs, 503 when stalled or stopping; it never touches the database. Cloud Run services need a listening port, and the HEALTHCHECK needs the same probe.
- **[P3-07] Cloud Run services** (`deploy/*.yaml`, Knative v1, `gcloud run services replace` after `envsubst`): secrets only as Secret Manager references (`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`); workers `minScale 1` (cpu) with CPU always allocated and internal ingress; GPU worker on `nvidia-l4`, `minScale ${GPU_MIN_INSTANCES}` (default 0, so no idle GPU cost until James raises it); runtime account = `GCP_SERVICE_ACCOUNT` (the only account name in Part 6).
- **[P3-07] Deploy workflow:** staging on push to `main`, production on `qcompass-v*` tags and from `release-please.yml` (tags pushed with `GITHUB_TOKEN` don't start other workflows), or by hand. Jobs use GitHub environments `staging`/`production`, check secrets first, and on a miss write `BLOCKED-ON-JAMES:<names>` to the summary and succeed. It also checks (never creates) the Artifact Registry repo and the Secret Manager entries. The web job never deploys without an API URL (a build without `VITE_API_URL` serves fixtures). Third-party actions pinned by SHA: `google-github-actions/auth@7c6bc770…` (v3.0.0), `setup-gcloud@aa5489c8…` (v3.0.1).
- **[P3-07] CI `images` job:** lints both Dockerfiles (`docker build --check`), builds the two CPU images, runs `scripts/container_smoke.sh` against a `postgres:16.4` service: non-root, Python 3.12, `/healthz` HEALTHCHECK, migrations from the API image, `/healthz` + `/readyz` 200, anonymous 401 (production config), worker `/healthz` + "serving cpu", then a real H2 job submitted with an API key through the API container and computed by the worker container. The CUDA image is linted only (size); the deploy workflow builds it.
- **[P4-02] Worker could not run cosmology through the qcompass route:** jobs carry the short domain (`cosmology`) but the plugin registers as `cosmology.ucglef1`, so every such run failed ("No qcompass.domains plugin named 'cosmology'"). `ucgle_f1.worker.resolve_simulation` maps short names to plugin names; the schema route uses it too (it served a generic `{"type": "object"}` for cosmology). Tested in `backend/tests/test_sdk_contract.py`.
- **[P4-02]** Services no longer swallow API errors and return fixtures (`qcompass/runs`, `auth`, `manifestSchema`, `scans`, `visualizer`, `simulator`, `assistant`, `artifacts`).
- **[P4-02]** API mode has no source yet for: the cosmology six-panel timelines (`services/visualizer.ts`; P4-04 real-run timelines), the bench particle-suite leaderboard (P2-14), run artefact listing/download (`/api/runs/{id}/artifacts` does not exist; artefacts are in `run-artifacts` storage, P4-04/P4-06). In API mode these views report the missing source instead of showing fixtures. The domain visualization endpoint still bakes synthetic frames (P4-04 removes `bake_synthetic`). Scans as jobs: P4-07.
- **[P4-02]** None new.
- **[P3-07]** GitHub environment secrets `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT` (staging, production) → Cloud Run deploys.
- **[P3-07]** `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` (staging, production) → Worker deploys.
- **[P3-07]** In each GCP project: Artifact Registry Docker repo `qcompass`; Secret Manager `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`; IAM for the service account; L4 quota.
- **[P3-07]** `QCOMPASS_CORS_ORIGINS` per environment (the workbench origin), and environment variables `VITE_SUPABASE_URL`/`VITE_SUPABASE_PUBLISHABLE_KEY`/`VITE_SUPABASE_PROJECT_ID`.


**[W1 Gate 1 security + code-review fixes]** (from `docs/build/lanes/W1-platform.md`; evidence `docs/build/evidence/W1-security-fixes.md`)

- **[SEC-H1] Tenant passed explicitly, ambient binding kept as defence in depth.** `RunRegistry.submit/get/result/cancel/stream`, the simulator and research tools and `mcp_server._dispatch` take `tenant=`; `/api/runs*`, `/mcp/tools/{name}` and `/v1/chat` pass `principal.tenant_id`. `require_scope`'s dependency is now `async` (it runs `authenticate` with `asyncio.to_thread`), so `set_active_tenant` lands in the request's own context and reaches sync endpoints; the old sync dependency set it in a threadpool copy that was then discarded. The budget hook reads that binding.
- **[SEC-H1] No default tenant outside dev.** `principal.resolve_tenant_slug(None)` returns the bound tenant, else `dev` only under `QCOMPASS_ENV=dev`, else raises `TenantNotBound` (a 500: it marks a programming error, so it fails closed). This replaces the P3-02 decision "a run without a bound tenant is recorded under the dev tenant".
- **[SEC-H1] Slug guard** (`20261031200000_qcompass_tenant_slug_guard.sql`): CHECK `tenants_slug_reserved_check` refuses a slug shaped like any UUID form Postgres casts (hyphens and braces optional, any case), and refuses `dev` unless `created_by is null`. Only the service creates tenants without `created_by` (users' inserts must set it to `auth.uid()` under main's RLS), so the API's own dev tenant still works while no user can create or rename a tenant to `dev`. The constraint is added `NOT VALID` and validated only when no existing row violates it. Otherwise a NOTICE is raised and no rows are rewritten (R13). Local and test databases validated it.
- **[SEC-H1] `AuthStore.resolve_tenant`** orders an id match first (`order by (id = cast(:t as uuid)) desc limit 1`), so a slug that predates the guard can never shadow a tenant id.
- **[SEC-H2] Service-role-only enqueue** (`20261031200100_qcompass_jobs_service_enqueue.sql`): main's "tenant members enqueue jobs" is dropped and replaced by "service role enqueues jobs" (`to service_role`). No SECURITY DEFINER RPC: the only client insert was `src/lib/jobs.ts::enqueueJob`, which nothing imports and whose kinds (`run.simulate`, `run.audit`) no worker handles. Clients enqueue through the API, which checks scopes and plan limits.
- **[SEC-H2] Worker ownership check:** before running a job with a `run_id`, the worker reads `runs.tenant_id` and fails the job with `JOB_TENANT_MISMATCH` (or `JOB_RUN_MISSING`) unless it equals `job.tenant_id`. The run, its events, result and artefacts are not touched, and the handler never runs.
- **[SEC-H2] Tenant-filtered reads:** `JobQueue.result/result_text/provenance/events` take `tenant_uuid`. `RunRegistry` and every qcompass run route pass the run's own tenant, so `job_events`/`run_results`/`run_provenance` rows written under another tenant are never served.
- **[SEC-M1] Run writes stay in the writer's tenants** (`20261031200200_qcompass_runs_tenant_write_check.sql`): "authenticated users create runs", "authors update own runs" and "authors write results" add `tenant_id is null or public.is_tenant_member(tenant_id, auth.uid())` to with-check. `tenant_id is null` keeps the frontend's personal-run persistence (`src/lib/persistence.ts`) working.
- **[SEC-M2] Deploy workflow:**
  - Every action in `deploy.yml` is pinned to a full commit SHA with a `# vX` comment: `actions/checkout@11d5960a…` v4.4.0, `oven-sh/setup-bun@0c5077e5…` v2.2.0 (tags resolved with `git ls-remote`; both are lightweight tags), plus the existing google-github-actions pins. Checkout uses `persist-credentials: false`.
  - The Cloudflare token and account id are no longer job-level env. Only the wrangler step receives them; the check step sees booleans (`secrets.X != ''`).
  - The build is secret-less: `bun install --frozen-lockfile --ignore-scripts`. It was verified locally that the build and `wrangler deploy --dry-run` work that way, so no separate build job is needed.
  - The deploy runs the locked `./node_modules/.bin/wrangler` (4.82.2, `bun.lock`). `bunx wrangler` would download an unpinned copy when none is installed.
  - release-please's `deploy-production` job only calls `./.github/workflows/deploy.yml`, a local path that cannot carry a SHA. It now inherits these pins.
- **[SEC-L1] `/readyz`:** a failed check reports `ok: false` with detail `unavailable`, or a bare `BLOCKED-ON-JAMES:<NAME>` marker (a variable name, never a value), and the exception goes to the log.
- **[SEC-L2] Colliding `runId`:** the least invasive option is a generic 409 `CONFLICT` "runId is not available; choose another runId or omit it". It is identical whether the id belongs to the caller or to another tenant, and never says "exists". Per-tenant id namespaces would change `runs.id` (the primary key that `jobs`, `run_results` and `run_provenance` reference, and that main's storage policy reads), which is far more invasive. Residual: a client still learns that an id it guessed is taken somewhere. Generated ids carry 48 random bits.
- **[SEC-L3] Wall-clock limit:** each handler runs on its own thread, and the loop waits at most `job_timeout_seconds` (`--job-timeout-seconds` / `QCOMPASS_JOB_TIMEOUT_SECONDS`, default 3600 s, the API's Cloud Run timeout; non-positive or invalid values fall back to the default). On expiry:
  - the job fails with `JOB_TIMEOUT: …` and the run is marked failed;
  - the heartbeat stops renewing the lease;
  - the handler's later queue writes raise `JobCancelled` (`_GuardedQueue`).
  Python cannot kill a thread, so the worker's `/healthz` reports 503 while an abandoned handler is still alive, and Cloud Run replaces the container.
- **[SEC-L3] Custom potentials:** `m2_scalar/potentials.py` lives in `backend/src`, not under `backend/audit/physics`, so it may be edited. `_custom_expr` now caps:
  - source length 4096 and AST size 512 nodes;
  - numeric literals at |x| ≤ 1e30, real numbers only (strings, complex and booleans refused);
  - constant exponents at |e| ≤ 64;
  - every constant subexpression at 1000 digits, estimated from the AST without evaluating it.
  `phi**(9**9**9)`, `9**(64*64*64*64)` and `((9**64)**64)**64` are refused in milliseconds; real potentials are unchanged (`tests/unit/test_m2*` pass).
- **[SEC-L4] Visualization:** HTTP and WS look the run up in the caller's tenant (`_stored_run`) before baking: 404 or close 1008 otherwise, and nothing is written. `provenanceSidecar` is now a logical reference relative to the artifacts root (`qcompass/<tenant>/<domain>/<runId>.provenance.json`). The SDK was regenerated: only the field's description changed, and the frontend reads nothing from it.
- **[SEC-L5]** `deploy/qcompass-api.yaml` no longer mounts `SUPABASE_SERVICE_ROLE_KEY`. Grep: only `ucgle_f1/artifacts.py` reads it, called only from `worker._record_provenance`; the API verifies users with JWKS and reads roles with the caller's token.
- **[SEC-verify] `resolve_tenant`:** confirmed: `.first()` with no ORDER BY was nondeterministic when a UUID-shaped slug existed. Fixed as above (SEC-H1).
- **[REV-B1]** Same bug as SEC-H1.
  - With the async `require_scope`, `active_tenant()` is bound in the API process, so the router's budget hook (`auth.install_budget_hook`) gates by the caller's tenant. Before, `gate_spend` received `None` and skipped silently.
  - `cancel_run` is now an MCP tool (approval-gated, tenant-scoped). Another tenant's run, or a missing one, is `NOT_FOUND` before the approval is spent.
  - Async tools run from the sync dispatcher through `mcp_server._run_coroutine`.
- **[REV-B2] Option chosen: label the frames, don't refuse them.** `VisualizationResponse` gains `synthetic: true` and `source: "synthetic-bake"`, and the WS header carries the same flag.
  - The domain visualizer already labels `metadata.synthetic`. `normalizeDomainTimeline` now passes through `source`, and `surface.tsx` says "Synthetic frames — not a computed result. Real-run timelines arrive with P4-04."
  - A synthetic response also never opens the live stream (existing rule).
  - Unknown or foreign run ids are 404 (SEC-L4). The SDK was regenerated.
  - A 501 would have broken A7's visualization contract tests, which R4 forbids weakening. The label keeps them, and R7 is met.
  - The cosmology visualizer card (`CosmologyVisualizerDetail`) is left to the physics lane, which owns the cosmology synthetic badge (decision 13). `VisualizationTimeline.synthetic` is populated for it.
- **[REV-SF1]** New migration `20261031200300_qcompass_queue_lease_guard.sql` (`create or replace`; the down migration restores the 20261031180000 bodies). In the dead-letter branch, the janitor sets the run to `failed` (only if it hasn't ended, and only within the job's tenant) and inserts a `status: failed` job event.
  - Streams are bounded: SSE, WS and `RunRegistry.stream` (`settings.StreamBound`) stop after `QCOMPASS_STREAM_IDLE_SECONDS` (default 900) with no new event, or after `QCOMPASS_STREAM_MAX_SECONDS` (default 7200) overall.
  - When they stop, they emit an `error` event `{code: "STREAM_ABORTED"}`. SSE then sends `end`, WS closes 1000, and the legacy SSE sends `event: error`. Clients may reconnect and replay.
- **[REV-SF2] Lease holder only.**
  - The same migration adds `complete_job(job, worker, result, error) → boolean`, which completes only while `status = 'running' and locked_by = worker`.
  - The old 3-argument `complete_job` now raises, so no caller can bypass the check (its only caller was `JobQueue`).
  - `heartbeat_job` already checked `locked_by`.
  - `JobQueue.set_run_status/save_result/save_provenance/emit` take `job_id` + `worker_id` and apply only under the lease. `set_run_status` and `save_result` never touch a `canceled` run, with or without a lease.
  - The worker's `_GuardedQueue` injects the lease into every handler write and turns a refused write into `JobCancelled`. The worker's own failure and completion paths pass `worker_id` too, so worker A can no longer fail or complete worker B's job or run.
- **[REV-SF4] Agent memory tenancy.** New migration `20261031200400_qcompass_agent_memory_tenancy.sql`:
  - adds nullable `tenant_id` (FK to tenants, indexed) to the six `agent_*` tables;
  - backfills them to the `dev` tenant if one exists, otherwise leaves them null (invisible to everyone);
  - adds member read policies on hypotheses, plans, run links, tool calls and patches. Approval tokens stay service-only, since a token id is a bearer secret.
  - The down migration renames the columns `_deprecated_tenant_id_20261031200400` (R13), and re-applying renames them back.
  `ConversationStore` takes `tenant=` on every method (`None` falls back to `resolve_tenant_slug`, the dev tenant in dev only). `/api/approvals`, `/v1/chat`, `/api/runs`, the MCP patch, hypothesis and cancel tools, and `start_run`/`cancel_run`/`save_plan` all pass the principal's tenant. An approval token issued to one tenant doesn't verify in another. This also closes the approval-token cross-tenant observation from the security section.
- **[REV-SF5] One shape: the platform route.** In API mode `services/simulator.ts` reads `GET /api/qcompass/domains/cosmology.ucglef1/runs/{id}` and streams its `/stream`. This one route serves both run kinds: workbench `qcompass.run` stores `payload.result.run_result`, and agent `ucgle_f1.run` stores the RunResult itself. `cosmologyRunResult` reads either.
  - A not-yet-completed run is `NOT_FOUND`.
  - The cosmology adapter's `run()` calls the new `awaitRun`, which follows the stream to its terminal status and then reads the result.
  - Fixture mode is unchanged byte for byte, so R19 holds (`check_r19.sh` passes).
  - The legacy `/api/runs/*` routes remain for MCP and agent clients.
  - Only API-mode code paths were edited. The cosmology run views and home summary belong to the physics lane.
- **[REV-SF6] Both engine resolvers kept.** `qcompass_core.db` and `ucgle_f1.db.engine` stay separate:
  - `qcompass-core` is only an optional extra (`qcompass`) and a dev-group dependency of the backend.
  - Making the backend's core engine import it would make `qcompass-core` (with `openfermion`, `h5py`, …) a hard runtime dependency of `ucgle_f1`.
  - `qcompass_core` may not import `ucgle_f1` (boundary guard).
  - The drift alarm's `uv sync --package ucgle_f1` still installs the dev group, but a plain `pip install ucgle_f1` would break.
  Parity tests (`test_sf6_*`, 7 cases) assert identical URL rewriting, identical `BLOCKED-ON-JAMES:DATABASE_URL` blocking and identical pool settings. There was no behavioural bug, so these tests pass on 3d2355a too. They are a guard, not a regression test.
- **[REV-nit] JWKS:** an unknown `kid` forces one refetch, rate-limited to one per 30 s per URL, so a rotated Supabase key works without waiting out the 600 s cache and forged kids can't hammer the endpoint. HS256 stays refused. A legacy Supabase project with HS256 signing needs asymmetric JWT signing keys enabled.
- **[REV-nit] CUDA plugin in the lock:** `ucgle_f1` gains the extra `cuda12 = ["jax-cuda12-plugin[with-cuda]==0.12.0.1 ; sys_platform == 'linux'"]`. `uv lock` resolved it with no conflict (+15 packages: the plugin, the pjrt plugin and NVIDIA CUDA wheels). `Dockerfile.cuda12` syncs `--extra cuda12` and installs nothing outside the lock (`docker build --check`: no warnings). CI's `UV_SYNC` doesn't select this extra, so the licence gate's environment is unchanged. The NVIDIA wheels' own licence covers the CUDA image as before.
- **[REV-nit] uv workspace:** `packages/__pycache__` added to `[tool.uv.workspace].exclude`.
- **[REV-nit] Artefacts in API mode:** `services/artifacts.ts` `listArtifacts`/`downloadArtifact` throw `NOT_IMPLEMENTED` ("not available from the API until P4-04/P4-06") instead of calling the nonexistent `/api/runs/{id}/artifacts*` routes.
- **[REV-nit] openapi-spec-validator: not a bug.** It is not a backend runtime dependency. It appears only in the backend's `[dependency-groups] dev` (`backend/pyproject.toml`) and the root dev group. Nothing changed.
- **[REV-nit] `A_END_H_END`:** dropped by the coordinator. The physics lane owns `couplings.py` (LEDGER decision 11).
- **[SEC-H1]** `mcp_server._dispatch` returned `model_dump()` (Python datetimes), so `POST /mcp/tools/get_run` for a run that exists answered 500 (response validation). It was unreachable before, because tenant lookups never found the caller's runs. Every dispatch now returns `model_dump(mode="json")`.
- **[SEC-H1]** If the production Supabase project already has a tenant whose slug is `dev` (with `created_by` set) or is UUID-shaped, `20261031200000` leaves the constraint `NOT VALID` and raises a NOTICE. James should rename that tenant, then run `alter table public.tenants validate constraint tenants_slug_reserved_check`. New rows are guarded either way.
- **[SEC-M2]** None new. The workflow first runs on GitHub with the existing secrets (CI-PENDING).
- **[REV-nit]** `BLOCKED-ON-JAMES:supabase-jwt-signing-keys`, only if the production Supabase project still signs with the legacy HS256 secret. The API accepts only asymmetric (RS256/ES256) keys from the JWKS, so James would enable asymmetric JWT signing keys in the Supabase dashboard. No secret is needed by the code.
- **[REV-SF4]** If production agent rows exist with no `dev` tenant, they stay `tenant_id is null` (invisible). Assigning them to tenants needs James's call.
- `deploy/qcompass-api.yaml` doesn't provide `SUPABASE_PUBLISHABLE_KEY`, which `supabase_auth` needs for verdict roles (P4-01). Until it is added, those routes answer `BLOCKED-ON-JAMES:SUPABASE_PUBLISHABLE_KEY`.
- The other `release-please.yml` jobs (outside this finding's scope) still use tag-pinned actions (`release-please-action@v4`, `pypa/gh-action-pypi-publish@release/v1`, …).
- **[W1 security lane] Commit-trailer slip.** Merge commit `4cad980` on `build/w1-platform` (merging `9edef41`, docs only) has git's default message without the two attribution lines. It was already pushed; rewriting it would need a force-push (R12), so it stays and is recorded here.


**[W1 physics lane part 2: P1-03 default coupling (Decision 11), D13a badge]** (from `docs/build/lanes/W1-physics-2.md`; evidence `docs/build/evidence/P1-03.md`)

- **[P1-03] `coupling_model="physical"` is the default.** The option exists only on `RunPipeline` (`m7_infer/pipeline.py`). `RunConfig`, the hydra config loader and the API schema have no coupling-model field, so nothing changes there and the OpenAPI/SDK types stay the same. `"schematic"` stays available as an opt-in.
- **[P1-03] Units.** Everything inside the engine is in reduced-Planck units (M_Pl = `M_PL_GEV` = 2.4352e18 GeV = 1; the LEDGER's 2.44e18 is the same constant to three figures). Two mixed-unit uses in M7 were found and fixed at the API boundary:
  - `reheating.Gamma_phi`: the UI labels it "[GeV]", but it was passed raw to M1, which works in M_Pl. It is now divided by `M_PL_GEV`.
  - The schematic CS term used θ_grav/f_a with f_a in GeV. It now uses f_a/`M_PL_GEV`.
  - M2's potentials were already all in M_Pl units, so no change there. `couplings.py` already converted `couplings.f_a` with `M_PL_GEV`.
  - Outside this lane's scope (M4), recorded for P1-04: `m4_anomaly` divides an M_Pl-unit source by `T_reh_GeV**3`, which mixes units.
- **[P1-03] Mapping to Kawai & Kim.** It is recorded in the `couplings.py` docstring.
  - GB: −½ξ(φ)R²_GB ≡ −(1/16)ξ_KK R²_GB, so ξ = ξ_KK/8. ξ_KK = −δ ln[2e^φ η⁴(ie^φ)] with δ = −1, and ξ_KK′ = −δ[1 − (π/3)e^φ E₂(ie^φ)].
  - CS: (1/16)ϑRR̃, so f = ϑ/2, with ϑ = γφ and γ = 1. That means θ_grav/f̂_a = γ/2.
  - `xi` is UCGLE-F1's linear ξ(φ) = xi·φ. It stands for ξ_KK′/8 over the window, but it has no ξ_KK″ term. This is a model difference, not a fit.
  - `M_star`, `M1` and `S_E2` have no counterpart in the tensor action, and M1–M6 do not read them.
  - Kawai & Kim's equation numbers beyond Eq. 2 are still unverified, because arXiv is unreachable from the sandbox.
- **[P1-03] Natural benchmark.** New module `m2_scalar/natural.py`, with slow-roll closed forms for V = Λ⁴(1 − cos φ/f_a). M2's minus sign is the paper's "±" under φ → φ + πf_a.
  - f_a = 8.7, A_s = 2.207e-9, N_e = 60 give Λ = 7.1154324599829784e-3 M_Pl and m = Λ²/f_a = 5.82e-6 M_Pl. Decision 11 quotes m ≈ 5e-6; at one significant figure the computed value rounds to 6e-6, and it is reported as computed.
  - The test reproduces A_s to 1e-9 through M2's compiled V and V′, with a root-found φ_end and the N integral done by quadrature, independently of the closed form.
- **[P1-03] Initial field for `natural`.** φ₀ = min(φ_*(N_e = 60), πf_a(1 − 10⁻⁶)).
  - For the benchmark's f_a = 8.7, the old hilltop start (≈ 1650 e-folds) never ends inflation within the trajectory's N_max = 80, so φ₀ is now the N_e = 60 pivot.
  - For f_a ≲ 1 (the audit conftest's f_a = 1), φ_*(60) is within 1e-13 of the hilltop. The old hilltop bound still applies, so audit behaviour is unchanged.
- **[P1-03] `A_END_H_END` is derived, and it does not cancel.**
  - Its value is −1/`M3_TAU_END["high"]` = 10³: the end of inflation (ε = 1) is the last point of M3's high-precision τ window, and τ(N_end) = −1/(a_end H_end).
  - The normalisation of a is a gauge freedom. Under a → ca, τ → τ/c and k → ck, the coefficients scale as B → c²B, A·k → c²A·k and C → C, so |β|² depends only on k/(aH). A unit test checks this scaling for c = 0.1 and 10, and another checks the window condition.
  - What it fixes is the unit of M3's comoving k: k_M3 = 1 is k = 10⁻³ a_end H_end.
  - **Assumption (recorded, not derivable here):** M3's τ grid (−5 → {−1, −0.1, −1e-3}) and k grids (10^±1, ±2, ±3) are the pipeline's pre-existing design, not values from the paper. Whether Kawai & Kim's relevant band matches them needs the paper. The τ-grid constants now live in one place (`couplings.M3_TAU_START` and `M3_TAU_END`), which the pipeline imports.
- **[P1-03] Fixture.** `public/fixtures/runs/kawai-kim-natural.json`: potential params `{f: 7e16, Lambda4: 2.5e-7}` → `{f_a: 8.7, Lambda: 0.0071154324599829784}`, and top-level `"synthetic": true` added.
  - The JSON diff touches only those five paths. All result fields are byte-for-byte unchanged (R7).
  - The couplings (`xi` 0.0085, `theta_grav` 0.78, `f_a` 1e16 GeV, `M_star`, `M1`, `S_E2`) are UCGLE-F1's own parameters. Decision 11 keeps them, so they are not changed. The paper's δ and γ are mapped in the docstring rather than turned into new values.
- **[P1-03] CI.** `backend-slow` now runs `pytest -q -m slow` with no `--deselect`. The `known-gap` job is removed.
- **[D13a] Badge placement.** The cosmology run views are the visualizer pages (in the default build, cosmology has no `/domains/.../runs` fixtures; `DOMAIN_FIXTURE_INDEX["cosmology.ucglef1"]` is empty).
  - Run list: on the `/visualizer` card of each run whose bundled run fixture is flagged.
  - Run detail header: the visualizer toolbar lead (`data-testid="cosmology-run-header"`).
  - Home: the F1 summary card header (`data-testid="f1-summary-header"`), which shows the V2 fixture's coupling numbers. It is shown while the form's couplings equal the fixture's, and disappears once the user edits them away.
  - The flag comes from the new `getRunFixtureSummary(id)` in `services/simulator.ts`. It is fixture-mode only, reads the bundled file with no DB backfill, and returns `null` with `VITE_API_URL`. It was appended at the end of the file so it does not touch the API-mode branch.
  - `RunResultShape` declares `synthetic: z.boolean().optional()` (it already passes unknown keys through), and `RunResult.synthetic?` is typed.
- **[P1-03 follow-up, coordinator] UI natural/hilltop parameter keys.** The UI sends `{f (GeV), Lambda4}` and `{mu (GeV), p}`; M2 defines `{f_a, Lambda}` and `{V0, mu}` in M_Pl units. The schematic path never evaluated V, so this was latent. Under the physical default, an API-mode run of the UI's V2 default fails. Fixed at the UI/API boundary in the Gate 1 lane `[W1-PARAMS]`, so the configurator's displayed values (R19 page `/`) don't change.
- **[P1-03 follow-up, coordinator] Other cosmology fixtures.** `starobinsky-standard`, `gb-off-control` and `failing-run` also carry hand-written results. Decision 13 names only `kawai-kim-natural`, and labelling the others would change R19 pages beyond rebaseline (a). → `BLOCKED-ON-JAMES:cosmology-fixture-synthetic-labels` (whether to flag them, and under which rebaseline). Resolved by Decision 16: flag all three under rebaseline (a).
- **[P1-03 follow-up] Remaining mixed units on the default path.** M4 divides a Planck-unit source by `T_reh_GeV**3`. It belongs to P1-04 (OPEN-WITH-GAP, `BLOCKED-ON-JAMES:arxiv-access`) and is recorded there.


- **[W1-PARAMS] Potential-parameter boundary (Gate 1)** (from `docs/build/lanes/W1-platform.md`, section "W1 potential-parameter boundary (Gate 1)"; evidence `docs/build/evidence/W1-potential-params.md`). The frontend sent potential parameters M2 does not define (`natural {f, Lambda4}`, `hilltop {mu, p}` with no `V0`). With `coupling_model="physical"` the default (Decision 11), an API run of the Configurator's V2 default failed in the worker with "potential parameters missing: ['f_a', 'Lambda']". This is the fix that `[P1-03 follow-up, coordinator] UI natural/hilltop parameter keys` points to.
- **[W1-PARAMS] One wire shape: the API carries the potential's parameters in the units the Configurator shows, and the backend request model is the boundary.** `ucgle_f1.domain.POTENTIAL_PARAM_FORMS` is the one table of names and units; every name has exactly one unit:
  - starobinsky `M` [M_Pl];
  - natural `f` [GeV] and `Lambda4` [M_Pl⁴] (the Configurator's names), or `f_a` and `Lambda` [M_Pl] (M2's names, which Decision 11 put in `kawai-kim-natural.json` and which the audits, `backend/configs/*.yaml` and the agent tools use);
  - hilltop `V0` [M_Pl⁴], `mu` [GeV], `p` (integer 2–64, default 4);
  - any kind: optional `phi0` [M_Pl] (`initial_field`'s override); custom: the snippet's own symbols.

  A params dict must use one form: mixing natural's two spellings is refused as ambiguous. The run route's request model and the agent's `RunConfig` share this one model (`CosmologyPotential` now subclasses `domain.Potential`), one validator and one conversion.

  M2's natural names stay accepted because Decision 11 put them in `kawai-kim-natural.json`, and R4 protects the tests and audits that send them: `test_qcompass_adapter.py`'s round trip, `backend/audit/conftest.py`, and the agent tests' configs. Refusing them would need James. Hilltop has one form: its `mu` is GeV on the wire, and only `engine()` produces M2's M_Pl value.
- **[W1-PARAMS] Why the backend, not the frontend service layer.**
  - The only M_Pl is `M_PL_GEV` (`m1_background/background.py`). Converting in `services/simulator.ts` would need a second constant in TypeScript, or a generated copy of it.
  - The physics lane already converts the other GeV inputs in the backend: `Γ_φ` at the pipeline's M1 step and `couplings.f_a` in `couplings.py`. The potential's conversion now runs at the pipeline's M2 step, beside Γ_φ.
  - Every client gets the same rule: the UI, the agent's `/api/runs` and MCP tools, hydra YAML configs.
  - A RunConfig stays exactly what the client sent, so a stored run's config re-validates unchanged and round-trips through the qcompass manifest (`test_manifest_round_trip`, R4).
- **[W1-PARAMS] The conversion, exactly once.** `Potential.engine()` returns M2's form: `f_a = f / M_PL_GEV`, `Lambda = Lambda4 ** 0.25`, hilltop `mu / M_PL_GEV`. Every other parameter (M, V0, p, phi0, M2's natural names, custom symbols) passes through as the same float objects. It returns an `EnginePotential`, whose `engine()` is itself, so nothing is converted twice. `RunPipeline.run` applies it at the M2 step. `compile_potential`, `initial_field` and `coupling_profile` also call it, which is a no-op on a converted potential, so a GeV value can never reach M2 unconverted. Existing engine-form configs (the audits, the Decision 11 fixture, Starobinsky) produce bit-identical results: the adapter's `data_regression` snapshot and the slow suite, `test_gb_to_zero_decoupling` included, pass unchanged.
- **[W1-PARAMS] Validation and 422.**
  - `domain.Potential` refuses unknown names, mixed spellings, non-finite values, non-positive dimensionful parameters, and a `p` that is not an integer from 2 to 64. Each message names the kind and the accepted forms with their units.
  - Completeness (every parameter of the chosen form) is required by `CosmologyPotential`, the run route's model, not by `domain.Potential`. The agent's A1 audit (`backend/audit/agent/test_a1_schema.py`, frozen) parses a partial natural dict through `StartRunInput`.
  - `POST /api/qcompass/domains/{d}/runs` now calls the plugin's optional `validate_problem` before enqueueing. Cosmology's parses the `CosmologyManifest` and compiles the potential in M2's units with every parameter bound (`potential_args`). A failure is 422 `INVALID_INPUT`, with one message part per error (`api_errors.invalid_input`). Before, a bad problem was queued (202) and failed in the worker.
  - `POST /api/runs` answers a refused RunConfig with 422 instead of 500.
- **[W1-PARAMS] Hilltop V0: a Configurator field, never invented by the API.** `V0` is added to the Configurator's hilltop parameters, defaulting to 1e-7 M_Pl⁴. That is the value the V(ψ) preview always drew (`potentialEvaluator.ts` hard-coded it), so the run now uses the V(ψ) the user sees, and the preview reads the field. The API supplies no V0: a hilltop without one is 422 "missing V0 [M_Pl^4]". No R19 page shows hilltop, because they render the natural default. The radio hint "μ, p" is on the R19 default page, so it stays as it is.
- **[W1-PARAMS] Hilltop p: generalised, not refused.** M2's hilltop is now V0 (1 − (φ/μ)^p) for an integer p from 2 to 64, default 4. p is an integer exponent inside the sympy expression, not a lambdify argument. So p = 4, or no p, builds the original expression symbol for symbol and lambdifies the same code:
  - `test_hilltop_p4_is_the_original_expression_symbol_for_symbol` checks `srepr` equality;
  - `test_hilltop_p4_values_are_bit_identical_to_the_original` checks V, V′ and V″ with `array_equal`.

  No existing test used hilltop, and the fast and slow suites are unchanged. This was chosen over refusing p ≠ 4 because the Configurator exposes p and V0(1 − (φ/μ)^p) is the standard hilltop family.
- **[W1-PARAMS] SDK types.** `Potential.params`'s OpenAPI schema is now `anyOf` of the per-kind forms, with units in each description. It is built from the same table (`WithJsonSchema`). `openapi.json` and `openapi.ts` were regenerated (`gen_sdk_types.sh --check` passes). `services/simulator.ts` types the problem as `config satisfies sdk.RunConfig`. The cosmology manifest schema (`GET …/schema`) marks every parameter of a form as required.
- **[W1-PARAMS] One source for the Configurator's defaults.** `src/lib/configDefaults.json` holds `defaultsForPotential`'s values and the V2 baseline. `configDefaults.ts` imports it, and the backend test reads it. Values and key order are unchanged for natural, Starobinsky and the V2 couplings (the R19 pages are pixel-identical to `040bc36`, see evidence). `defaultsForPotential` still returns a fresh object.
- **[W1-PARAMS] Custom potentials.** `compile_potential` now refuses a symbol that `params` does not bind ("custom potential: unbound parameter(s) […]"). Before, this failed only when V was first evaluated. A snippet that is not one expression is now a `ValueError` naming the problem (it was a bare `SyntaxError`), so the route answers 422.
- **[W1-PARAMS] `ui-v2-defaults-vs-paper-benchmark`: resolved by JAMES DECISION 15, no longer blocked.** The lane raised it as BLOCKED-ON-JAMES. The Configurator's V2 natural default, `{f: 7e16 GeV, Lambda4: 2.5e-7 M_Pl⁴}`, is f_a = 0.0287 M_Pl and Λ = 0.0224 M_Pl, not Decision 11's paper benchmark (f_a = 8.7 M_Pl, Λ = 0.0071154 M_Pl). With the units right it is accepted (202) but does not inflate under the physical default: |η| ≈ 1/f_a² ≈ 1200, and `coupling_profile` refuses "trajectory covers τ ≥ -0.0013 only; M3 needs τ ≥ -5.0". So `e2e-live` still failed (run status `failed`, spec expects `completed`), no longer at the parameters. The lane left the displayed defaults alone (R19) and offered (a) the paper benchmark in Configurator units, (b) an e2e-live config that inflates, or (c) e2e-live red until a decision. Decision 15 chose (a): f = 2.118624e19 GeV (8.7 × `M_PL_GEV`) and Λ⁴ = 2.563334027300118e-9 M_Pl⁴, which convert back to f_a = 8.7 and Λ = 0.0071154324599829784 exactly; per the lane, the run then completes at "fast" (η_B NaN from the budget gate, which the spec accepts). The change joins rebaseline (a) and is round 3B work (PROGRESS.md).
- **[W1-PARAMS] Note, custom source format (not changed by the lane).** The Configurator's `DEFAULT_CUSTOM_PYTHON` is a `def V(psi):` function, and its linter (`potentialValidator.ts`) requires one. The backend compiles one expression in `phi`, although its module docstring says "defines a `V(phi, **params)` function". This is a source-format mismatch, not a parameter one. The API now refuses the default snippet at submit with "customPython must be one expression in phi". JAMES DECISION 17 has since picked the form (one sympy expression in φ, with `def V(<name>): return <expr>` also accepted); the change is round 3B work.
- **[W1-PARAMS] Note, hilltop default (not changed).** `{V0: 1e-7, mu: 1e16 GeV, p: 4}` compiles but does not inflate under the physical model either (τ ≥ -0.0247 only). It is a UI default, not a benchmark.


- **[Gate 1 round 2, lane DB]** (from `docs/build/lanes/W1-sec-db.md`; evidence `docs/build/evidence/W1-security-round2-db.md`). Round-2 verifier findings on the database, authorisation, approval tokens and run ids (clusters c1-tenant, c2-rls, c4-memory), fixed on `build/w1-sec-db` from base `9c6bf4c`. Every finding was reproduced on `9c6bf4c` before it was fixed; none was a false positive. Regression tests: `backend/tests/test_security_gate1_round2.py`, plus the two rewritten SEC-H1 tests in `backend/tests/test_security_gate1.py`. New migrations `20261102100000`–`20261102100300` (the lane's range is `…100000`–`…104959`). Finding ids:
  - R2-DEV-SLUG (c1 MEDIUM, c2 MEDIUM): the `dev` slug reservation is bypassed by nulling `created_by` in the same UPDATE; `AuthStore.ensure_tenant('dev')` then returns the user's tenant.
  - R2-SF4-BACKFILL (c1 MEDIUM, c2 HIGH, c4 MEDIUM): `20261031200400` backfills every legacy agent row into a user-owned `dev` tenant.
  - R2-H1-TESTS (c1 LOW): two SEC-H1 regression tests failed on `3d2355a` only through ImportError / FileNotFoundError.
  - R2-CHAT-LOOP (c1 LOW): `_run_coroutine` blocks the `/v1/chat` event loop while `cancel_run` runs.
  - R2-UUID-SLUG (c1 NIT): the UUID-shaped-slug regex misses forms Postgres casts to uuid.
  - R2-TIER (c2 HIGH): an owner raises their own `subscription_tier` and escapes every plan limit.
  - R2-M1-USING (c2, M1 partial): USING clauses of runs update/delete and "authors write results"; `audit_reports`, `viz_timelines` and the storage write/update/delete policies had no tenant test.
  - R2-VIEWER-PLANT (c2 MEDIUM): a viewer plants completed tenant runs that the API serves.
  - R2-QUOTA (c2 MEDIUM): the runs-per-month quota counts client-written rows (permanent lockout).
  - R2-STORAGE-SHIM (c2 LOW): the test shim grants nothing on `storage.objects`, so storage RLS tests were vacuous.
  - R2-FORGED-REPORT (c2 residual): nothing detects rows forged before the fixes.
  - R2-TOKEN-LOG (c4 LOW): approval token ids in `agent_tool_calls.requestJson`, readable by every member.
  - R2-TOKEN-RACE (c4 LOW): `consume_approval` is read-then-write, so one-shot tokens can be spent twice across instances.
  - R2-TOKEN-TTL (c4 LOW): `*` tokens are never consumed, the TTL is unbounded, and a huge TTL is a 500.
  - R2-RUN-ID (c4 L2 open + LOW): run ids are one global client-chosen namespace (existence oracle and squatting).
  - R2-PLAN-PATH (c4 NIT): `agent_plans.path` is an absolute server path built from an unsanitised conversation id.
  - R2-START-ORDER (c4 NIT): `start_run` spends the token before validating and never checks the hypothesis.
- **[R2-DEV-SLUG][R2-TIER] One trigger for column rules on `public.tenants`** (`20261102100000_qcompass_tenant_write_guard.sql`). `tenants_write_guard` (BEFORE INSERT OR UPDATE) applies to every caller that is neither `service_role` nor the table owner, judged by `public.qcompass_privileged_writer(regclass)`: `pg_has_role(current_user, <owner>, 'MEMBER') or pg_has_role(current_user, 'service_role', 'MEMBER')`. It keys on the database role, not on a JWT claim, so a PostgREST user (`authenticated`) is always restricted, while the API and worker (owner connection), `ensure_personal_tenant` (SECURITY DEFINER, owner) and migrations are not.
  - INSERT: `subscription_tier` is forced to `free`.
  - UPDATE: `subscription_tier` and `created_by` are immutable (`insufficient_privilege`).
  - INSERT or a slug change: `lower(btrim(slug)) = 'dev'` is refused (`check_violation`, the same SQLSTATE as `tenants_slug_reserved_check`, so round-1 assertions hold).
  - A trigger rather than a column REVOKE: main's "owners update tenants" policy and the table-level grants stay as they are, the rule does not depend on a user-writable column, and service writes need no special role.
- **[R2-DEV-SLUG] The API never uses a user-owned `dev`.** A `dev` tenant is the service's only when `created_by is null` and it has no `tenant_members` row (that is what `AuthStore.ensure_tenant('dev')` creates). `AuthStore.resolve_tenant('dev')` returns None for any other `dev`; `ensure_tenant('dev')` raises `AuthError` (`TENANT_RESERVED`, message `BLOCKED-ON-JAMES:rename-user-owned-dev-tenant`) instead of returning it. The owner still reaches their tenant by its UUID. The same rule (`auth._USER_OWNED_DEV`) is the one the backfill fix uses.
- **[R2-SF4-BACKFILL] New migration, `20261031200400` not edited** (`20261102100100_qcompass_agent_memory_dev_backfill_fix.sql`). It sets `tenant_id` back to null on rows of the six `agent_*` tables whose tenant is a user-owned `dev` (`created_by is not null`, or any member: the round-2 scenarios cover both a creator and the `created_by = null` bypass, where the squatter is a member). Null rows belong to no tenant and are invisible to every caller and to `ConversationStore`. Nothing is deleted; the count is reported with a NOTICE. Why this is safe:
  - No environment has applied `20261031200400`: `DATABASE_URL` is BLOCKED-ON-JAMES, and the backend harness builds a throwaway cluster per run. The first real deploy applies `…200400` and `…100100` in one `supabase db push` / `ucgle_f1.db.migrate` run, so the backfill is undone before any request is served.
  - The service's own `dev` tenant keeps the rows `…200400` gave it.
  - The real owner of a legacy tenant-less row is unknown, so null is the only safe owner.
  - The down migration deliberately changes nothing: restoring the assignment would hand other customers' legacy agent memory back to that user. No column, policy or row is removed in either direction (R13).
- **[R2-UUID-SLUG] Castability, not a regex.** `public.qcompass_text_is_uuid(text)` (IMMUTABLE, `perform _value::uuid` with an `invalid_text_representation` handler) backs a new constraint `tenants_slug_not_uuid_check check (not qcompass_text_is_uuid(slug))`, for every writer. Added NOT VALID and validated only when no row violates it (otherwise a NOTICE), like `20261031200000`. It is a separate constraint so `tenants_slug_reserved_check` (and its round-1 down/up test) stays untouched.
- **[R2-M1-USING][R2-VIEWER-PLANT] Writer role on every client write hung off a run** (`20261102100200_qcompass_client_run_writes.sql`). `public.qcompass_can_write_run(tenant, user)` is `tenant is null or tenant_role(tenant, user) in ('owner','admin','member')`. It is now in the USING and WITH CHECK of runs insert/update/delete, "authors write results", "authors write audits", "authors write timelines" and the storage policies "authors write/update/delete viz-timelines" and "authors write/delete run-artifacts". Viewers and non-members write nothing hung off a tenant run; reads are unchanged.
  - Grep for legitimate client writes before restricting: `supabase/functions/` does not exist. In `src/`, `src/lib/persistence.ts` upserts `runs` (never sets `tenant_id`), `run_results`, `audit_reports`, `viz_timelines` and uploads `viz-timelines/<runId>/timeline.json`; `src/services/simulator.ts` calls those helpers. `src/lib/billing.ts` and `src/lib/tenants.ts` only read `tenants`/`tenant_members`; `startCheckout` is a stub, and there is no Stripe or billing webhook anywhere (`grep -riE 'stripe|webhook'` over `src/`, `supabase/`, `workers/`, `apps/`, `backend/src` finds only `billing.ts`'s note that no provider is wired yet and an unrelated GitHub webhook comment in `tools/patch.py`). All of these keep working: they write personal runs (`tenant_id` null), or runs that main's `20260427001133` backfilled into the author's personal tenant, which the author owns. Billing will set `subscription_tier` through the service role.
  - Writer roles rather than `tenant_id is null` everywhere: authors keep their pre-April runs that the backfill filed under their personal tenant.
- **[R2-VIEWER-PLANT] The API serves only runs it created.** `JobQueue.get_run(…, tenant_uuid=…)`, `list_runs` and the tenant-joined result query add `author_user_id is null`. Every client-written row carries its author (the insert policy requires `author_user_id = auth.uid()`), and the API's rows have none, so a member's client row is that member's data, never a platform run. The round-2 verifier found this marker unsound (`runs.author_user_id` is ON DELETE SET NULL); see `[Gate 1 round 2 verification]`.
- **[R2-QUOTA] The monthly quota counts rows clients cannot forge**: `public.runs` rows of the tenant with `author_user_id is null` created this month (`plans.enforce_at_enqueue`). Clients cannot create such rows, and the update/delete policies never match them (`author_user_id = auth.uid()`). This is equivalent to counting `public.jobs` (one job per API run, service-only since `20261031200100`) and keeps P3-05's boundary test, which seeds runs directly, unchanged. The round-2 verifier found the same gap as for R2-VIEWER-PLANT; see `[Gate 1 round 2 verification]`.
- **[R2-STORAGE-SHIM] Shim grants as on Supabase**: `grant select, insert, update, delete on storage.objects to anon, authenticated, service_role` and `grant select on storage.buckets` (the shim enables no RLS on buckets, so no writes there). `storage.objects` joins the per-test truncation list in `ucgle_f1.db.pytest_plugin`.
- **[R2-FORGED-REPORT] Report, never delete.** `public.qcompass_forged_row_report()` (service-only: execute revoked from `public`, `anon`, `authenticated`) returns `(kind, ref, tenant_id, detail)` rows of three kinds: `job_tenant_differs_from_run` (jobs forged before `20261031200100`), `run_author_not_a_writer` (runs whose author is not owner/admin/member of `tenant_id`, including viewers' plants), and `storage_object_of_such_run`. `20261102100200` prints the count with a NOTICE when it is non-zero.
- **[R2-TOKEN-LOG] Redact at the store.** `ConversationStore.record_tool_call` stores `redact_secrets(request)` and `redact_secrets(response)`: the value of any key `token`, `approval_token` or `*_token` (any case, any depth) becomes `"[redacted]"`. One place covers `/v1/chat` and any future caller.
- **[R2-TOKEN-RACE] One conditional UPDATE spends a token**: `update agent_approval_tokens set consumed = true where "tokenId" = :t and tenant_id = :tenant and not consumed and "expiresAt" > now() and :scope = any(string_to_array(scopes, ',')) returning "tokenId"`. Concurrent spends on any number of instances serialise on the row lock, and the loser's re-checked WHERE fails. The per-process `RLock` no longer matters for tokens.
- **[R2-TOKEN-TTL] No wildcard; one hour at most.** Nothing issues `*` (grep of `src/`, `backend/`, `packages/`, `e2e/`, `acceptance/`: only the store's own comment mentioned it), so `*` is removed rather than bound to a principal. Scopes are the `ApprovalScope` literal in `memory/store.py` (`start_run`, `cancel_run`, `scan_parameters`, `save_plan`, `precision_override`); `get_capabilities().approvalScopesRequired` is built from the same tuple (R20). `POST /api/approvals` takes `scopes: list[ApprovalScope]` (at least one) and `ttl_seconds: int` in (0, 3600], default 3600; anything else is 422 (a huge TTL used to be a 500). `issue_approval` enforces the same rule with ValueError. Every token is one-shot. A legacy `*` row or a row with a null `expiresAt` approves nothing.
- **[R2-RUN-ID] Server ids, per-tenant aliases** (`20261102100300_qcompass_run_client_alias.sql`). `POST /api/qcompass/domains/{d}/runs` always generates `runs.id` (`qc_<domain>_<12 hex>`, retried on the unlikely primary-key collision). A body `runId` (same safe-component grammar, 400 otherwise) is stored in `runs.client_run_id`, unique on `(tenant_id, client_run_id) where client_run_id is not null and author_user_id is null`. A run route accepts the id or the caller's own alias (`get_run` with a tenant: `(id = :id or client_run_id = :id) and tenant_id = … and author_user_id is null order by (id = :id) desc limit 1`), and every later step uses the resolved `rec.id`. The only 409 is reusing one's own alias. This closes both the oracle and squatting, including squatting through a PostgREST insert of a personal run. `runs.id` stays the primary key, so `jobs`, `run_results`, `run_provenance`, `job_events` and storage paths are unchanged. This replaces SEC-L2's round-1 decision (a generic 409 for a runId held by any tenant).
  - Wire and SDK in step: `SubmitRunResponse` gains `clientRunId` (nullable, documented), `runId` is documented as API-generated, `SubmitRunRequest.runId` in `packages/ts/qcompass-frontend-sdk/src/types.ts` is documented as an alias, and `scripts/gen_sdk_types.sh` regenerated `openapi.json`/`openapi.ts`. The frontend never sends `runId` and already uses the response's `runId`; `backend/tests/test_frontend_contract.py` passes unchanged.
- **[R2-PLAN-PATH]** `ConversationStore.save_plan` writes `<artifacts>/agent-sandbox/<tenant slug>/<conversation>/plans/<plan>.json` with `safe_component` on the tenant and the conversation id and `safe_join` under the root (as `qcompass_routes._tenant_root` does), and stores that path relative to the artifacts root. `research.save_plan` validates the conversation id before it spends the approval (INVALID_INPUT).
- **[R2-START-ORDER]** `start_run` checks the agent trace, then that `get_hypothesis(hypothesisId, tenant=…)` exists, then the config, and only then spends the token (as `cancel_run` already did). A foreign or unrecorded hypothesis is `AUDIT_VIOLATION` (409). `cancel_run`/`start_run` run the store calls with `asyncio.to_thread`.
- **[R2-CHAT-LOOP]** `/v1/chat` runs `_dispatch` and `record_tool_call` with `asyncio.to_thread` (which copies the request context), so no tool's database work or `cancel_run`'s own loop runs on the server's event loop. `_run_coroutine` is unchanged; its docstring records that callers on a loop must not call `_dispatch` there.
- **[Gate 1 round 2, lane DB] BLOCKED-ON-JAMES:DATABASE_URL (all findings).** None of the lane's migrations has been applied to a real project. Each was applied, rolled back and re-applied on the local Postgres 16 harness (`test_r2_migrations_are_reversible`).
- **[R2-DEV-SLUG][R2-SF4-BACKFILL] BLOCKED-ON-JAMES:rename-user-owned-dev-tenant.** If production has a user-owned tenant with slug `dev`, the API refuses to use it as its dev tenant, and `20261102100100` sets its legacy agent rows back to null (NOTICE with the count). James should rename that tenant. If `20261031200000` also reported it (constraint NOT VALID), validate `tenants_slug_reserved_check` after the rename.
- **[R2-UUID-SLUG] If an existing slug casts to uuid**, `tenants_slug_not_uuid_check` stays NOT VALID with a NOTICE. James renames the tenant, then runs `alter table public.tenants validate constraint tenants_slug_not_uuid_check`.
- **[R2-FORGED-REPORT] James reviews the forged-row report after the first deploy:** `select * from public.qcompass_forged_row_report()` (service role). The migration NOTICE gives the count. Nothing is deleted automatically.
- **[Gate 1 round 2, lane DB] Note, c1 residuals not assigned to the lane (not changed).** Runs filed under `dev` before SEC-H1 are not reassigned, and a tenant row left NOT VALID by `20261031200000` makes every later UPDATE of that row fail until its slug changes. The lane notes say a rename by James clears both; the round-2 verifier disputes this for the runs: the squatter stays owner/member of that tenant id and keeps reading those runs, `job_events`, provenance and scans.
- **[R2-DEV-SLUG] Note, `TENANT_RESERVED` answers 500 (not changed).** `AuthError("…", code="TENANT_RESERVED")` has no entry in `api_errors.HTTP_STATUS_FOR_CODE`, so a dev-mode request that reaches a user-owned `dev` answers 500 with the BLOCKED-ON-JAMES message. It only happens under `QCOMPASS_ENV=dev` on a database that needs James's rename.


- **[Gate 1 round 2, lane WORKER]** (from `docs/build/lanes/W1-sec-worker.md`; evidence `docs/build/evidence/W1-security-round2-worker.md`). Gate 1 fix lane for the worker: job execution, the queue, run streams and custom potentials. These are cluster c3 of the round-2 verification, plus the SF1, SF2 and SEC-L3 residuals, fixed on `build/w1-sec-worker` from base `9c6bf4c`. New migration `20261102105000_qcompass_queue_attempt_lease.sql`. Finding ids:
  - c3-expr-caps (`m2_scalar/potentials.py:132`): the caps can be bypassed (`^`, constants wrapped in calls, nested power towers). SEC-L3 residual.
  - c3-gil-timeout (`worker.py:448`): the thread-based JOB_TIMEOUT cannot stop a handler that holds the GIL.
  - c3-timeout-parse (`worker.py:51`): inf, nan and values above `TIMEOUT_MAX` are accepted, the CLI value is not checked, and an error in `join` leaves the job unfailed.
  - c3-lock-order (`20261031200300:49`): the dead-letter branch and `cancel_run` take their locks in opposite orders.
  - c3-attempt-lease (`worker.py:82`): an abandoned attempt's in-flight write lands after `_fail`. SF2 residuals (1) and (2): the lease is the worker id alone, terminal runs can change, and the lease check takes no row lock.
  - c3-guarded-queue (SF2 residual 3): `_GuardedQueue` passes `complete`, `heartbeat`, `cancel_run`, `enqueue_run`, `_emit` and `engine` through.
  - c3-stream-bounds (`m8_agent/settings.py:73`): healthy long runs are aborted as idle and the client doesn't reconnect. SF1 residuals (1), (2) and (3): a terminal run with no terminal event, and the max bound checked only on empty polls.
  - c3-claim-after-abandon (`worker.py:350`): the worker keeps claiming after an abandonment, and a lost lease does not end the wait.
  - c3-provenance-upload (`worker.py:134`): provenance is uploaded with no lease check.
  - c3-healthy-race (`worker.py:335`): `healthy()` rebinds the abandoned list while the loop appends to it.
- **[c3-gil-timeout] Each job runs in its own child process.**
  - The child is started with `multiprocessing` "spawn" and is never reused for another job.
  - The parent keeps the heartbeat thread, `/healthz` and the wall-clock limit.
  - At the limit, on a lost lease, or on any error while waiting, the parent terminates the child, waits 2 s, kills it, and waits 2 s more.
  - A child that survives the kill goes into `Worker.abandoned` (see c3-claim-after-abandon).
  - The time limit counts the child's start-up (about 0.4 s).
  - Defence in depth:
    - `RLIMIT_CPU` soft limit = ceil(timeout × usable CPUs) + 30 s; hard limit = soft + 5 s.
    - `PR_SET_PDEATHSIG = SIGKILL` (Linux), so a child dies if its worker dies.
- **[c3-gil-timeout][c3-attempt-lease] The child has no write path of its own.**
  - The handler's `ctx.queue` exposes only `set_run_status`, `save_result`, `record_provenance`, `emit` and `job_status`.
  - Each call is a request over a pipe to the worker process. The worker applies it under the attempt's lease, for the job's own run and tenant only, or refuses it. A refusal raises `JobCancelled` in the handler.
  - The worker serves requests on the same thread that enforces the limit, so once it abandons an attempt, nothing of that attempt is applied.
  - The child still builds its own DB engine from the same environment (`DATABASE_URL`) when handler code reads the database, for example the P3-05 budget hook.
  - Why requests to the parent rather than the child writing through its own engine: a killed child's last statement could still commit after the parent's failure. With requests, writes land strictly before the abandonment.
  - After a refused write, the child gets 2 s to report its own outcome before it is stopped.
  - Handlers are pickled by reference, so they must be module-level functions. `_owned_elsewhere` handlers are now `functools.partial` of a module-level function.
  - The child installs the router budget hook only when the parent has it installed, and sets the job's tenant as before.
- **[c3-gil-timeout] `ucgle_f1.m8_agent/__init__.py` now loads `build_app`/`run` on first use (PEP 562).**
  - Before, `import ucgle_f1.m8_agent.auth` loaded the whole API server, about 1.9 s in every job process.
  - It now takes about 0.4 s for the child's whole start-up.
  - `from ucgle_f1.m8_agent import build_app` works as before.
- **[c3-attempt-lease] A lease is (job, worker id, attempt, run).**
  - `attempt` is `jobs.attempts` as the claim returned it. The next claim increments it, so an abandoned attempt, or a stale worker that reuses the same worker id, never matches again.
  - Migration `20261102105000_qcompass_queue_attempt_lease.sql` adds `heartbeat_job(job, worker, attempt, lease)` and `complete_job(job, worker, attempt, result, error)`. The forms without an attempt now raise, as `20261031200300` did for the 3-argument `complete_job`.
  - The down migration restores the `20261031180000` heartbeat body and the `20261031200300` complete body.
  - In Python, `JobQueue.heartbeat` and `complete` take a keyword-only `attempt`. The run, result, provenance and event writes take `job_id`, `worker_id` and `attempt` together, or none of them. A partial lease raises `ValueError`.
- **[c3-attempt-lease] Lease check and write are one locked step.** The lease subquery locks the job row `FOR SHARE` until the write commits, so a cancel or completion lands wholly before or after the write.
- **[c3-attempt-lease] Terminal run states are sticky in SQL.**
  - Trigger `runs_status_transition` allows only these status changes, for every writer (service, worker, janitor, client): queued → running / failed / canceled; running → completed / failed / canceled. Any other status change raises `check_violation`.
  - `set_run_status` carries the same rule as a predicate, so a refused write returns False instead of raising.
  - `save_result` and `save_provenance` write only while the run is queued or running, so a terminal run's result never changes.
  - If a write is refused because the run already ended while the lease is still held (a re-run of a job whose `complete()` failed), the attempt fails the job. It no longer leaves the job to be retried until it dead-letters.
- **[c3-lock-order] One lock order, the job rows before the run row, everywhere.**
  - `JobQueue.cancel_run` now takes `select … from jobs where run_id = … order by id for update` before the run.
  - That is the janitor's order, and the lease-checked writes' order through `FOR SHARE`.
  - `reap_expired_jobs` is unchanged, so no migration was needed for this item.
- **[c3-stream-bounds] A running job is never idle.**
  - Every lease renewal (every lease/3, 20 s by default) also appends a lease-checked `heartbeat` row to `job_events`, until the attempt sets its run terminal. A 1-hour job adds about 180 rows.
  - The SSE, WS and legacy streams count these rows as activity but never send them to clients. The idle default stays 900 s.
  - The max bound is checked on every poll.
  - The stream checks the run itself after every 1 s of silence. A run that has been terminal for 2 s (database clock, `completed_at`) without a terminal event gets a synthesized terminal `status` event, then `end`. The legacy stream yields the stored result for a completed run.
  - Frontend: one resumable stream (`runEventStream` in `src/lib/sdk.ts`) serves both `services/qcompass/runs.ts` and `services/simulator.ts`. On `STREAM_ABORTED` it asks whether the run ended. If not, it reconnects (at most 20 times) and skips the events it already delivered; the server replays a run's events in id order. A cosmology stream that ends before its run did is now a `STREAM_ABORTED` error instead of a silent end.
- **[c3-expr-caps] Sympy never sees the raw string.**
  - Python's `ast` parses the snippet once. No sympy parser, so `^` stays XOR and is refused with "write powers with `'**'`".
  - The unevaluated tree is allow-listed: numbers, names, `+ - * / **`, unary ±, and calls to `sqrt log exp sin cos tanh cosh sinh` with one argument, or `Rational` with integer literals.
  - Then every node is bounded before any evaluation: literals |x| ≤ 1e30; every exponent |x| ≤ 64, whether or not it looks constant; digits of any exact number ≤ 1000; the factor of an `exp` of a `log` ≤ 64; ≤ 512 nodes, and ≤ 32 levels of real nesting (the left spine of a sum or product counts as one level, as sympy flattens it).
  - A symbol counts as a number of magnitude 1. This keeps the bounds sound when symbols cancel (`phi - phi + 9**9`).
  - Only then is the same tree evaluated with sympy's operators. For every accepted input the result is the expression `sympify` built before, compared with `srepr` (`test_c3_expr_caps_real_potentials_compile_as_before`).
  - Behaviour changes: `^` is refused; a name that is not a declared symbol is a parameter symbol, never a sympy global (`E`, `I`, `oo`, `gamma`…); a function name that isn't called is refused.
  - Measured: a 31-deep `exp(exp(…))` compiles in 0.9 s. A Horner form 50 levels deep took 15 s, which is why nesting is capped.
  - The round-2 verifier found Float magnitudes still unbounded; see `[Gate 1 round 2 verification]`.
- **[c3-timeout-parse] An invalid limit refuses to start.**
  - `QCOMPASS_JOB_TIMEOUT_SECONDS` and the constructor/CLI value must be finite, > 0 and ≤ `threading.TIMEOUT_MAX` (`MAX_JOB_TIMEOUT_SECONDS`).
  - Otherwise `Worker(...)` raises `ValueError`, and `python -m qcompass_worker` exits 2 with the message.
  - Any exception while the worker waits on a job (`JOB_ABANDONED`) stops the child and fails the job.
- **[c3-claim-after-abandon]** `run_once` claims nothing while a job process in `abandoned` is alive; it still runs the janitor. A lost lease (the heartbeat returns False) ends the wait within one 0.1 s poll, and the child is stopped.
- **[c3-provenance-upload]** The worker process does the upload. It renews the lease (`heartbeat_job`) immediately before the Storage put, and uploads nothing if the lease is gone; the row is lease-checked again. The object path stays `run-artifacts/<run>/provenance.json`, which `test_provenance_is_a_row_and_a_run_artifacts_object` pins. An upload already in flight when a cancel commits can still land; every earlier window is closed (see `[Gate 1 round 2 verification]`).
- **[c3-healthy-race]** `healthy()` only reads `abandoned`, under `Worker._lock`. Dead entries are pruned on the loop thread.
- **[Gate 1 round 2, lane WORKER] BLOCKED-ON-JAMES: none.** No fix in this lane needs a secret.


- **[Gate 1 round 2 verification]** Two adversarial verifiers checked the round-2 fixes (evidence `docs/build/evidence/gate1-round2/round2-fix-verify.txt`, keys `db.verify` and `worker.verify`). Lane DB (`build/w1-sec-db` @ `9a6d853`): 15 of 17 items closed, 2 partial, 1 regression, 5 new findings. Lane WORKER (`build/w1-sec-worker` @ `a68c87f`): 8 of 10 items closed, 2 partial, no regression, 1 new finding. For every item the regression test fails before the fix for the finding's own reason (R2-FORGED-REPORT is a new capability, so not applicable). Open items:
  - DB, R2-VIEWER-PLANT partial: viewers are fully closed, but the fix treats `author_user_id is null` as "API-created" while `runs.author_user_id` references `auth.users` ON DELETE SET NULL (`20260424153958`). A writer's planted completed run is served by the API once the writer's account is deleted (probe: GET 200 with `{'forged': true}`), and the owner cannot delete it through the client. Carried into round 3B.
  - DB, R2-QUOTA partial: same cause. A member's 25 future-dated runs count against the quota once their account is deleted (429 "27 used"), and the owner cannot delete them through RLS. The verifier suggests counting only runs that have a matching `public.jobs` row. Carried into round 3B.
  - DB regression (LOW, `20261102100300` line 29): the partial unique index `runs_tenant_client_run_id_key` on `(tenant_id, client_run_id) where author_user_id is null`, with ON DELETE SET NULL, lets a member insert a client run that reuses an API run's alias, so deleting the member's auth account fails with UniqueViolation (account undeletable). Suggested fix: clients may not write `client_run_id`, or the index keys on a positive API-origin marker. Carried into round 3B.
  - DB new MEDIUM (`jobs.py:183`, `plans.py:109`): `author_user_id is null` as proof of API origin, the cause of the two partials above. Suggested fix: mark API rows positively (a matching `public.jobs` row, or a service-only `runs.origin` column), use the same marker in the alias index, and add author-null tenant runs without a job to `qcompass_forged_row_report`. Carried into round 3B.
  - DB new MEDIUM (`m8_agent/auth.py:124`): generic slug squatting, which predates the lane. R2-DEV-SLUG guards only `dev`; `AuthStore.issue()` calls `ensure_tenant(slug)`, which adopts any existing tenant with that slug, including a user's personal tenant renamed to a new customer's slug, whose owner then reads the customer's runs. Carried into round 3B.
  - DB new LOW (`20261031200400` line 32): a single-version down/up of `20261031200400` re-runs its backfill and hands null agent rows, including those `20261102100100` nulled, back to a user-owned `dev`, and `…100100` never runs again. c1's and c4's original repros still fail this way. Carried into round 3B.
  - DB new LOW (`m8_agent/memory/store.py:54`, plausible): `redact_secrets` matches only the keys `token` and `*_token`, so `agent.approvalTokenId` and `tokenId` are stored unredacted in `agent_tool_calls`, which viewers can read. Carried into round 3B.
  - DB new NIT (`m8_agent/auth.py:145`): `TENANT_RESERVED` has no `HTTP_STATUS_FOR_CODE` entry, so it answers 500 (dev mode only; fails closed; the lane reported it). Carried into round 3B.
  - WORKER, c3-expr-caps partial: the listed bypasses are fixed, but Float magnitudes are not bounded. `exp`/`sinh`/`cosh` are refused only over a `log`, and `sin`/`cos`/`tanh` take any argument, so `sin(exp(1e30))` runs for over 60 s and `sin(exp(1e6))` is accepted and takes 4.4 s. In the worker the job process limit stops it (c3-gil-timeout is closed), but the submit-time compile has no time bound (see the WORKER new MEDIUM below). Carried into round 3B.
  - WORKER, c3-provenance-upload partial: the lane's test covers only the window before the upload starts. An upload in flight when `cancel_run` commits still writes the object for the canceled run (only the row is refused), and a stale attempt's in-flight upload can overwrite the reclaiming attempt's object at the same path. The lane notes admit this. Carried into round 3B.
  - WORKER new MEDIUM (`adapters/qcompass.py:198`): the API compiles a tenant's custom potential with sympy at submit (`validate_problem` in `asyncio.to_thread`, `qcompass_routes.py:337`) with no time or CPU bound and no child process. `phi**2 + sin(exp(1e30))` never returns, holds one of the 40 thread-pool threads and a core, and slows `/healthz` from 0.01 s to 3.1 s. Suggested fix: compile in a short-lived child process with a limit of a few seconds (422 on timeout), and bound Float magnitudes in `_Checker`. Carried into round 3B.
- **[W1 merge 3737f6a] η_B gating lands with the physics round 3.** The round-3A verifier called it a hard merge blocker (HIGH). After the Bogoliubov fix the budget is under 0.5 % and M4 divides by T_reh in M_Pl, so the raw η_B is no longer ~1e-42. The worker's V2 validation row (`m8_agent/runs.py` `validation_benchmarks_for`) and the agent's scan cells (`m8_agent/tools/simulator.py`) still used the raw value, so a run whose `RunResult.eta_B` was refused could carry a V2 "Kawai-Kim 1702.07689" row reading "match", or a scan cell with the raw number. Both now apply `pipeline.eta_B_refusal`, the rule `RunResult.eta_B` uses. A refused η_B gives no validation row: `ValidationStatus` has no "refused" value, and a status derived from the raw number would be a claim the pipeline doesn't make. In a scan cell it is NaN, serialised as null. Tests: `backend/tests/unit/test_eta_b_gating.py` (5). The refused-row and refused-cell cases fail on 3737f6a: the row comes back with status "match", and the cell carries 6.1e-10.

## Substitutions

- **[P0-04]** `packages/qcompass/pyproject.toml` extra `tn`: `tensornetwork>=0.5` → `tensornetwork>=0.4.6`. 0.5 was never published (PyPI tops out at 0.4.6), so the lock could not resolve; no code imports tensornetwork.
- **[P0-04]** Starlette ≥1.10 deprecates its httpx test-client path ("install httpx2"); fixed by adding `httpx2>=2.16` (BSD-3-Clause, pydantic org) to the dev group/extra, not by a warning filter.
- **[P0-05]** Licence gate allowlist (`scripts/licence_allowlist.toml`): `posthog-js` (LICENSE file Apache-2.0; package.json says "SEE LICENSE IN LICENSE") and `webgl-constants` (LICENSE file MIT; no package.json licence field). Both read by hand.

**[P0-02 router lane]**

- S1 6B `Cost` pydantic model (`usd`, `pricing_basis`, `cache_age_s`, `live`) → agent `Cost` dataclass
  with `cache_age_s` field and `usd`/`live`/`pricing_basis` properties.
- S2 6B `PricingEngine(seed_yaml=...)` → no per-engine seed path; the package seed is the only seed.
  Constructor is `PricingEngine(cache_dir=None, ttl_seconds=86400, *, ca_bundle, endpoints, ttl_s,
  client_factory, ledger)`.
- S3 6B live cache `{..., "_cached_at"}` → agent cache `{"recorded_at_epoch", "origin": "seed"|"live",
  "entries"}`; live payload scalars overlay the provider's seed entries.
- S4 6B `RoutingDecision.calibration` → same name, optional `dict | None` on the agent model.
- S5 6B free-tier label for seed-flagged backends no ledger tier lists → `<provider>_free_tier`.

- **[P0-03]** `@tanstack/zod-adapter` removed. It requires zod 3 as a peer while the app uses zod 4, which made `npm ci` fail with ERESOLVE on every branch. Replacement: zod 4 schemas passed directly as TanStack Router Standard Schema validators; `fallback(x, d)` → `x.default(d).catch(d)` (or `.optional().catch(undefined)`), behaviour-identical for invalid search params (`src/lib/visualizerSearch.ts`, `src/routes/qa.tsx`, `src/routes/visualizer.tsx`).
- **[P0-03]** Added dev dependency `@testing-library/dom@10.4.2`, the missing peer of `@testing-library/react`; `katex-block.test.tsx` couldn't load without it.

**[W1 platform lane]**

- None yet.

## Conflicts

- **[Gate 0] BLOCKED-ON-JAMES:drift-alarm-workflow.** `ucglef1-drift-alarm.yml` failed on its first-ever run (PR #3, run 41210014497) before it checked anything. Step "Install dirhash" runs `uv pip install --system dirhash>=0.5`, which (a) writes to the runner's system Python 3.10 (`/usr/local/lib/python3.10/dist-packages`, permission denied), and (b) unquoted, the `>` is a shell redirect: it installs unpinned `dirhash` and writes stdout to a file named `=0.5`. The freeze itself is intact: the same dirhash computed locally gives `42805c73…92dd`, and the frozen files are byte-identical to the agent branch. R5 forbids me to edit this workflow, and Gate 0 requires it green, so Gate 0 is blocked on this one item. The minimal patch, which leaves what is checked unchanged:
  ```diff
  -      - name: Install dirhash
  -        run: uv pip install --system dirhash>=0.5
  +      - name: Install dirhash
  +        run: uv pip install "dirhash>=0.5"
  @@ Compute physics dirhash
  -          ACTUAL=$(dirhash -i '*.pyc' '__pycache__' '.pytest_cache' \
  +          ACTUAL=$(uv run --no-sync dirhash -i '*.pyc' '__pycache__' '.pytest_cache' \
  ```
  James can apply it, or authorise me to (it would be the only edit to that file).
  **Resolved by correction 10:** applied exactly these two lines (no other byte of the workflow changed). Locally, `dirhash -i '*.pyc' '__pycache__' '.pytest_cache' --algorithm sha256 backend/audit/physics` on a `git archive` of HEAD gives `42805c73…92dd`, which equals `golden.lock`. CI evidence: evidence/P0-07.md.

- **[P0-05] R19 baseline was an error page.** The cosmology screenshots that P0-01 and the P0-02 frontend lane matched "byte-identical" against `origin/main` show error states for two of the three routes. `/` shows "Something went wrong — fetch failed", and `/visualizer/kawai-kim-natural` shows "Couldn't load this visualization — fetch failed". Main's SSR fixture loader always failed (`require()` in ESM → `http://localhost:8080`), and the client didn't recover in the screenshot window. Only `/visualizer` rendered real content. The P0-05 SSR fix makes both routes render, so their hashes change by design. That exposed a second defect, which is also fixed: loader data crossing SSR lost the non-enumerable `baked` GPU buffers (Phase space panel: "Cannot read properties of undefined (reading 'maxModes')"). Resolution: R19's intent is "cosmology does not regress", so the baseline is re-anchored to the first correct render. That baseline is `docs/build/evidence/screens/r19-baseline/chromium_*.png` (`/` `bbe6927967ecb967`, `/visualizer` `54aa784115904e13`, unchanged from main, `/visualizer/kawai-kim-natural` `cfb38b1376d626b7`); main's error renders are kept beside them as `main-chromium_*.png`. P0-06's Playwright specs assert against the re-anchored baseline on all three browsers.

- **[Part 3 vs repo]** Part 3 describes main as lacking the backend; main actually carries the original UCGLE-F1 backend (pre-branch) and an independent 6A `qcompass-router` (`eec2488`) that depends on a `qcompass-core` absent from main. Resolution per P0-01: backend and packages come from the agent branch.
- **[Part 2 baseline vs measurement]** Orientation numbers differ (see BASELINE.md); measured values recorded, not the orientation values.
- **[Older plan files]** `/root/.claude/plans/the-schematic-a-b-coupling-cozy-hedgehog.md` (production-readiness roadmap) and the v2 prompt set are superseded by PLAN.md.


## Corrected tests

- **[P0-04]** `backend/tests/test_lovable_contract.py` — P0-01 made main's fixtures (`DomainRunResult` shape) the contract, so the branch's assertions targeted a fixture shape that no longer exists (13 failures). Each assertion keeps its intent against main's shape; none was loosened:
  - chemistry manifest round trip. Old: `manifest = qcompass_core.Manifest.model_validate(blob["manifest"])`; `assert key in manifest.problem` / `assert key in request_dump` (chemistry only). New: every one of the 22 run fixtures (all 8 domains) validates as `qcompass_core.wire.DomainRunResult` (`extra="forbid"`) and `assert dumped == blob` (exact, no field dropped or altered) — strictly stronger.
  - provenance. Old: `qcompass_core.ProvenanceRecord.model_validate(prov)` for chemistry, `pytest.skip` when absent. New: `wire.ProvenanceRecordExt.model_validate(prov)` for every fixture, absence is a failure; `assert rec.classical_reference_hash` unchanged.
  - HEP. Old: `assert "value" in entry`, `"unit"`, `"status"`. New: keys `label, value, uncertainty, units, provider, backend, calibration_at` (main's `ParticleObservable`), value numeric, uncertainty ≥ 0.
  - nuclear. Old: `assert md in {...}` unchanged; added: provenance `model_domain` must agree.
  - gravity. Old: top-level `provenance_warning` non-empty for learned fixtures. New: `provenance.provenance_warning` non-empty (main's location) and run/provenance `is_learned_hamiltonian` must agree.
  - verdict. Old: `assert needle in text` for `generated_at:, cutoff_days:, verdicts:, status:`. New: YAML validates as `wire.VerdictSample` (generated_at, reviewer, rows[domain,status,evidence]), non-empty rows, no duplicate domains.
  New wire models: `packages/qcompass-core/src/qcompass_core/wire.py` (mirrors `src/lib/domains/types.ts`; P4-01 reuses as response models). Result: 54 passed.

**[P0-02 router lane]**

- `audit/test_a_router_3.py::test_drift_score_assertion`: old `drift = cache.drift_score(p, b)`;
  new `drift = cache.drift_score(p, b)["two_q_error"]` (D1). Threshold `>= 3.5`, `error_code`, `str(exc)`
  assertions unchanged.
- `audit/test_a_router_6.py::_build_decision_with_transforms`: old `transforms_applied=[r.name ...],
  transform_records=records`; new `transforms_applied=records` (D1).
- `audit/test_a_router_6.py::test_round_trip_into_provenance_record`: old `ProvenanceRecord(provider=...,
  backend=..., error_mitigation_config=...)` (fields that do not exist on qcompass-core's model, which is
  `extra="forbid"` and requires `classical_reference_hash`); new `ProvenanceRecord(classical_reference_hash=
  "sha256:a-router-6", error_mitigation_config={provider, backend, transforms, calibration})`. Old assertion
  kept; added: JSON round trip equality, transform names `["cutting", "obp"]`, provider/backend carried.

**[P0-02 viz lane]** **L1 — `tests/viz/test_server.py::test_ws_stream` ported to the envelope WS protocol.**
Old assertions: first binary message is a msgpack frame (`first[0] != ord("{")`),
`decode_frame(first).domain == "chemistry"`, two more `receive_bytes()`, then
`ws.receive_text() == "__done__"`.
New assertions: a `header` envelope first (`decode(...)["type"] == "header"`,
`payload["n_frames"] == 3`); then the same msgpack check and `decode_frame(first).domain ==
"chemistry"` on the first frame; the two following frames now also assert
`domain == "chemistry"` (strictly stronger); end is `decode(ws.receive_bytes())["type"] == "end"`.
Every behaviour previously asserted (3 frames, msgpack wire, typed decode, explicit end marker) is
still asserted. Reason: one WS protocol (R20) — the envelope protocol is the one the agent tests
and the M8 `/ws/qcompass/...` route already use.

**[P0-02 fe lane]**

- **LF1 — test fix, `src/lib/__tests__/manifest.test.ts`.** The `vi.mock` factory referenced top-level
  `apiFetchMock`/`BackendUnavailable`, which `vi.mock` hoisting evaluates before they exist (file failed to load).
  They are now created with `vi.hoisted(...)`. No assertion changed (old = new, all four tests).
- **LF2 — test retarget, `e2e/visualizer-domain.spec.ts`.** Old: `page.goto("/visualizer/chemistry/test")` expects
  title `/chemistry\/test — Visualizer/`; `/visualizer/cosmology/ucgle-f1-demo` shows link "Open cosmology
  visualizer"; `/visualizer/phantom/x` → 404. New: the folded route — per-domain panel titles + synthetic label for
  the 5 domains with bundled timelines (title `/<id> viz — QCompass/`, no uncaught exceptions); empty state for an
  unknown run; cosmology keeps its existing view; `/domains/phantom/visualizer/x` → 404; old
  `/visualizer/chemistry/test` → 404. The cosmology link assertion moved with the route: the cosmology layout (and
  its link) is still in `DomainVisualizerSurface`, but the folded route keeps main's cosmology view instead.

- **[P0-05]** `packages/qcompass-router/tests/audit/test_a_router_2.py::_fake_response` (a helper, not an assertion). Old: `resp.content = b"{}" if body is None else b"{}"`. New: `resp.content = b"{}"`. Both branches were identical (ruff RUF034), so behaviour is unchanged.

**[P0-06 e2e lane]**

- **`e2e/cosmology-byte-identity.spec.ts`** (agent branch; asserted agent-branch UI that P0-01 replaced with main's):
  - Old: `await expect(page.locator("text=static-shell")).toBeVisible();` and
    `await expect(page.locator('nav[aria-label="Research domain"]')).toHaveCount(0);`.
    New: the default build's domain selector lists exactly one domain, `Cosmology · UCGLE-F1`, enabled
    (`menuitem` count 1, not `aria-disabled`). The "static-shell" pill and the `DomainSwitcher` nav don't exist on main; the
    intent ("cosmology renders as v1 with multi-domain off") is kept.
  - Old: `await page.waitForSelector("text=kawai-kim-natural"); await expect(page).toHaveScreenshot("cosmology-default.png", { fullPage: true, maxDiffPixelRatio: 0.001 });`.
    New: waits for `benchmarks available` (the `/` content; `/` has no run card on main), the same screenshot name and tolerance,
    the build-stamp footer masked, and no error text. Two more routes are pinned the same way (`/visualizer`,
    `/visualizer/kawai-kim-natural`), which is strictly stronger.
- **`e2e/chemistry-h2-flow.spec.ts`**:
  - Old: `page.addInitScript(() => localStorage.setItem("qcompass:overrideMultiDomain","1"))` (the app never read that key).
    New: runs against the all-domains production build.
  - Old: `goto("/domains/chemistry/configurator")`, `text=Chemistry configurator`. New: `goto("/domains/chemistry.molecular/configurator")`,
    h1 `Chemistry · Molecular` and the active Configurator tab.
  - Old: `getByRole("button", { name: /Submit run/i })`, `waitForURL(/domains\/chemistry\/runs\/h2-sto3g/)`. New:
    `getByRole("button", { name: /^Submit$/ })`, `waitForURL(/\/domains\/chemistry\.molecular\/runs\/h2-sto3g$/)`.
  - Old: `text=classical_reference_hash`. New: the "Classical reference" field showing the fixture hash `cls-8a54a2e7`, which is
    stronger.
  - Old: `text=/-1\.137274/`. New: `getByText("-1.137158 Ha")`. Main's fixture classical reference is
    `-1.1371581804212496` Ha (the old number was the agent branch's fixture); P0-01 made main's fixtures win.
- **`e2e/visualizer-domain.spec.ts`**: old `test.skip(!DOMAINS_ENABLED, …)` on 6 tests (`E2E_QCOMPASS_DOMAINS=1` opt-in). New: those
  tests always run against `DOMAINS_URL`. Assertions are unchanged; there are no skips now.
- **`e2e/smoke.spec.ts`**: unchanged. It now passes because of app fix 4.

**[W1 platform lane]**

- `backend/audit/agent/test_a7_qcompass_routes.py::test_get_run_returns_sidecar_payload` (A7 is editable under R4, correction 2). The route's contract changed in P4-01 from the raw sidecar to the frontend's `DomainRunResult`.
  - Old: `assert body["runId"] == run_id` and `assert body["domain"] == "cosmology"`.
  - New: `assert body["id"] == run_id`, `assert body["domain"] == "cosmology.ucglef1"` and `assert "classical_reference_hash" in body["provenance"]`, plus a GET by the full domain id returning the identical body.
  - Same intent (the stored run comes back for its id and domain); strictly more assertions.
- `backend/tests/test_lovable_contract.py::test_verdict_sample_yaml_round_trips_when_present`: the data path moved (correction 9). Old `VERDICT_DIR = _FIXTURES_ROOT / "verdict"` with `"sample-verdict.yaml"`; new `backend/src/ucgle_f1/m8_agent/data/verdicts` with `"sample.yaml"`. Assertions unchanged.

- **P3-04 fixtures** (no assertion changed): `QCOMPASS_DEV_ALLOW_ANONYMOUS=1` alone no longer enables anonymous access; it also needs `QCOMPASS_ENV=dev`.
  - `QCOMPASS_ENV=dev` is now set next to the existing flag in `audit/agent/test_a7_qcompass_routes.py`, `audit/agent/test_a9_observability.py` and `tests/test_path_guards.py`.
  - `tests/agent/test_server_routes.py` gains an autouse fixture setting both, because its routes now require a principal.
  - `tests/test_api_hardening.py` (P3-06, this lane) sends a real tenant API key, so it still exercises production CORS defaults.

**[W1 platform lane: P3-01]**

- **[P3-01]** `audit/agent/test_a8_auth_tenancy.py::test_api_keys_are_stored_only_as_hashes`. Old: dumped the SQLite file `tmp_path/auth.db` and asserted the key was absent. After the move that file no longer existed, so the test would have passed vacuously. New: reads `public.api_keys` in Postgres, asserts rows exist, the plaintext is absent and the SHA-256 hash is present. Strictly stronger.
- **[P3-01]** `…::test_supabase_users_resolve_tenants_through_membership` and `…::test_ws_rejects_supabase_non_member`. Old: user ids `"user-1"`/`"user-2"`. New: real `auth.users` rows (UUIDs), as Supabase issues; `tenant_members.user_id` is a UUID foreign key.
  - Old: `assert tenants == [acme viewer, initech admin]`.
  - New: the same two entries asserted exactly, plus main's `handle_new_user_tenant` trigger's personal tenant (owner → reported `admin`), with exactly 3 tenants.


**[W1 platform lane: P3-01 part 2, P3-02, P3-05]**

- **[P3-01]** Router calibration fixtures and tests (`tests/audit/conftest.py`, `src/qcompass_router/audit/conftest.py`, 5 tests in `tests/test_prompt6_v2.py`, 6 in `tests/test_p002_unification.py`): old `CalibrationCache(db_path=tmp_path / "….sqlite")`; new `CalibrationCache(pg_engine)` (per-test truncated Postgres). Assertions unchanged.
- **[P3-01]** `packages/qcompass-bench/tests/test_runner.py::isolated_store`: old `LeaderboardStore(db_path=tmp_path / "leaderboard.sqlite")` plus `QCOMPASS_BENCH_DB`; new `LeaderboardStore(pg_engine)`. Assertions unchanged.
- **[P3-02]** `backend/tests/agent/test_approval_flow.py::test_full_agent_run_flow` and `backend/audit/agent/test_a7_qcompass_routes.py::test_sse_stream_replays_history_then_status` gain the `inprocess_worker` fixture (a real `Worker.run_forever` on a thread with its own engine). Before P3-02 the API computed the run itself; now a worker must, or the stream would never end. Assertions unchanged.
- **[P3-05]** None. The new `tests/test_worker_queue.py` `api` fixture puts its tenant on `enterprise`, since it submits up to 50 concurrent runs.


**[W1 platform lane: P4-02, P3-07]**

- **[P4-02]** None. No existing test was changed. New: `backend/tests/test_sdk_contract.py` (4), `src/lib/__tests__/sdkClient.test.ts` (3), `src/lib/__tests__/dataSource.test.ts` (4), `e2e/live/workbench-live.spec.ts` (3). New `@endpoint` annotations (simulator, assistant) add parametrized cases to `test_frontend_contract.py`.
- **[P3-07]** None. New: `backend/tests/test_deploy_config.py` (14 cases).


**[W1 Gate 1 security + code-review fixes]**

- **[SEC-L1]** `backend/tests/test_api_hardening.py::test_readyz_not_ready_when_a_dependency_fails`.
  - Old: `assert "db down" in body["checks"]["database"]["detail"]`. That pinned the leak itself.
  - New: the exception carries a host and user. The test asserts detail `== "unavailable"`, that none of `db down`/`db.internal`/`postgres` appears in the response, and that the full message is in the log (`caplog`). Every other assertion is unchanged.
  - `tests/test_postgres_stores.py::test_missing_database_url_is_503_blocked_on_james` is unchanged and still passes (the marker is still public).
- **[SEC-L4]** `backend/audit/agent/test_a7_qcompass_routes.py::test_post_run_writes_provenance_sidecar`.
  - Old: `sidecar = Path(body["provenanceSidecar"]); assert sidecar.exists()`, an absolute server path.
  - New: asserts the reference is relative with no `..`, then the same `exists()` and content assertions on `_artifacts_root().parent / ref`.
- **[SEC-L4]** `…::test_visualization_endpoint_returns_typed_timeline`. Old: GET for a never-submitted id `schwinger-1plus1d`. New: submits a hep run with that `runId` first, then the same GET and assertions. A visualization now needs the caller's run.
- **[SEC-L4]** `backend/audit/agent/test_a8_auth_tenancy.py::test_ws_visualization_accepts_valid_token`: setup only. An `acme` run `kawai-kim-natural` is enqueued before connecting. Assertions are unchanged.
- **[SEC-L5]** `backend/tests/test_deploy_config.py::test_cloud_run_services_are_production_safe`.
  - Old: all three Secret Manager refs required on every service.
  - New: `SECRETS_BY_SERVICE` (API: `DATABASE_URL`, `SUPABASE_URL`; workers: all three), each still required as a `latest` Secret Manager ref. Two assertions are added: the service's secret refs equal that set exactly, and the API has no `SUPABASE_SERVICE_ROLE_KEY`.
  - Stricter for every service. The one dropped requirement, the API holding the key, is the finding.
- **[SEC-H1] Fixtures only, no assertion changed.** In-process tool calls with no principal now need `QCOMPASS_ENV=dev`. Autouse `_dev_tenant` was added in `tests/agent/test_approval_flow.py` and `audit/agent/test_a6_run_traceability.py`, and a `dev_tenant` fixture on `tests/test_worker_queue.py::test_cosmology_progress_comes_from_modules_as_they_finish`.
- New tests:
  - `backend/tests/test_security_gate1.py` (27);
  - `test_deploy_config.py::test_deploy_workflow_pins_every_action_and_scopes_the_cloudflare_token`.
- **[REV-nit]** `audit/agent/test_a8_auth_tenancy.py::test_scopes_are_enforced`: old `assert ok.status_code in {200, 202}`; new `assert ok.status_code == 202`. This is a tightening; submit is always 202 since P3-02.
- **[REV-nit]** `tests/test_worker_queue.py::test_fifty_concurrent_runs_complete_with_two_worker_processes`:
  - The two workers are terminated, and their pipes drained and closed with `communicate()`, in the `finally`.
  - The `statuses`, `workers` and return-code assertions, unchanged, now run after it.
  - Before, two assertions ran inside the `try` and the stderr reads in the `finally` could leak a pipe on failure.
- **[REV-SF2]** `tests/test_worker_queue.py::test_heartbeat_janitor_requeue_and_dead_letter`: the stale-worker call `q.complete(job.id, result=…)` now names its worker (`worker_id="dead-worker-2"`), because completion requires one. Assertion unchanged (the job stays `failed`).
- **[REV-SF4] Fixtures only:**
  - `audit/agent/test_a5_audit_preservation.py` gains an autouse `QCOMPASS_ENV=dev` fixture, because in-process patch tools use the dev tenant.
  - `tests/test_postgres_stores.py::test_backend_migration_is_reversible_without_data_loss` re-applies `20261031200400` after recreating the agent tables, so later tests see the current schema. Its assertions are unchanged.
- **[REV-SF1/SF2] Fixtures only:** `tests/test_postgres_stores.py::test_worker_queue_migration_is_reversible_without_data_loss` re-applies `20261031200300` after it re-creates the 20261031180000 functions, for the same reason as above. Its assertions are unchanged.
- **[REV]** The Gate 1 tests seed legacy runs from their own frozen payload (`backend/tests/data/gate1_run_result.json`, a copy of the 3d2355a run fixture) rather than `public/fixtures/runs/kawai-kim-natural.json`, which the physics lane now owns.
- New tests:
  - `tests/test_security_gate1.py`: B2, SF1 (2), SF2 (3), SF4 (2), JWKS nit, SF6 (7);
  - `audit/agent/test_a8_auth_tenancy.py`: cross-tenant legacy runs and MCP tools, `cancel_run` own run, budget hook;
  - `tests/test_deploy_config.py::test_cuda_image_installs_nothing_outside_the_lock`;
  - `src/lib/__tests__/cosmologyLive.test.ts` (4);
  - `src/lib/visualizer/__tests__/domainFrames.test.ts` (+2).


**[W1 physics lane part 2: P1-03, D13a]**

- `backend/tests/test_qcompass_adapter.py::test_adapter_matches_direct_pipeline_eta_b`. The regression snapshot `test_adapter_matches_direct_pipeline_eta_b.yml` changes:
  - `F_GB: 0.6727334345929941` → `0.6727340798350541`;
  - `audit_passed: 9` → `10`;
  - `audit_total: 15`, `eta_B: NaN` and `eta_B_is_nan: true` are unchanged.

  Why the old values no longer apply: they were the schematic placeholder couplings on the old, un-evaluable parameterisation. Under the physical default, S6 (adiabatic residual) goes from FAIL to PASS_P; every other verdict is the same. The test also gains an assertion that the fixture is M2's natural potential with `kawai_kim_natural_params()` and that the pipeline default is `physical` (tightening).
- `…::test_validate_returns_relative_error`. Same added parameterisation assertion. Its old assertions are unchanged (under the physical default it previously failed with "potential parameters missing").
- `…::test_v2_provenance_sidecar_classical_run_fields`. Same as above.
- The module docstring's NaN paragraph no longer says "schematic A/B coupling profile". The parked `xfail` (V2 η_B) is untouched (R4: only P1-08 removes it).
- `src/lib/__tests__/syntheticFixtures.test.ts`: its comment "Cosmology fixtures … are out of scope here (R19)" is replaced by the new cosmology V2 block. No assertion was removed.


**[W1-PARAMS]** (from `docs/build/lanes/W1-platform.md`, section "W1 potential-parameter boundary (Gate 1)")

- **[W1-PARAMS] Route-contract tests that posted an empty cosmology problem (6 tests).**
  - Tests:
    - `backend/tests/test_security_gate1.py::test_l2_run_id_collision_does_not_reveal_another_tenants_run`;
    - `backend/tests/test_security_gate1.py::test_l4_submit_returns_a_logical_sidecar_reference`;
    - `backend/audit/agent/test_a7_qcompass_routes.py::test_get_run_returns_sidecar_payload`;
    - `backend/audit/agent/test_a7_qcompass_routes.py::test_ws_visualization_streams_decodable_frames`;
    - `backend/audit/agent/test_a8_auth_tenancy.py::test_scopes_are_enforced` (the member's post);
    - `backend/audit/agent/test_a8_auth_tenancy.py::test_cross_tenant_runs_and_scans_are_404`.
  - Old: `json={"manifest": {"problem": {}}}` (L2: `body = {"runId": "qc_shared_id", "manifest": {"problem": {}}}`).
  - New: `json={"manifest": _COSMOLOGY_PROBLEM}`, a complete Starobinsky problem (M = 1e-5, `precision: "fast"`) defined once per file. L2 keeps its `runId`.
  - Why the old ones were wrong: they relied on the run route queueing a cosmology problem the worker refuses, the 202-then-fail path this fix closes. Their subjects are the run-id collision answer, sidecars, visualization frames, scopes and tenancy, none of which is problem validation. Every assertion is unchanged; the new bodies pass on `040bc36` too.
  - `backend/audit/physics/**` is not touched. The physics freeze (`golden.lock`) hashes only that tree.
  - The viewer posts in A8 (`test_scopes_are_enforced`, `test_supabase_users_resolve_tenants_through_membership`) are unchanged, and still answer 403: the scope is checked before the body.
- **[W1-PARAMS] Fixture (input only, no result field).** `public/fixtures/runs/failing-run.json` `config.potential.params`.
  - Old: `{"phi0": 0.4, "Lambda": 0.001}`.
  - New: `{"phi0": 0.4, "V0": 1e-7, "mu": 1e16, "p": 4}`.
  - Why the old one was wrong: `Lambda` was never a hilltop parameter, in M2 or the Configurator, and V0 and mu were missing, so the config could not compile ("potential parameters missing: ['V0', 'mu']"). V0, mu and p are the Configurator's hilltop defaults. `phi0` and every result field are kept. The fixture is not on an R19 page.
- **[W1-PARAMS] New tests** (each fails on `040bc36`, passes now):
  - `backend/tests/test_frontend_potential_configs.py` (30): every frontend config accepted and compiled; the HTTP 202 and 422 cases; the custom snippet refusal;
  - `backend/tests/unit/test_potential_params.py` (23): conversion values, pass-through, idempotence, refusals, hilltop p;
  - `src/lib/__tests__/configDefaults.test.ts` (4).


**[Gate 1 round 2, lane DB]** (from `docs/build/lanes/W1-sec-db.md`)

- **[R2-H1-TESTS]** `backend/tests/test_security_gate1.py::test_h1_no_dev_tenant_fallback_outside_dev` (tightened).
  - Old: `from ucgle_f1.m8_agent.principal import TenantNotBound`; `with pytest.raises(TenantNotBound): RunRegistry().get("run_x")`; in dev, `RunRegistry().get("run_x") is None`. On `3d2355a` it failed at the import, before the fallback ran.
  - New: imports nothing the fix added. Outside dev: `asyncio.run(RunRegistry().submit(cfg))` raises a `RuntimeError` whose type name is `TenantNotBound`, and afterwards no `dev` tenant and no run exist; a run filed under the service's `dev` tenant is refused by `RunRegistry().get` the same way. In dev: the same `get` returns that run and `get("run_x") is None`. On `3d2355a` it fails with `DID NOT RAISE RuntimeError` (the dev fallback created and used the shared tenant).
- **[R2-H1-TESTS]** `backend/tests/test_security_gate1.py::test_h1_resolve_tenant_prefers_the_id_match_and_slug_guard_is_reversible` (tightened).
  - Old: `victim = ensure_tenant("victim")`; `rollback("20261031200000")`; insert the shadow after the victim; `resolve_tenant(victim) == (victim, "victim")` ×5; re-apply; constraint validated. On `3d2355a` it failed at `rollback` (FileNotFoundError). The shadow came second in heap order, so the old lookup may well have returned the right row anyway.
  - New: a context manager drops every CHECK constraint on `tenants` and restores each with its own `pg_get_constraintdef` (no migration file needed); the shadow (slug = a fresh UUID) is inserted before the victim with that id, then the same five assertions run. Then the guard's reversibility: validated → down drops it → up re-adds it validated. On `3d2355a` it fails on the first `resolve_tenant` (the shadow's id is returned).
  - The old shape also broke on this branch: after `rollback("20261031200000")` the new `tenants_slug_not_uuid_check` still refuses the UUID-shaped shadow.
- **[R2-RUN-ID]** `backend/tests/test_security_gate1.py::test_l2_run_id_collision_does_not_reveal_another_tenants_run`.
  - Old: globex submits `runId: qc_shared_id`; acme's submit with the same runId and globex's resubmit both 409 with identical bodies; the message has no "exist" and no id.
  - New: acme's submit is 202 with a different `runId` (its own alias); globex's resubmit is 409 `CONFLICT` with the same message checks; `GET …/runs/qc_shared_id` returns each tenant's own run.
  - Why the old one was wrong: the old 409 for acme encoded the global namespace, which round 2 identified as the squatting bug (c4).
- **[R2-M1-USING]** `backend/tests/test_security_gate1.py::test_m1_runs_policy_migration_is_reversible`.
  - Old: asserted that the head policies contain `is_tenant_member`, rolled back `20261031200200` alone and re-applied it.
  - New: the test records the head policies, rolls back every later migration (newest first), then checks `…200200`'s own state, its down (main's policies) and the re-application of all of them, and finally that the head policies are identical to before.
  - Why the old one was wrong: `20261102100200` now replaces these policies, so the head no longer contains that text, and re-applying `…200200` alone would leave its policies active while `…100200` stays recorded as applied.
- **[R2-START-ORDER] Setup only, no assertion changed.** These tests started runs that cite a hypothesis nobody recorded, which A6 now refuses. Each now records the hypothesis first with `ConversationStore.record_hypothesis` and cites its id (lane notes give no old text beyond this):
  - `backend/tests/test_security_gate1.py::test_h1_post_api_runs_files_the_run_under_the_callers_tenant` (acme's hypothesis);
  - `backend/tests/test_security_gate1.py::test_sf4_agent_memory_is_tenant_scoped` (globex's own hypothesis for the stolen-token request, so it still reaches the token check and gets 403 `APPROVAL_REQUIRED`; acme's for the legitimate request);
  - `backend/tests/agent/test_approval_flow.py::test_full_agent_run_flow`;
  - `backend/audit/agent/test_a6_run_traceability.py::test_start_run_rejects_without_approval`.
- **[R2-START-ORDER]** `backend/audit/agent/test_a6_run_traceability.py::test_start_run_links_run_to_conversation`.
  - Old: cited the literal `hypothesisId="hyp_a6"`, never recorded, and asserted `link.hypothesisId == "hyp_a6"`.
  - New: records a hypothesis in the tenant and cites its generated id; asserts `link.hypothesisId == hyp` (the cited id), with the other assertions unchanged.
  - Why the old one was wrong: the literal was an unrecorded hypothesis, which is exactly what A6 now refuses.
  - Added `test_start_run_rejects_a_hypothesis_the_tenant_never_recorded` (A6): `AUDIT_VIOLATION`, and the token is still unspent.
- **[R2-STORAGE-SHIM]** `backend/src/ucgle_f1/db/pytest_plugin.py`: `storage.objects` added to the per-test truncation list (harness, not a test; lane notes give no old text).
- **[Gate 1 round 2, lane DB] New tests:** `backend/tests/test_security_gate1_round2.py` (19 functions, 26 cases).


**[Gate 1 round 2, lane WORKER]** (from `docs/build/lanes/W1-sec-worker.md`)

- **[c3-gil-timeout]** `backend/tests/test_security_gate1.py::test_l3_hung_handler_is_abandoned_and_the_job_fails_with_job_timeout`.
  - Old:
    - a closure handler `hang` that waits on a `threading.Event`, then tries `save_result` and appends the exception name to a list;
    - `assert worker.healthy() is False, "a wedged handler thread makes /healthz fail"`;
    - after release, `assert late == ["JobCancelled"]` and `assert worker.healthy() is True`.
  - New:
    - the module-level `gate1_worker_handlers.ignore_cancel_and_sleep`, which sleeps 2 s, then tries `save_result` and `completed`;
    - `assert worker.abandoned == [] and worker.healthy() is True`;
    - after 3 s, `assert (tmp_path / "started").exists() and not (tmp_path / "finished").exists()`, `assert q.result("run_hang") is None`, and the run is still `failed`.
  - The JOB_TIMEOUT, run-failed and wall-clock assertions are unchanged.
  - Why:
    - A handler now runs in a spawned process. A closure can't be sent there, and a `threading.Event` or list in the test process can't be shared with it.
    - The old `healthy() is False` described the thread design's limit: a thread can't be killed, so `/healthz` had to fail until the container was replaced.
    - Now the job process is killed at the limit, so nothing wedged remains.
    - "Unhealthy while a job survives the kill" is still tested, by `test_c3_claim_nothing_while_an_abandoned_job_is_alive`.
    - The new test also proves the handler was stopped, not only that its write raised.
- **[c3-attempt-lease]** `backend/tests/test_security_gate1.py::test_sf2_cancel_racing_completion_keeps_the_run_canceled`.
  - Old: a closure handler `finish_after_cancel` coordinated with two `threading.Event`s, and `assert outcome == ["JobCancelled"]`.
  - New: the module-level `gate1_worker_handlers.attempt_gated`, coordinated through files (`started-1`, `go-1`), and `assert (tmp_path / "outcome-1").read_text() == "JobCancelled"`.
  - The other assertions are unchanged. Why: the handler now runs in a spawned child process, so a closure and `threading.Event`s in the test process can't be shared with it.
- **[c3-timeout-parse]** `backend/tests/test_security_gate1.py::test_l3_job_timeout_is_configurable`.
  - Old: `for raw in ("0", "-5", "soon"): assert job_timeout_seconds_default() == 3600, "no way to disable the limit"`.
  - New: the same values give `pytest.raises(ValueError, match="no way to disable the job time limit")`.
  - Why: the finding requires invalid values to refuse to start. Falling back to 3600 silently hid a misconfigured worker. The test's intent, that the limit can't be disabled, is kept.
- **[c3-attempt-lease]** `backend/tests/test_security_gate1.py::test_sf1_sf2_queue_migration_is_reversible`.
  - Old: `rollback("20261031200300")` only; re-apply expected `["20261031200300"]`; final `assert len(procs()) == 2`.
  - New: `rollback("20261102105000")` first, then `rollback("20261031200300")`; re-apply expects `["20261031200300", "20261102105000"]`; final `assert procs() ==` the exact set of three `complete_job` signatures.
  - Why: `20261102105000` replaces the bodies that `20261031200300` created. Rolling `200300` back alone, with the later migration still applied, would restore a lease-checked 4-argument `complete_job` over the refusing one. The new overload makes the count 3. The exact-set check is stricter than a count.
- **[c3-attempt-lease]** `backend/tests/test_postgres_stores.py::test_worker_queue_migration_is_reversible_without_data_loss`.
  - Old: `rollback("20261031180000")` only; in `finally`, `assert apply_migrations(url) == ["20261031180000"]`, then `rollback("20261031200300")` and `apply_migrations(url)`.
  - New: `rollback("20261102105000")`, `rollback("20261031200300")`, `rollback("20261031180000")`, newest first; in `finally`, `assert apply_migrations(url) == ["20261031180000", "20261031200300", "20261102105000"]`.
  - The data-loss and dropped-object assertions are unchanged.
  - Why: `20261102105000` adds a 4-argument `heartbeat_job`, which `20261031180000`'s down doesn't know about. Rolled back out of order, `to_regproc('public.heartbeat_job')` still found that overload. Rolling back newest first is the order the migrations depend on, and it leaves the schema exactly as it was.
- **[c3-attempt-lease] A lease now names its attempt (API change, assertions unchanged).** Each lease-carrying call gained the attempt of its claim (lane notes give no old text; the old calls had no `attempt`):
  - `backend/tests/test_worker_queue.py::test_heartbeat_janitor_requeue_and_dead_letter`: `q.heartbeat(…, attempt=job.attempts)` ×2 and `q.complete(…, attempt=again.attempts, …)`.
  - `backend/tests/test_worker_queue.py::test_cancel_stops_the_lease`: `q.heartbeat(…, attempt=job.attempts)`.
  - `backend/tests/test_security_gate1.py::test_sf1_dead_letter_fails_the_run_and_writes_a_terminal_event`: `set_run_status(…, attempt=job.attempts)`.
  - `backend/tests/test_security_gate1.py::test_sf2_a_stale_worker_cannot_touch_a_reclaimed_job`: every call of worker A or B passes `attempt=a.attempts` or `attempt=b.attempts`.
- **[Gate 1 round 2, lane WORKER] New tests** (from the evidence file; the lane notes list none): `backend/tests/test_security_gate1_worker.py` (34 tests; 33 fail on `9c6bf4c`, 1 passes there), `backend/tests/gate1_worker_handlers.py` (module-level handlers a spawned job process can import), vitest `src/lib/__tests__/streamReconnect.test.ts` (3 cases).
- **[W1 merge f3a1592] Round-2 lanes combined.** `backend/tests/test_security_gate1_round2.py::test_r2_writes_hung_off_a_run_need_a_writer_of_its_tenant` (lane DB). Old: `assert conn.execute("update public.runs set status = 'completed' where id = %s", (run_id,)).rowcount == 1` on a `queued` run. New: `… set status = 'running' …).rowcount == 1`, then `… set status = 'completed' …).rowcount == 1`. Why the old one was wrong: lane WORKER's `runs_status_transition_guard` (`20261102105000`) allows only queued → running/failed/canceled and running → completed/failed/canceled, so CI failed on the merged head with "run run_alice_acme cannot go from queued to completed". No real client makes that jump: the frontend writes queued → running → completed (`src/services/simulator.ts` `setRunStatus`, lines 312 and 328). The test still requires every writer update to succeed (rowcount 1), and now covers two writes instead of one.

## Removals with replacement

- **[P0-04]** `backend/pyproject.toml` extras: `PyTransport>=3.0` (from `multifield`) and `GWBird` (from `gw`). Neither is on any package index, so the workspace lock cannot resolve them. Replacement: manual install steps in `docs/qcompass/optional-backends.md`. The extras keep their names, and the code still imports them lazily.

- **[P0-01]** `src/routes/domains/chemistry/{route,configurator,runs,runs.$id,research}.tsx` → main's generic `src/routes/domains/$domain/*` + `src/components/results/chemistry/ChemistryResult.tsx`.
- **[P0-01]** `src/components/qcompass/domain-switcher.tsx` → `src/components/domain-selector.tsx`.
- **[P0-01]** `src/components/qcompass/json-schema-form.tsx` → `src/components/configurator/QcompassManifestForm.tsx` (rjsf).
- **[P0-01]** `src/components/qcompass/provenance-panel.tsx` → `src/components/ProvenancePanel.tsx`.
- **[P0-01]** `src/services/qcompass/chemistry.ts` → `src/services/qcompass/runs.ts` (generic over `DomainId`).
- **[P0-01]** Branch versions of 50 conflicted paths → see MERGE-MAP.md (fixtures: main's file of the same run id; router: agent lineage + `tests/lineage_6a/`).

**[P0-02 router lane]**

- `audit/test_a_router_4.py::test_decision_fields_non_none_zero_budget` → `qcompass_router/audit/
  test_a_router_4.py::test_decision_carries_all_three_metrics` (floats + ranges) and
  `tests/lineage_6a/test_router_local_aer.py::test_zero_budget_routes_to_local_aer` (same FakeAdapter
  setup, exact values); `transforms_applied`/`reason` presence → `test_required_fields_present_in_schema`,
  `test_no_transforms_yields_empty_list`.
- `audit/test_a_router_4.py::test_decision_fields_non_none_paid` → `tests/lineage_6a/
  test_router_paid_cheapest.py::test_paid_request_picks_cheapest` (identical setup, exact provider/backend/
  cost) and `qcompass_router/audit/test_a_router_4.py::test_decision_carries_metrics_paid_path`.
- `audit/test_a_router_6.py::test_transform_records_carry_into_decision` → `qcompass_router/audit/
  test_a_router_6.py::test_transforms_propagate_to_decision` and `tests/test_p002_unification.py::
  test_transform_records_measure_depth_and_runtime`.
- **[P0-02 router lane]** `packages/qcompass-router/fixtures/pricing_seed.yaml` → merged into `src/qcompass_router/fixtures/pricing_seed.yaml` (see seed reconciliation).

**[P0-02 fe lane]**

- **LF3 — removals.** `routes/visualizer.$domain.$id.tsx`, `.lazy.tsx` → replaced by
  `routes/domains/$domain/visualizer.$id.tsx`. `panels/condmat/LatticeBonds.tsx` → `LatticeWithBondColors.tsx`.
  `panels/condmat/OtocButterfly.tsx` → `OtocButterflyCone.tsx`. `routes/domains/$domain/visualizer.tsx` →
  renamed `visualizer.index.tsx` (same content, serialisable loader).

- **[P0-03]** `package-lock.json`, `bun.lockb`, `pnpm-workspace.yaml` → `bun.lock` + `bunfig.toml`.

- **[P0-05]** `.github/workflows/ci-python.yml` → its jobs moved into `ci.yml` (`backend`, `backend-slow`, `packages`, `frontend`).
- **[P0-05]** The CI step `pytest tests audit … || true`, which ignored per-domain audit failures, → `packages` runs `pytest packages`, which includes every `src/*/audit`, as a hard gate.
- **[P0-05]** The CI step `mypy --strict … || true`, which was never a gate, → `ruff check packages`, which is. Strict mypy has no W0 ticket; it isn't claimed as passing.
- **[P0-05]** The broken boundary guard (`grep -E` with a `(?!…)` lookahead, so it never matched anything; wrong gravity/statmech module dirs) → `grep -P` with corrected `qfull_grav`/`qfull_stat` dirs. All 10 packages pass.

- **[P0-07]** Committed `.env` → `.env.example` (names only) + build/deploy environment variables; local `.env` git-ignored.

- **[P0-05]** CI step `bunx tsc --noEmit -p packages/ts/qcompass-frontend-sdk`, which failed because the SDK has no tsconfig of its own → the root `bunx tsc --noEmit`, whose `tsconfig.json` `include` already covers `packages/ts/qcompass-frontend-sdk/src/**/*.ts`.

- **[P0-01, made explicit after the Gate 0 review]** Agent `src/lib/domains/registry.ts` exports `listDomainPlugins`, `listAllDomainPlugins`, `getDomainPlugin`, `PHASE2_PLACEHOLDERS` and the `DomainPlaceholder` type → main's `getDomain`, `listDomains`, `listDomainSurface` (their only callers were the deleted agent chemistry routes).
- **[P0-01, made explicit after the Gate 0 review]** Agent deps `react-katex`, `@types/react-katex` → main's lazy KaTeX (`src/components/lazy/katex-{block,inline}.tsx`).

**[P0-06 e2e lane]**

- `e2e/playwright.config.ts` (`npm run dev`, port 5173, 3 browsers) → root `playwright.config.ts` (production build, 3 browsers).
- The root config's previous single-chromium project with `bun run preview` (which couldn't serve the Worker build) → the same
  file, now with 3 projects and `scripts/e2e_serve.sh`.

**[W1 platform lane]**

- `CORSMiddleware(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])` → env allowlist with explicit methods and headers.
- `server._status` table, `mcp_server._status_for` table, `qcompass_routes._AUTH_CODE_TO_HTTP` → `api_errors.HTTP_STATUS_FOR_CODE`. The two function names remain as thin delegates.

- `public/fixtures/verdict/sample-verdict.yaml` → `backend/src/ucgle_f1/m8_agent/data/verdicts/sample.yaml`; `sample-verdict.md` → `…/verdicts/sample.md`; `sample-verdict.yaml.json` → removed, replaced by `GET /api/verdict/{id}` (correction 9).
- `src/services/qcompass/verdict.ts` static-fixture read → authenticated API fetch.
- `qcompass_routes._qcompass_auth` / `_maybe_auth_dependency` / `_allow_dev_anonymous` and `server._chat_auth` → `principal.require_scope` / `principal.dev_anonymous_allowed` (one auth path, R20).
- API-key storage `tokens.token_id` (plaintext) → `api_keys.key_hash` (SHA-256). The old table is kept, deprecated and unused, so keys issued before P3-04 must be reissued.

**[W1 platform lane: P3-01]**

- **[P3-01]** SQLite files `${UCGLE_F1_STATE_DIR}/auth.db`, `scans.sqlite` and `agent.db` → Postgres tables in `supabase/migrations/20261031160000_*`. SQLite data is not migrated (dev-only state).
- **[P3-01]** `ConversationStore(db_path=…)` and `SQLModel.metadata.create_all` → the shared engine; the schema comes from migrations.

**[W1 platform lane: P3-01 part 2, P3-02, P3-03]**

- **[P3-01]** `~/.cache/qcompass/calibration.sqlite` and `QCOMPASS_CALIBRATION_DB` → `public.router_calibration_daily` / `public.router_calibration_devices`.
- **[P3-01]** `~/.qcompass/bench/leaderboard.sqlite` and `QCOMPASS_BENCH_DB` → `public.bench_runs`.
- **[P3-01]** `CalibrationCache(db_path=…)` / `LeaderboardStore(db_path=…)` → `(engine=…)`.
- **[P3-01]** Dependency `sqlite-utils` (declared, never imported) → `sqlalchemy` + `psycopg[binary]`.
- **[P3-02]** `RunRegistry._drive` (in-process pipeline with pre-emitted progress) and its in-memory `_runs`/listeners → `ucgle_f1.jobs.JobQueue` + `ucgle_f1.worker` (`ucgle_f1.run` handler) + `job_events` streaming. `RunRegistry`'s public methods (`submit/get/result/cancel/stream/ping`) are kept.
- **[P3-02]** Synchronous `prepare/run` inside `submit_run` → `qcompass.run` handler in the worker; response 200/202 with the computed status → always 202 `queued`.
- **[P3-03]** Sidecar-file reads in `list_runs`/`get_run`/`stream_run` → `public.runs`, `public.run_results`, `public.run_provenance`, `public.job_events`. The sidecar is still written at submit.
- **[P3-02]** `runs._validation_benchmarks_for` → `validation_benchmarks_for` (old name kept as an alias).

**[W1 platform lane: P4-02, P3-07]**

- **[P4-02]** `src/services/qcompass/http.ts` (own `fetch` wrapper) → `src/lib/sdk.ts` (`api`, `apiStream`, `usesApi`, `authHeaders`) over `@qcompass/frontend-sdk`.
- **[P4-02]** `src/lib/apiClient.ts` `fetch`/SSE implementation → the SDK client (`apiFetch`/`apiSse` keep their signatures); `errorFromResponse` moved to `src/lib/apiErrors.ts` and is re-exported from `apiClient`.
- **[P4-02]** SDK hand-aligned mirror types (`types.ts`) and the `datamodel-codegen` script (never run; it targeted Python models, not the API) → aliases of generated OpenAPI schemas; `ProvenanceSidecar`-returning `getRun` → `DomainRunResult` (what the API returns since P4-01).
- **[P4-02]** `ParticleObservablesTable` `literatureUrl` prop (direct `/fixtures/` fetch) → `getLatticeQCDReferences()`; `particle-suite.tsx` direct `loadFixture` → `services/qcompass/bench.ts::getParticleSuite` (fixture mode unchanged; API mode reports that the leaderboard arrives with P2-14).
- **[P3-07]** Dockerfile `pip install -e` of each member (unpinned transitive deps, root user, compilers in the runtime image) → `uv sync --frozen` in a build stage, slim non-root runtime stage. `ENV` `UCGLE_F1_STATE_DIR`/`UCGLE_F1_ARTIFACTS`/`QCOMPASS_PRICING_CACHE` kept. Port 8787 → `$PORT` (default 8080, Cloud Run's).
- **[P3-07]** CUDA base `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04` with apt `python3.12` (not in Ubuntu 22.04's archive, so that build could not succeed) and unpinned `jax[cuda12]>=0.4.30` → CUDA 12.6.3/Ubuntu 24.04 by digest, uv-managed CPython, locked jax + matching CUDA plugin.

**[W1 Gate 1 security + code-review fixes]**

- **[SEC-H2]** `src/lib/jobs.ts` (`enqueueJob`, a direct `jobs` insert from the browser, never imported) → enqueue through the API: `POST /api/qcompass/domains/{id}/runs` via `src/lib/sdk.ts`.
- **[SEC-H2]** RLS policy "tenant members enqueue jobs" → "service role enqueues jobs" (down migration restores main's).
- **[SEC-H1]** Dev-tenant fallback in `runs._tenant_uuid` (any environment) → `principal.resolve_tenant_slug` (dev only).
- **[SEC-M2]** `bunx wrangler deploy` → `./node_modules/.bin/wrangler deploy` (the locked copy).
- **[SEC-L5]** API service env `SUPABASE_SERVICE_ROLE_KEY` → none (workers keep it).
- **[REV-SF2]** `complete_job(uuid, jsonb, text)` (no lease check) → `complete_job(uuid, text, jsonb, text)`. The old signature remains and raises.
- **[REV-SF5]** API-mode `sdk.getUcgleRun`/`sdk.streamUcgleRun` in `services/simulator.ts` → `sdk.getRun`/`sdk.streamRun` on `cosmology.ucglef1`. The SDK functions remain for agent clients.
- **[REV-nit]** `Dockerfile.cuda12` `uv pip install jax-cuda12-plugin…` → `uv sync --frozen … --extra cuda12`; the `JAX_VERSION` build arg is removed.

**[W1 physics lane part 2: P1-03, D13a]**

- The `known-gap` CI job ("known gap: GB→0 decoupling (P1-03, not required)"). Replaced by the `backend (slow audits)` job, which now runs `test_gb_to_zero_decoupling` as a required test (no `--deselect`).
- `tau_span_end` in `pipeline.py`. Replaced by `couplings.M3_TAU_END`, with the same values.

**[W1-PARAMS]** (from `docs/build/lanes/W1-platform.md`, section "W1 potential-parameter boundary (Gate 1)")

- **[W1-PARAMS]** `CosmologyPotential`'s own copy of `kind`/`params`/`customPython` (a separate `BaseModel`) → a subclass of `domain.Potential` that adds completeness (R20). The now-unused `cosmology_manifest.PotentialKind` → `domain.PotentialKind`.
- **[W1-PARAMS]** `configDefaults.ts`'s literal `switch` and V2 object → `configDefaults.json`, which it imports.
- **[W1-PARAMS]** `potentialEvaluator.ts` hilltop `const V0 = 1e-7` → `p.V0 ?? 1e-7`.
- **[W1-PARAMS]** `couplings.py` docstring "The potential's parameters (`Potential.params`) are already in M_Pl units" → they arrive in API units and are converted once by `Potential.engine()`.

**[Gate 1 round 2, lane DB]** (from `docs/build/lanes/W1-sec-db.md`)

- **[R2-TOKEN-TTL]** Wildcard approval scope `*` (session-wide, never consumed) → named one-shot scopes only; nothing issued `*`.
- **[R2-TOKEN-TTL]** `IssueReq.ttl_seconds: int | None` (null produced a token that had already expired; any size accepted) → `int` in (0, 3600], default 3600.
- **[R2-RUN-ID]** Client-chosen `runs.id` on `POST /api/qcompass/domains/{d}/runs` → server-generated id plus `runs.client_run_id` (per-tenant alias, accepted by every run route).
- **[R2-RUN-ID]** The generic 409 for a runId held by another tenant (SEC-L2's round-1 fix) → no conflict across tenants; 409 only when the caller's own tenant reuses an alias.
- **[R2-QUOTA]** Quota over all `runs` rows of the tenant → over API-created rows only (`author_user_id is null`).
- **[R2-PLAN-PATH]** Absolute `agent_plans.path` → path relative to the artifacts root, under the tenant's sandbox.
- **[R2-M1-USING]** Policies replaced by `20261102100200` (its down migration restores them): runs "authenticated users create runs", "authors update own runs" (both from `20261031200200`), "authors delete own runs"; "authors write results" (`20261031200200`); "authors write audits"; "authors write timelines"; storage "authors write/update/delete viz-timelines", "authors write/delete run-artifacts" (main's `20260424153958`).

**[Gate 1 round 2, lane WORKER]** (from `docs/build/lanes/W1-sec-worker.md`)

- **[c3-gil-timeout]** The handler thread (`threading.Thread` + `join(timeout)`) → a child process per job (`_run_child`, `_wait_child`, `_stop_child`). `JobContext(job, queue, lost, worker_id)` → `JobContext(job, queue)`, where `queue` is the child-side `_GuardedQueue`.
- **[c3-guarded-queue]** `_GuardedQueue.__getattr__` pass-through → explicit methods: `set_run_status`, `save_result`, `record_provenance`, `emit`, `job_status`. Nothing else of `JobQueue` is reachable.
- **[c3-provenance-upload]** The handler's `ArtifactStore().put` + `ctx.queue.save_provenance` → `ctx.queue.record_provenance(run_id, record)`. The worker process does the lease check, the upload and the row.
- **[c3-attempt-lease]** SQL `heartbeat_job(job, worker, lease)` and `complete_job(job, worker, result, error)` → refuse. They are replaced by the attempt forms `heartbeat_job(job, worker, attempt, lease)` and `complete_job(job, worker, attempt, result, error)`, and the down migration restores them.
- **[c3-expr-caps]** `sympy.sympify(source)` → `_check_shape` + `_Checker` + `_build`, evaluated from the checked `ast`. `_check_custom_size` and `_constant_digits` → `_Checker`.
- **[c3-stream-bounds]** `apiStream(sdk.streamRun(…))` in `services/qcompass/runs.ts` and `services/simulator.ts` → `runEventStream` (`src/lib/sdk.ts`).
