# Build ledger

## Decisions

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

## Conflicts

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
