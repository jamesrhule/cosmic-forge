# P0-02 — router lane (qcompass-router unification)

Branch `build/w0-p002-router` from `4b68d9b`. Scope: `packages/qcompass-router/**` only.
One router (agent lineage) now carries the 6A (main) and 6B (router branch
`claude/provider-adapters-routing-33xCz`) behaviour.

## Final run

```
.venv-lane/bin/python -m pytest packages/qcompass-router -q -p no:cacheprovider \
  --import-mode=importlib -o asyncio_default_fixture_loop_scope=function
118 passed, 1 warning in 0.69s        # exit code 0
```

Before this lane: collection error in `tests/audit` (`FreeTierLedger` missing); at P0-01, 9 `lineage_6a`
+ 2 `test_pricing_stub.py` failures. Also passes from `packages/qcompass-router` with no `-o` override
(the option is now in `pyproject.toml`). The 1 warning is `qcompass_core/manifest.py:102`
`datetime.utcnow()` (`ProvenanceRecord.recorded_at` default) — outside this lane, handed to P0-04.

Versions: Python 3.12.3, pytest 9.2.0, pytest-asyncio 1.4.1, pydantic 2.14.2, PyYAML 6.0.3,
httpx 0.28.1, certifi 2026.10.23, qcompass-core 0.1.0 (editable), qcompass-router 0.1.0 (editable).

## Disposition of every router-branch test

| Test | Disposition |
|---|---|
| `tests/lineage_6a/*` (11 tests, main's 6A) | unmodified, pass |
| `tests/test_pricing_stub.py` (5) | unmodified, pass |
| `audit/test_a_router_1.py::test_zero_budget_never_routes_to_cloud` | kept unmodified (zero-cost cloud fakes listed first — not covered elsewhere), pass |
| `audit/test_a_router_2.py` (4: pinned verify, offline-safe, factory unavailable, pinned transport) | kept unmodified; capability ported (`PricingEngine` `ca_bundle`/`client_factory`/`_verify_target`, `_LiveFetchError`), pass |
| `audit/test_a_router_3.py::test_drift_score_assertion` | corrected (see below), pass |
| `audit/test_a_router_3.py::test_router_refuses_on_drift` | kept unmodified, pass |
| `audit/test_a_router_4.py` (2) | **removed** — see Removals |
| `audit/test_a_router_5.py` (2: free tier wins / exhausted fallback) | kept unmodified; `FreeTierLedger`/`_FreeTierBucket` ported, pass |
| `audit/test_a_router_6.py::test_transform_records_carry_into_decision` | **removed** — see Removals |
| `audit/test_a_router_6.py::test_round_trip_into_provenance_record` | corrected (see below), pass |
| `audit/conftest.py` | unmodified |

`from tests.conftest import FakeAdapter` resolves via `tests/conftest.py`, which loads
`tests/lineage_6a/conftest.py` by path and re-exports `FakeAdapter`, `SMALL_QASM`, `LARGE_QASM` (one
definition; `lineage_6a` untouched).

## Decisions

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

## Substitutions

- S1 6B `Cost` pydantic model (`usd`, `pricing_basis`, `cache_age_s`, `live`) → agent `Cost` dataclass
  with `cache_age_s` field and `usd`/`live`/`pricing_basis` properties.
- S2 6B `PricingEngine(seed_yaml=...)` → no per-engine seed path; the package seed is the only seed.
  Constructor is `PricingEngine(cache_dir=None, ttl_seconds=86400, *, ca_bundle, endpoints, ttl_s,
  client_factory, ledger)`.
- S3 6B live cache `{..., "_cached_at"}` → agent cache `{"recorded_at_epoch", "origin": "seed"|"live",
  "entries"}`; live payload scalars overlay the provider's seed entries.
- S4 6B `RoutingDecision.calibration` → same name, optional `dict | None` on the agent model.
- S5 6B free-tier label for seed-flagged backends no ledger tier lists → `<provider>_free_tier`.

## Seed reconciliation (one source of truth)

`packages/qcompass-router/fixtures/pricing_seed.yaml` (router branch) deleted; its `free_tiers` and
`device_typical_depth_max` blocks merged into `src/qcompass_router/fixtures/pricing_seed.yaml`. Prices
already present in the package seed win (only difference: `braket_rigetti_ankaa` keeps `per_task_usd:
0.30`; the router-branch seed had none). Free-tier backend lists add the package's names (`ibm_eagle`,
`iqm_garnet`, `iqm_deneb`) next to the router-branch ones; every free-flagged seed entry is listed by a
tier (tested). The three router-branch CSVs (`ibm_torino`, `ionq_forte`, `iqm_garnet`) moved unchanged to
`src/qcompass_router/fixtures/calibration_seed/` (they now ship in the wheel); `load_calibration_seed`
reads `.yaml` or `.csv` (`name.csv` selects CSV; bare name prefers YAML — `ionq_forte` has both).

## Corrected tests (old → new)

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

## Removals (with replacement)

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

## New tests (`tests/test_p002_unification.py`, 25 incl. parametrised)

Single seed + tiers/depth caps; lookup fallbacks + no cross-provider borrowing; Azure price shapes; 6A
aliases; `BackendInfo` priors + `JobHandle` default; 6A adapter backends; budget=0 real hardware on a
covering tier / refused when exhausted; free tier beats a cheaper paid backend and falls back when
exhausted; auto transforms above/at the depth cap; explicit override + disable; transform depth/runtime;
stale downgrade; all-stale keeps cost order; drift gate on chosen backend only; three CSV seeds + YAML
precedence + missing seed; `pull_qdmi` without QDMI; live refresh overrides seed (stub client); non-2xx
writes nothing; no live fetch without opt-in; router reports live pricing; `pinned_context`.
