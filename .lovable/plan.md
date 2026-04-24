## Heads-up: scope vs. what's actually in the repo

The prompt assumes several pieces already exist that don't:

| Mentioned | Actually in the repo today |
|---|---|
| Control view, Research view, Runs view | Only `/` (Configurator) and `/qa` exist |
| AI assistant drawer / chat UI | `useChat` Zustand store exists (`src/store/ui.ts`), but no drawer component |
| cmd-k palette | `useCommandPalette` store exists, no UI |
| Top-nav tabs Configurator/Control/Research | Static labels in the header — only the active label is styled, no routes |
| Equation gallery for F1–F7 | `public/fixtures/formulas/F1-F7.json` exists; no UI consumes it |
| `RunResult.config.formula_variant` | Not a current field |

I'll deliver everything that's purely additive and clearly scoped, and leave the missing host UI hooks as documented integration seams. **No existing types or services are modified.** Specifically:

- **Build the Visualizer** (routes, panels, store, services, fixtures, README) — all six panels, A/B overlay, split-screen, transport bar, keyboard shortcuts, reduced-motion path, WebGL→2D fallback.
- **Add a "Visualizer" link to the existing top-nav** in `src/routes/index.tsx` (real `<Link>`, not just a label) so the feature is reachable.
- **Assistant integration**: extend `AssistantContextChip` union additively in `src/store/ui.ts` with the two new chip kinds and add a `useAssistantAttach` helper. The right-click context menu in the visualizer dispatches into this. (Allowed: `src/store/ui.ts` is shell scaffolding, not a domain type.)
- **cmd-k entries / Runs-row "Open in visualizer" / "Launch visualizer" button**: these UIs don't exist yet — out of scope, called out in README under "Future host hooks". The store-level `useCommandPalette` already has the slot.
- **Formula `termIds`**: `public/fixtures/formulas/F1-F7.json` will get a new optional `termIds: string[]` per F-formula (allowed additive extension).

If you'd rather I also build a minimal Control view + run list + cmd-k surface to host the "Open in visualizer" actions, say the word and I'll fold that into a follow-up.

## Architecture

```text
src/
  types/visualizer.ts                 NEW — VisualizationFrame, VisualizationTimeline,
                                            VisualizationHints, FormulaVariant,
                                            ComparisonMode, RenderOptions
  services/visualizer.ts              NEW — getVisualization, renderVisualization,
                                            streamVisualization (all fixture-backed,
                                            JSDoc-annotated with backend endpoints)
  store/visualizer.ts                 NEW — useVisualizerStore (transport, comparison)
  store/ui.ts                         EDIT — extend AssistantContextChip union with
                                            'visualizer_frame' and 'visualizer_comparison'
  lib/exportFrame.ts                  NEW — tiny SVG/Canvas → PNG snapshotter (no deps)
  lib/visualizerColors.ts             NEW — colorForChirality, colorForKkLevel, etc.
  hooks/useAnimationFrame.ts          NEW — rAF loop bound to a `running` flag
  hooks/useFrameAt.ts                 NEW — pick a frame by index/τ
  hooks/usePrefersReducedMotion.ts    NEW — matchMedia wrapper
  components/visualizer/
    PhaseSpaceCanvas.tsx              R3F InstancedMesh particle field + 2D fallback
    PhaseSpaceCanvas2D.tsx            Canvas2D fallback (Re h_+ vs log k)
    GBWindowTimeline.tsx              Recharts AreaChart + master scrubber
    SGWBSnapshotPlot.tsx              wraps existing <SGWBPlot> with 3 snapshots
    AnomalyIntegrandPlot.tsx          Recharts LineChart + cumulative + cutoff line
    LeptonFlowSankey.tsx              custom SVG Sankey, animated widths
    FormulaOverlay.tsx                KaTeX with \htmlId term highlighting
    TransportBar.tsx                  play/pause/seek/speed/loop/export/comparison
    KeymapOverlay.tsx                 "?" help dialog
    EmptyPanel.tsx                    typed error + retry, used by every panel
    PanelSkeleton.tsx                 shimmer placeholder
    VisualizerLayout.tsx              ResizablePanelGroup 3-row frame
    VisualizerCanvas.tsx              top-level workbench (composes all panels)
    ComparisonControls.tsx            mode dropdown + sync-by-phase toggle
    ContextMenu.tsx                   right-click → attach/ask/copy τ/export
  routes/
    visualizer.tsx                    NEW — empty state + run picker
    visualizer.$runId.tsx             NEW — workbench, lazy-loads VisualizerCanvas

public/fixtures/visualizations/
  kawai-kim-natural.json              F1 baseline, 200 frames × 500 modes
  starobinsky-standard.json           F1, different potential
  gb-off-control.json                 F1 with ξ=0 (flat windows, demonstrates decoupling)
  f2-nieh-yan-demo.json               F2 (torsion overlay tag)
  f3-large-N-demo.json                F3 (kk_level on modes)
  f5-resonance-demo.json              F5 (resonance peak inset)
  f7-stacked-demo.json                F7 multi-phase
  streams/kawai-kim-live.jsonl        for streamVisualization

public/fixtures/formulas/F1-F7.json   EDIT — add `termIds: string[]` per entry
README.md                             EDIT — Visualizer integration handoff section
```

