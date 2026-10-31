# Build ledger

## Decisions

- **[P0-01] Interim second CI file.** Main's `ci.yml` kept; the agent branch's `ci.yml` kept verbatim as `.github/workflows/ci-python.yml` until P0-05 merges them into one CI.
- **[P0-01] Chemistry Result.** The agent branch's run-detail content now lives in `src/components/results/chemistry/ChemistryResult.tsx`, dispatched by `DomainResult` for `chemistry.molecular`. It maps main's payload (`classical_reference_hartree`, `energy_hartree`) — or the qfull fields (`classical_energy`, `quantum_energy`, `classical_method`) when present — onto the energy-comparison card.
- **[P0-01] Main's 6A router tests preserved** verbatim in `packages/qcompass-router/tests/lineage_6a/` (with main's conftest) for P0-02.
- **[Baseline] Screenshot method.** Production SSR does not serve locally (see BASELINE.md); cosmology screenshots are taken from `vite dev`, Chromium 1440×900, animations off, after the auth button settles, with a main-vs-main determinism control.


## Substitutions

## Conflicts

- **[Part 3 vs repo]** Part 3 describes main as lacking the backend; main actually carries the original UCGLE-F1 backend (pre-branch) and an independent 6A `qcompass-router` (`eec2488`) that depends on a `qcompass-core` absent from main. Resolution per P0-01: backend and packages come from the agent branch.
- **[Part 2 baseline vs measurement]** Orientation numbers differ (see BASELINE.md); measured values recorded, not the orientation values.
- **[Older plan files]** `/root/.claude/plans/the-schematic-a-b-coupling-cozy-hedgehog.md` (production-readiness roadmap) and the v2 prompt set are superseded by PLAN.md.


## Corrected tests

## Removals with replacement

- **[P0-01]** `src/routes/domains/chemistry/{route,configurator,runs,runs.$id,research}.tsx` → main's generic `src/routes/domains/$domain/*` + `src/components/results/chemistry/ChemistryResult.tsx`.
- **[P0-01]** `src/components/qcompass/domain-switcher.tsx` → `src/components/domain-selector.tsx`.
- **[P0-01]** `src/components/qcompass/json-schema-form.tsx` → `src/components/configurator/QcompassManifestForm.tsx` (rjsf).
- **[P0-01]** `src/components/qcompass/provenance-panel.tsx` → `src/components/ProvenancePanel.tsx`.
- **[P0-01]** `src/services/qcompass/chemistry.ts` → `src/services/qcompass/runs.ts` (generic over `DomainId`).
- **[P0-01]** Branch versions of 50 conflicted paths → see MERGE-MAP.md (fixtures: main's file of the same run id; router: agent lineage + `tests/lineage_6a/`).

