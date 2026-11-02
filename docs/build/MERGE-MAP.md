# P0-01 merge map — `claude/ucgle-f1-agent-simulator-agRxR` → `build/w0-consolidate` (from `origin/main`)

Merge base: `876bb48`. Main: 377 commits after base. Agent branch: 31 commits after base.
`git merge --no-ff origin/claude/ucgle-f1-agent-simulator-agRxR` reported **50 conflicted paths**.

Rules applied (PLAN.md, P0-01): main's generic `src/routes/domains/$domain/*`, rjsf forms, eight-plugin
registry and `register-all.ts` win; the branch's chemistry pages / energy-comparison card / provenance
cards move into main's chemistry Result component; `src/config/features.ts` = union of flags;
`public/fixtures/**` keeps main's files and adds branch-only files; backend, packages, docs, workflows,
`acceptance/` come from the branch.

## Conflicted paths (50)

| # | Path | Resolution |
|---|---|---|
| 1 | `.github/workflows/ci.yml` | Main's version kept as `ci.yml`; branch's version kept verbatim as `.github/workflows/ci-python.yml`. P0-05 merges them into one CI. |
| 2–25 | `packages/qcompass-router/{README.md, pyproject.toml, src/qcompass_router/{__init__,budget,decision,pricing_stub,router}.py, providers/{__init__,azure,base,braket,ibm,ionq,iqm,local_aer,local_lightning,pasqal,quera}.py, tests/{conftest,test_provider_soft_import,test_router_local_aer,test_router_paid_cheapest,test_router_preferred_filter,test_router_real_hw_no_budget}.py}` (24 paths) | Branch (agent lineage) wins — "packages come from the branch". Main carried an independent 6A router (`eec2488`). Main's six conflicting 6A test files are preserved verbatim under `packages/qcompass-router/tests/lineage_6a/` (with main's conftest) so P0-02 can make the unified router pass both lineages. Main-only router files merged in untouched: `fixtures/pricing_seed.yaml` (top-level), `tests/__init__.py`, `tests/test_pricing_stub.py`. |
| 26–29 | `public/fixtures/chemistry/instances/{h2,lih,n2}.yaml`, `public/fixtures/chemistry/manifest-schema.json` | Main wins. |
| 30–33 | `public/fixtures/chemistry/runs/{femoco-toy,h2-sto3g,lih-631g,n2-ccpvdz}.json` | Main wins (main's `DomainRunResult` shape). Branch shape (manifest/energies envelope) replaced by main's run of the same id. |
| 34 | `public/fixtures/literature/lattice-qcd-references.json` | Main wins. |
| 35–36 | `public/fixtures/verdict/sample-verdict.{md,yaml}` | Main wins (P4-01 fixes the verdict endpoint shape to main's YAML). |
| 37–43 | `public/fixtures/visualizations/{f2-nieh-yan-demo,f3-large-N-demo,f5-resonance-demo,f7-stacked-demo,gb-off-control,kawai-kim-natural,starobinsky-standard}.json` | Main wins (cosmology visualizer byte-identity, R19). Branch-only visualization fixtures (per-domain timelines) are added. |
| 44 | `src/config/features.ts` | Main's version; it already contains every branch flag (`liveBackend`, `liveAssistantToolDispatch`, `liveModelManagement`, `qcompassMultiDomain`) as env-driven flags, so main's file *is* the union. |
| 45–48 | `src/lib/domains/{chemistry,cosmology.ucglef1,registry,types}.ts` | Main wins (eight-plugin registry). |
| 49 | `src/routes/index.tsx` | Main wins (cosmology workbench, R19). The branch only added a `DomainSwitcher` chip; main's header already has `DomainSelector`. |
| 50 | `src/services/qcompass/manifestSchema.ts` (add/add) | Main wins — generic over `DomainId`, superset of the branch's chemistry-only loader. |

Total: 50 paths.

## Semantic resolutions of auto-merged branch files

| Path (branch) | Resolution | Replacement |
|---|---|---|
| `src/routes/domains/chemistry/{route,configurator,runs,runs.$id,research}.tsx` | Removed | Main's generic `src/routes/domains/$domain/*` routes. The run-detail content (energy comparison + provenance + payload) moved into `src/components/results/chemistry/ChemistryResult.tsx`, dispatched by `DomainResult` for `chemistry.molecular`. |
| `src/components/qcompass/domain-switcher.tsx` | Removed | `src/components/domain-selector.tsx` (main). |
| `src/components/qcompass/json-schema-form.tsx` | Removed | `src/components/configurator/QcompassManifestForm.tsx` (main, rjsf). |
| `src/components/qcompass/provenance-panel.tsx` | Removed | `src/components/ProvenancePanel.tsx` (main) — renders the same hash/calibration/mitigation fields plus resource estimate and transforms. |
| `src/services/qcompass/chemistry.ts` | Removed | `src/services/qcompass/runs.ts` (main, generic over `DomainId`). |
| `src/components/qcompass/energy-comparison-card.tsx` | Kept | Used by `ChemistryResult`. |
| `src/services/qcompass/manifest.ts`, `src/types/qcompass.ts` | Kept | Re-export shim / types used by the energy card. |
| `src/components/visualizer/panels/**` (19 panels + `index.ts`, `types.ts`) | Kept | Wired into domain visualizers in P4-03. |
| `e2e/playwright.config.ts`, `e2e/{cosmology-byte-identity,chemistry-h2-flow}.spec.ts` | Kept | P0-06 consolidates to one `playwright.config.ts`. |
| `tsconfig.json` | Auto-merged | Adds the `@qcompass/frontend-sdk` path alias from the branch. |
| `src/routeTree.gen.ts` | Regenerated | By the TanStack router plugin on build after the chemistry routes were removed. |
