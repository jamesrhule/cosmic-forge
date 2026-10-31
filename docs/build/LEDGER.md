# Build ledger

## Decisions

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
