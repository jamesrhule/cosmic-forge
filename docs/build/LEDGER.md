# Build ledger

## Decisions

- **[P0-04]** `uv.lock` resolution: `amazon-braket-sdk>=1.115` pins `antlr4-python3-runtime==4.13.2`, while `omegaconf` (used by `ucgle_f1.m7_infer.hydra_cfg`) pins `4.9.*`. Declared `[tool.uv] conflicts` between package `ucgle-f1` and `qcompass-router[braket]`, so the lock has two forks. These can't share an environment, and CI installs without `braket`. This uses uv's experimental package-conflict feature.
- **[P0-04]** Root `[tool.uv.sources]` declares every member `{ workspace = true }`; `[tool.uv] dev-dependencies` moved to `[dependency-groups].dev`.

- **[P0-01] Interim second CI file.** Main's `ci.yml` kept; the agent branch's `ci.yml` kept verbatim as `.github/workflows/ci-python.yml` until P0-05 merges them into one CI.
- **[P0-01] Chemistry Result.** The agent branch's run-detail content now lives in `src/components/results/chemistry/ChemistryResult.tsx`, dispatched by `DomainResult` for `chemistry.molecular`. It maps main's payload (`classical_reference_hartree`, `energy_hartree`) — or the qfull fields (`classical_energy`, `quantum_energy`, `classical_method`) when present — onto the energy-comparison card.
- **[P0-01] Main's 6A router tests preserved** verbatim in `packages/qcompass-router/tests/lineage_6a/` (with main's conftest) for P0-02.
- **[Baseline] Screenshot method.** Production SSR does not serve locally (see BASELINE.md); cosmology screenshots are taken from `vite dev`, Chromium 1440×900, animations off, after the auth button settles, with a main-vs-main determinism control.


## Substitutions

- **[P0-04]** `packages/qcompass/pyproject.toml` extra `tn`: `tensornetwork>=0.5` → `tensornetwork>=0.4.6`. 0.5 was never published (PyPI tops out at 0.4.6), so the lock could not resolve; no code imports tensornetwork.
- **[P0-04]** Starlette ≥1.10 deprecates its httpx test-client path ("install httpx2"); fixed by adding `httpx2>=2.16` (BSD-3-Clause, pydantic org) to the dev group/extra, not by a warning filter.
- **[P0-05]** Licence gate allowlist (`scripts/licence_allowlist.toml`): `posthog-js` (LICENSE file Apache-2.0; package.json says "SEE LICENSE IN LICENSE") and `webgl-constants` (LICENSE file MIT; no package.json licence field). Both read by hand.

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

## Removals with replacement

- **[P0-04]** `backend/pyproject.toml` extras: `PyTransport>=3.0` (from `multifield`) and `GWBird` (from `gw`). Neither is on any package index, so the workspace lock cannot resolve them. Replacement: manual install steps in `docs/qcompass/optional-backends.md`. The extras keep their names, and the code still imports them lazily.

- **[P0-01]** `src/routes/domains/chemistry/{route,configurator,runs,runs.$id,research}.tsx` → main's generic `src/routes/domains/$domain/*` + `src/components/results/chemistry/ChemistryResult.tsx`.
- **[P0-01]** `src/components/qcompass/domain-switcher.tsx` → `src/components/domain-selector.tsx`.
- **[P0-01]** `src/components/qcompass/json-schema-form.tsx` → `src/components/configurator/QcompassManifestForm.tsx` (rjsf).
- **[P0-01]** `src/components/qcompass/provenance-panel.tsx` → `src/components/ProvenancePanel.tsx`.
- **[P0-01]** `src/services/qcompass/chemistry.ts` → `src/services/qcompass/runs.ts` (generic over `DomainId`).
- **[P0-01]** Branch versions of 50 conflicted paths → see MERGE-MAP.md (fixtures: main's file of the same run id; router: agent lineage + `tests/lineage_6a/`).