## Type contract (new, additive)

```ts
// src/types/visualizer.ts
export type FormulaVariant = 'F1'|'F2'|'F3'|'F4'|'F5'|'F6'|'F7';
export type Phase = 'inflation'|'gb_window'|'reheating'|'radiation'|'sphaleron';
export type ComparisonMode = 'single'|'ab_overlay'|'split_screen';
export type ParticleColorMode = 'chirality'|'kk_level'|'condensate'|'resonance';
export type RenderResolution = 'low'|'medium'|'high';

export interface VisualizationModeSample { /* k, h_plus_re/im, h_minus_re/im,
                                              alpha_sq_minus_beta_sq,
                                              in_tachyonic_window, kk_level? */ }
export interface VisualizationFrame { /* tau, t_cosmic_seconds, phase, modes,
                                         B_plus, B_minus, xi_dot_H,
                                         sgwb_snapshot?, anomaly_integrand?,
                                         lepton_flow, active_terms */ }
export interface VisualizationHints { /* panelEmphasis, particleColorMode,
                                         extraOverlays, formulaTermIds */ }
export interface VisualizationTimeline { runId; formulaVariant; frames; meta; }
export interface RenderOptions { resolution: RenderResolution; framesCount?: number; }
```

The `formulaVariant` lives on the timeline (not on `RunResult`) — so `RunConfig` is untouched. The fixture name encodes its formula and the timeline echoes it.

## Performance plan (matches the budget)

- **Pre-bake on load**: `services/visualizer.ts` post-processes the fetched timeline into typed `Float32Array` buffers `positionsByFrame[frame] : Float32Array(modes*3)` and `colorsByFrame[frame] : Float32Array(modes*3)`. Stored on the timeline object behind a non-enumerable property (so React's structural sharing doesn't copy them).
- **InstancedMesh**: one `<instancedMesh args={[…, MAX_MODES]}>` whose matrix attribute is updated per frame from the pre-baked buffer in a `useFrame` callback. No per-particle React.
- **Frame-skipping at high speed**: `TransportBar` writes `effectiveStride` (1/2/4) into the store; `useAnimationFrame` advances `currentFrameIndex += stride`; Sankey + formula overlay always render every step (cheap).
- **Imperative 2D panels**: GBWindowTimeline / Anomaly use static Recharts axes/data; the playhead is a separately positioned `<line>` updated via `transform` in a ref subscriber — no React reconciliation per frame.
- **Lazy loading**: `routes/visualizer.$runId.tsx` does `const VisualizerCanvas = lazy(() => import('@/components/visualizer/VisualizerCanvas'))`. R3F + drei + the panels are pulled into a single chunk so `/` and `/qa` keep their current bundle size.
- **2D fallback**: `PhaseSpaceCanvas` probes WebGL via `document.createElement('canvas').getContext('webgl2') ?? webgl`. On failure, mounts `PhaseSpaceCanvas2D` and shows a shadcn `<Alert>`.
- **Memory ceiling**: timeline service rejects payloads > 200MB (measured by `JSON.stringify(timeline).length` post-fetch as a cheap upper bound) → `EmptyPanel` with a "download notebook" CTA.

