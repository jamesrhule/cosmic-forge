## Goal

Close the remaining silent-failure gaps in the visualizer surface. Today, only `panel-formula` validates its fixture and renders `DataErrorPanel`. The route loader surfaces a toast on `getVisualization` failure but a malformed timeline (truncated JSON, missing `frames`, broken `meta`, NaN positions) can still slip through `loadFixture` and crash deep inside `bakeTimelineBuffers` or the chart panels.

## Changes

### 1. Validate visualization timelines at load time
**File:** `src/lib/fixtureSchemas.ts`
- Add a lenient `VisualizationTimelineShape` Zod schema asserting only what downstream code dereferences:
  - `runId: string`, `formulaVariant: enum(F1..F7)`
  - `frames: array(min 1)` of objects with `tau:number`, `phase:string`, `B_plus/B_minus/xi_dot_H: finite number`, `lepton_flow: { chiral_gw, anomaly, delta_N_L, eta_B_running }`, `active_terms: string[]`, `modes: array`
  - `meta: { durationSeconds, tauRange:[number,number], phaseBoundaries: record, visualizationHints: { panelEmphasis, particleColorMode, extraOverlays, formulaTermIds } }`
  - Use `.passthrough()` on the outer object and on `frames[]` so unknown forward-compatible fields stay through.

### 2. Wire the validator + per-panel error fallback
**File:** `src/services/visualizer.ts`
- Pass `{ validate: (raw) => VisualizationTimelineShape.parse(raw) as VisualizationTimeline }` to the `loadFixture<VisualizationTimeline>(path, ...)` call inside `getVisualization`.
- Wrap the `bake(...)` call in a try/catch and rethrow as `ServiceError("INVALID_INPUT", ...)` so a baking crash maps to the same friendly toast path instead of a blank screen.
- Same treatment for the JSONL fallback in `streamVisualization`: catch parse errors per line, skip and `trackError("service_error", { scope:"viz_stream" })` so stream hiccups don't kill the generator.

### 3. Replace the run-level "Couldn't load this visualization" screen with DataErrorPanel
**File:** `src/routes/visualizer.$runId.tsx` — `RunErrorComponent`
- Render a centered `<DataErrorPanel>` instead of the bespoke markup.
- Title/description come from `toUserError(error, "visualization")` (so the on-screen copy matches the toast verbatim).
- `onRetry` calls `router.invalidate(); reset();` (current behavior preserved, now wired through the standardized button).
- `secondaryAction` keeps the existing `<Link to="/visualizer">Back to runs</Link>` styled as a small ghost button.

### 4. Add an inline DataErrorPanel guard to each timeline-driven panel
The five chart panels (`panel-phase-space`, `panel-gb-window`, `panel-sgwb`, `panel-anomaly`, `panel-lepton-flow`) currently fall back to `EmptyPanel("Pick a run …")` when `timelineA` is null — fine. But when a non-null timeline arrives with a corrupted frame they can still throw at render time (e.g. baked buffers mismatched with `modeCount`, missing `lepton_flow` for the active frame).

For each of those five panels:
- Wrap the panel body in a small local error boundary helper (`withPanelErrorBoundary(label, scope)`) — a thin wrapper around React's error boundary that renders `<DataErrorPanel dense title="Couldn't render <label>" description={err.message} onRetry={() => forceRemount()} />` and calls `notifyServiceError(err, "visualization", { silent: true })` once on capture (silent because the route-level toast already fires for load failures; this one is only for render-time crashes that escape validation).
- Place this helper in `src/components/visualizer/panel-error-boundary.tsx` (new file).

### 5. Visualizer-index empty state stays as-is
`src/routes/visualizer.index.tsx` already shows a clean `EmptyPanel` when no runs are registered — no fixture failure path, no change needed.

## Out of scope
- Per-frame validation inside the bake loop (would slow fixtures-first dev; the lenient outer schema is enough to catch real corruption).
- Replacing toasts in `panel-formula` — already on the new pattern.
- Backend live-mode handling — separate stream.

## Files touched

- `src/lib/fixtureSchemas.ts` — add `VisualizationTimelineShape`.
- `src/services/visualizer.ts` — validate fixture + guard `bake()` + guard JSONL stream.
- `src/routes/visualizer.$runId.tsx` — `RunErrorComponent` switches to `DataErrorPanel` + `toUserError`.
- `src/components/visualizer/panel-error-boundary.tsx` — new helper component.
- `src/components/visualizer/visualizer-layout.tsx` — wrap each `<PanelTile>`'s child in `withPanelErrorBoundary` (single-line change per panel).

## Verification

- `bun run typecheck` clean.
- Manually corrupt `public/fixtures/visualizations/kawai-kim-natural.json` (e.g. drop `meta.tauRange`) → expect a single "Couldn't load this visualization" toast plus the new `DataErrorPanel` with a working Retry button on `/visualizer/kawai-kim-natural`.
- Throw inside one panel's `useMemo` (temporary) → expect only that panel to flip to its dense `DataErrorPanel` while the other five continue to render.
