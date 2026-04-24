# Plan: User-friendly error UX for fixture-backed service calls

Add a consistent error story across the workbench so a missing, malformed, or invalid fixture (or live-backend response) surfaces as **(a)** a sonner toast with a recovery hint and **(b)** an inline placeholder where the data was supposed to render — never a blank panel or a cryptic stack.

## Problems today

- `loadFixture` checks HTTP status but **never validates JSON shape**. A truncated or hand-edited fixture crashes deep in a chart with `Cannot read properties of undefined`.
- Service functions catch live-backend errors but **silently fall through to fixtures** — the user sees stale data and never learns the live call failed.
- Some routes toast on loader failure (`/`, `/visualizer/$runId`), others don't (`/qa`, panel-level queries). Inconsistent UX.
- `EmptyPanel` only has a "no data" tone — there is no error variant, so a failed panel either disappears, shows a stack, or looks identical to "this run has no data here."
- Toast deduplication is missing — a flapping fixture can fire 6+ toasts per render.

## Approach

### 1. Centralize the error → user-message mapping (`src/lib/serviceErrors.ts`, new)

One helper consumed by every route loader, every `useQuery`, and every panel. Returns `{ title, description, hint, code }`.

```ts
toUserError(err, { scope: "benchmarks" }) → {
  title: "Couldn't load benchmarks",
  description: "The bundled fixture is missing or invalid.",
  hint: "Reload the page; if it persists, file an issue.",
  code: "FIXTURE_INVALID",
}
```

- Maps `ServiceError.code` (`NOT_FOUND` / `INVALID_INPUT` / `UPSTREAM_FAILURE` / `STREAM_ABORTED` / `NOT_IMPLEMENTED`) plus generic `Error` and `ZodError` to friendly copy.
- Honors a per-scope override table for known surfaces (benchmarks, runs, visualization, audit, models, artifacts, formulas, scan).
- Exposes `notifyServiceError(err, scope)` — calls `toast.error` with a stable `id = "svc:<scope>"` (sonner dedupes by id) and routes to `trackError` once.

### 2. Add lightweight runtime shape validation to fixtures (`src/lib/fixtures.ts`)

`loadFixture<T>(path, opts?)` gains an optional `validate?: (raw: unknown) => T` callback. When provided, a shape mismatch throws `new ServiceError("INVALID_INPUT", "Fixture <path> failed validation: <zod issue>")` instead of letting downstream code crash. No validator → today's behavior (no breaking change).

Wire validators for the highest-value fixtures using **existing** zod schemas where they already exist, and minimal new schemas where they don't:

- `benchmarks.json` → `z.object({ benchmarks: z.array(BenchmarkEntrySchema) })`
- `runs/*.json` → `RunResultShape` (fields actually consumed: `runId`, `status`, `audit?`, optional `config`)
- `models.json` → `z.array(ModelDescriptorShape)`
- `formulas/F1-F7.json` → `z.array(FormulaEntryShape)`
- `scans/*.json` → `ScanResultShape` (axis lengths must match grid dims)

Visualization timelines already pass through `bakeTimelineBuffers`, which throws on bad shapes — keep as-is, just route the throw through `notifyServiceError`.

### 3. Surface live-backend fall-through (`src/services/*.ts`)

When `FEATURES.liveBackend && isBackendConfigured()` and the live call fails, currently we silently use fixtures. Add a **single** dev-only toast (`id: "svc:live-fallback:<scope>"`) explaining "Live backend unavailable — showing bundled sample data." Production users still get the silent fallback (no scary toast for visitors of the demo site), but developers get the signal. Gated on `FEATURES.liveBackend === true` so demo-mode users never see it.

### 4. New `<DataErrorPanel />` component (`src/components/data-error-panel.tsx`)

Sibling to `EmptyPanel`. Same visual language (dashed border, muted bg) but with a destructive-toned icon, the user message, and a `Retry` button slot. Used as the inline placeholder anywhere a fixture-backed query fails.

```tsx
<DataErrorPanel
  title="Couldn't load formula reference"
  description="The bundled fixture is missing or invalid."
  onRetry={() => refetch()}
  dense
/>
```

### 5. Wire it up in consumers

- **`src/routes/index.tsx` loader** — replace ad-hoc try/catch with `notifyServiceError(err, "benchmarks")` then rethrow (route's `errorComponent` already exists).
- **`src/routes/visualizer.$runId.tsx` loader** — same, scope `"visualization"`. Keep the `NOT_FOUND → notFound()` branch.
- **`src/routes/qa.tsx` loader** — wrap in try/catch, toast, rethrow (currently silently crashes the route).
- **`src/routes/visualizer.tsx`** — `listVisualizationRunIds()` is sync and can't fail; no change.
- **`src/components/visualizer/panel-formula.tsx`** — replace the inline `useEffect`/`toast.error` block with `notifyServiceError` + render `<DataErrorPanel onRetry={refetch} />` instead of the silent `EmptyPanel` when `formulasError` is set.
- **`src/components/chat/chat-drawer.tsx`** — already toasts. Switch to `notifyServiceError` for consistency (preserves the "Assistant failed" copy).

### 6. Guard against double-toasting on retry

`notifyServiceError` uses sonner's stable `id` per scope so a `router.invalidate()` retry replaces the existing toast instead of stacking. Includes a `dismiss(scope)` helper called by `<DataErrorPanel onRetry>` and route `reset()` paths so the toast clears the moment the user acts.

## Files

**New**
- `src/lib/serviceErrors.ts` — mapper + `notifyServiceError` + `dismissServiceError`
- `src/lib/fixtureSchemas.ts` — minimal zod shapes for the fixtures we validate
- `src/components/data-error-panel.tsx` — inline error placeholder

**Edited**
- `src/lib/fixtures.ts` — add `validate?` option
- `src/services/simulator.ts` — pass validators; emit dev-only live-fallback toast
- `src/services/assistant.ts` — same
- `src/services/visualizer.ts` — same
- `src/services/artifacts.ts` — same; toast on `downloadArtifact` failure (currently throws raw)
- `src/routes/index.tsx` — use `notifyServiceError`
- `src/routes/visualizer.$runId.tsx` — use `notifyServiceError`
- `src/routes/qa.tsx` — wrap loader; add toast
- `src/components/visualizer/panel-formula.tsx` — use `<DataErrorPanel>`
- `src/components/chat/chat-drawer.tsx` — use `notifyServiceError`

## Out of scope

- Refactoring `ServiceError` codes (additive only).
- Changing the persistence layer's silent-fallback semantics — those are intentional cold-start backfills and already filtered by `src/lib/persistence.ts`.
- A retry-with-backoff mechanism for transient network errors. (Sonner's action button + `router.invalidate()` is sufficient for this pass.)
- Internationalization of the error copy.