## Routes & layout

- `/visualizer` — empty state. Calls `listRuns()` (existing) and renders a card per run with "Open in visualizer". URL search: `?mode=single|ab_overlay|split_screen` retained.
- `/visualizer/$runId` — workbench. Search params: `?frame=N&compare=runIdB&mode=…&speed=…&loop=1` (TanStack `validateSearch` with zod + `fallback`). Loader resolves `getVisualization(runId)` plus optionally a second timeline when `compare` is set, then renders `<Suspense fallback={<PanelSkeleton />}><VisualizerCanvas .../></Suspense>`.
- `errorComponent` and `notFoundComponent` on both per stack rules.

The 3-row resizable layout follows the spec exactly using existing `ResizablePanelGroup` from `@/components/ui/resizable`. Row 2 left = Panel 2 also acts as the global scrubber; pointer events on its plot area write `currentFrameIndex` into the store.

## Transport store (Zustand)

```ts
// src/store/visualizer.ts
useVisualizerStore: {
  currentFrameIndex; playing; speed; loop; effectiveStride;
  comparisonMode: 'single'|'ab_overlay'|'split_screen';
  syncByPhase: boolean;
  runIdA; runIdB?;
  // actions: play/pause/toggle/seek/seekToPhase/setSpeed/setLoop/
  //          setComparisonMode/setSyncByPhase/loadTimelines
}
```

Frame index ↔ URL is reconciled with a tiny effect: store change → `navigate({ search })` debounced 200ms; URL change → store hydrate on mount only (avoids feedback loop).

## Comparison modes

`useTimelinesForCompare(timelineA, timelineB?)` returns either `{a}`, `{a,b,aligned: 'tau'|'phase'}` based on `comparisonMode` + `syncByPhase`. Each panel reads it via `useFrameAt(timeline, currentFrameIndex)` and renders A/B accordingly:

- **ab_overlay**: panels render two series, A in `--color-accent-indigo`, B in `--color-amber-500`. Sankey shows side-by-side with a delta-η_B chip.
- **split_screen**: `VisualizerLayout` switches its top-level wrapper to a 2-column grid; each column gets its own composed workbench bound to A or B; transport store stays single (one playhead).
- **Sync to phase**: when on, `seek(frameIdx)` in the master timeline computes `phase` then maps to the equivalent `frameIdx` in the partner timeline using `meta.phaseBoundaries`.

## Formula overlay & term highlighting

`FormulaOverlay` renders the F-formula's LaTeX via `react-katex` with `trust: true` + custom `\htmlId{F1-term-GB}{…}` macros. After mount, a small effect walks `[id^="F1-term-"]` and toggles `data-active="true"` based on the current frame's `active_terms`. CSS in `styles.css`:

```css
[data-active="true"] { color: var(--color-accent-indigo); filter: drop-shadow(0 0 6px color-mix(in oklab, var(--color-accent-indigo) 35%, transparent)); }
```

`fixtures/formulas/F1-F7.json` gets a new optional field per entry:

```json
{ "id": "F1", "termIds": ["F1-term-GB", "F1-term-RR", "F1-term-CS"], ... }
```

