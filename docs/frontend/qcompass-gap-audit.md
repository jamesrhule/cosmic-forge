# QCompass Frontend Gap Audit

This document audits the multi-domain frontend scaffolding pass against the
contract in the Lovable prompt. It is co-authored by the frontend agent and
the backend team — every "Missing entirely" row is a handoff item.

Pass type: **AUDIT + SCAFFOLDING** (per user option-2 decision).
Per-domain rich Result/Visualizer panels are deferred to a depth pass,
EXCEPT carve-outs 1 (HEP/Nuclear ParticleObservablesTable) and
2 (gravity provenance-warning blocking guard), which ship fully built here.

## 1. Present-and-correct (do not touch)

| Surface | File | Notes |
|---|---|---|
| Cosmology configurator | `src/routes/index.tsx` | UCGLE-F1 home; immutable. |
| Cosmology visualizer | `src/routes/visualizer.tsx`, `visualizer.$runId.tsx`, `visualizer.index.tsx` | Six-panel layout untouched. |
| Cosmology domain plugin | `src/lib/domains/cosmology.ucglef1.ts` | Reference adapter; mirrored by new plugins. |
| Domain types | `src/lib/domains/types.ts` | Extended additively (see §3). |
| Cosmology services | `src/services/{simulator,assistant,artifacts,visualizer}.ts` | Untouched; new services live under `services/qcompass/`. |
| Visualizer panels | `src/components/visualizer/panel-*.tsx` | Cosmology-specific; mirrored under `panels/<domain>/`. |
| Existing UI primitives | `src/components/{equation-block,verdict-chip,validity-light,sci,arxiv-link,uncertainty-bar,parameter-heatmap,sgwb-plot,potential-editor,sci-input,status-chip,theme-toggle,cost-badge,model-badge}.tsx` | Reused across new surfaces. |
| Chat drawer | `src/components/chat/*` | Untouched; LLM/RAG out of scope. |
| Model manager | (inside chat drawer header) | Untouched. |
| Cosmology fixtures | `public/fixtures/{benchmarks,models,runs,scans,formulas,events,chat,artifacts}/*` | Untouched. |
| Existing Playwright suite | `e2e/smoke.spec.ts` | Continues to gate cosmology regression. |

## 2. Present-but-incomplete (additive edits this pass)

| File | Edit | Why safe for cosmology |
|---|---|---|
| `src/config/features.ts` | +10 flags (`qcompassMultiDomain`, 7 per-domain, `qcompassAuth`, `qcompassObservability`); existing flags untouched. | Defaults are `false`. Cosmology code path never reads new flags. |
| `src/lib/domains/types.ts` | Extended `DomainPlugin` with optional `manifestSchemaUrl`, `fixturePathPrefix`, `resultRendererId`, `visualizerPanelGroupId`, `requiresProvenanceWarning`. Added `DomainRunResult`, `RunSummary`, `VisualizationTimeline`, `RunEvent`, `ProvenanceRecordExt`. | All new fields optional; cosmology plugin compiles unchanged. |
| `src/lib/domains/registry.ts` | Removed the seven `PHASE2_PLACEHOLDERS`; new domains self-register via side-effect imports from `register-all.ts`. Surface listing now reads enabled flag from `FEATURES`. | When `qcompassMultiDomain` is false, `listDomainSurface()` returns only cosmology, matching today's selector. |
| `src/components/domain-selector.tsx` | Imports `register-all.ts`. Disabled rows now show "Enable in feature flags" tooltip when flag-off. | Selector itself is already gated on `domainsRegistry`; new domains hidden when master flag is off. |
| `src/routes/__root.tsx` | Adds optional `<QCompassAuthStrip />` rendered only when `FEATURES.qcompassAuth === true`. | Default false → not rendered → DOM identical. |

## 3. Missing entirely — built in this pass

| Item | Files |
|---|---|
| Audit document | `docs/frontend/qcompass-gap-audit.md` (this file) |
| Feature flags | `src/config/features.ts` (extended) |
| Domain plugins (7) | `src/lib/domains/{chemistry,condmat,amo,hep,nuclear,gravity,statmech}.ts` + `src/lib/domains/register-all.ts` |
| Generic domain shell | `src/components/domain-shell.tsx` |
| Routes (42 = 7 × 6) | `src/routes/domains/$domain/{configurator,runs,runs.$id,research,visualizer,visualizer.$id}.tsx` |
| Verdict admin route | `src/routes/admin.verdict.tsx` |
| QCompass services (8) | `src/services/qcompass/{manifestSchema,runs,visualizer,scans,literature,verdict,auth,http}.ts` |
| Shared components | `src/components/ProvenancePanel.tsx`, `ProvenanceWarningBanner.tsx`, `ModelDomainBadge.tsx`, `qcompass-coming-online-card.tsx`, `qcompass-auth-strip.tsx`, `metrics-tile.tsx`, `trace-link-chip.tsx`, `LiteratureCompareSheet.tsx`, `verdict-table.tsx` |
| Carve-out 1 — HEP/Nuclear tables | `src/components/results/hep/ParticleObservablesTable.tsx`, `src/components/results/nuclear/NuclearObservablesTable.tsx` |
| Carve-out 2 — gravity guard | `src/components/results/gravity/Result.tsx` (REFUSES render when `is_learned_hamiltonian === true && !provenance_warning`) |
| Per-domain Result wrappers | `src/components/results/<domain>/Result.tsx` ×7 |
| Per-domain Visualizer panel groups | `src/components/visualizer/panels/<domain>/CommingOnlinePanel.tsx` ×7 |
| Particle Suite Research view | `src/components/research/particle-suite.tsx` (used by HEP + nuclear) |
| Auth UI scaffolding | `src/store/auth.ts`, `src/components/auth/TokenInput.tsx`, `src/components/auth/TenantPicker.tsx` |
| Manifest forms | `src/components/configurator/QcompassManifestForm.tsx` (rjsf wrapper) |
| Fixtures (~35 files) | `public/fixtures/{chemistry,condmat,amo,hep,nuclear,gravity,statmech,literature,benchmarks,verdict,auth}/*` |
| Playwright tests (6) | `e2e/{cosmology-regression,hep-particle-observables,nuclear-observables,gravity-provenance-guard,verdict-admin-gate,domain-shell-coming-online}.spec.ts` |

## 4. Touched-shared-files registry

Each edit below is gated by a feature flag whose default is `false`, OR is
purely additive (new optional types/fields). Cosmology rendering is
byte-identical with all defaults.

| File | Change | Gate | Cosmology impact |
|---|---|---|---|
| `src/config/features.ts` | +10 flags | n/a (additive, defaults false) | none |
| `src/lib/domains/types.ts` | +optional fields, +new exported types | n/a (optional/additive) | none |
| `src/lib/domains/registry.ts` | Replaced placeholder list with flag-driven surface | `qcompassMultiDomain` (off → returns only cosmology) | none |
| `src/components/domain-selector.tsx` | Imports `register-all.ts` (which imports each plugin's side-effect register) | `domainsRegistry` already gates render; `qcompassMultiDomain` gates non-cosmology rows | none when master flag off |
| `src/routes/__root.tsx` | Mounts `<QCompassAuthStrip />` | `qcompassAuth` (default false → not rendered) | none |

## 5. Deferred dependencies

These were intentionally **not installed** this pass. They land with the
depth pass that needs them:

| Package | Why deferred | Depth-pass target |
|---|---|---|
| `3dmol@^2.4` | Only used by chemistry `OrbitalOccupation3D`. Heavy bundle (≈ 1MB) and Worker-runtime risk (touches DOM at import time). | Chemistry depth pass — wrap in `ClientOnly` + dynamic import. |
| `zarrita@^0.5` | Only needed when visualizer reads live Zarr v3 stores; current fixtures are JSON. | First live-Zarr visualizer pass. |

## 6. Deferred work (not in this pass)

- Rich result panels for chemistry/condmat/amo/statmech (replace
  "coming online" cards).
- 3D visualizers (R3F panels under `panels/<domain>/`).
- Real auth implementation behind `qcompassAuth`.
- Real metrics / trace deep links behind `qcompassObservability`.
- Mobile-first layouts.

## 7. Backend handoff contract

Every new service function under `src/services/qcompass/` carries a JSDoc
`@endpoint` annotation identifying the URL the backend team owns. See the
"Multi-domain handoff" section of `README.md` for the consolidated list.