For the visualizer to insert the `\htmlId` wrappers, the formula latex itself needs them. Since editing F1.latex would touch existing rendering, I'll instead ship a parallel `latexAnnotated` field per entry and `FormulaOverlay` prefers `latexAnnotated` when present (graceful no-op for entries without it). Existing readers continue to use `latex`.

## Assistant integration (additive only)

`src/store/ui.ts` `AssistantContextChip` union gets two extra arms:

```ts
| { kind: 'visualizer_frame'; label: string; runId: string; frameIndex: number; tau: number }
| { kind: 'visualizer_comparison'; label: string; runIdA: string; runIdB: string; frameIndex: number }
```

`ContextMenu.tsx` calls `useChat.getState().addContext({...})`. The "Explain this frame" shortcut is a small button visible only when `useLocation().pathname.startsWith('/visualizer/')`; it calls `addContext` then `setOpen(true)` — no chat-completion logic added.

## Dependencies

`add_dependency`: `three`, `@types/three`, `@react-three/fiber`, `@react-three/drei`. No others. Zustand and Recharts are already installed.

## Fixtures (synthetic but internally consistent)

A small Node script (kept under `scripts/gen-visualizations.mjs`, not shipped) generates each timeline by:

1. Reading the existing `runs/{id}.json` to lock `eta_B`, `F_GB`, and `spectra.sgwb` as the final-frame values.
2. Sampling 500 k-modes log-uniform across `spectra.modes.k`'s range.
3. Synthesising 200 frames with smooth phase transitions and a `gb_window` band where `B_± < 0`. `lepton_flow.eta_B_running` interpolates 0 → eta_B.value.
4. Snapshotting the SGWB spectrum at frames {amplification end, post-reheating, today}.
5. Emitting `meta.visualizationHints` per the F-variant table.

I'll commit the script and the generated JSONs; each gzipped under 500KB. The streaming fixture is a JSONL of every 4th frame.

## Quality bars

- Every panel: `<Suspense>` boundary + `EmptyPanel` error path with retry.
- `usePrefersReducedMotion()` — when true: `playing=false` on mount, `LeptonFlowSankey` uses 0ms transitions, `PhaseSpaceCanvas` disables trails.
- Color-blind safe: chirality also encoded with stroke-dash on Panel 3 series and shape variation on Panel 1 (sphere vs. tetrahedron via instanced geometry swap by sign).
- Keyboard: a single `useEffect` on the workbench installs listeners for `space`, `←/→`, `shift+←/→`, `L`, `1..5`, `?`. Listed in `KeymapOverlay`.
- Theming: R3F canvas uses `useTheme` to pick `--color-background` for `gl.setClearColor`.
- Export PNG: `lib/exportFrame.ts` exposes `exportCanvasPng(canvas)` and `exportSvgPng(svgEl, {width, height})` (the SVG variant draws the serialized SVG into a 2D canvas and calls `toBlob`). No new deps.

## README — Handoff to Claude Code (new subsection)

A "Visualizer integration" subsection lists:

1. The three new service functions and their backend endpoints (echoed from JSDoc).
2. The Pydantic-mirror schema for `VisualizationFrame`.
3. The simulator-module → frame-field mapping (M1/M3/M4/M5/M6 as in the prompt).
4. Server-side `compute_visualization_hints(formula_variant)` helper signature.
5. Streaming protocol: 30 frames per cosmological e-fold over `/ws/runs/{id}/visualization-live`.
6. Note that `formula_variant` should land on `RunConfig` server-side; frontend reads it off the timeline today, will switch to `RunConfig.formula_variant` once the type is updated.

## Out of scope (called out so it isn't a surprise)

- Building Control/Research/Runs routes, command palette UI, chat drawer UI, or a "Launch visualizer" button on a non-existent run-detail page. Hooks are added in `useChat`/`useCommandPalette` so future work can wire them in three lines.
- `RunResult.config.formula_variant` field — mentioned in README handoff, not added to types.
- VR/AR; particle auto-tuning beyond the three resolution tiers; server-side persistence of viewpoints.
