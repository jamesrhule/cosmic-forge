## Goal

Wire the existing Visualizer feature (store, services, layout, panels) into the TanStack Router file-based route tree as two new routes:

- `/visualizer` — index/landing that lists available runs and lets the user pick one (and optionally a B-side comparison).
- `/visualizer/$runId` — the loaded workbench: fetches the timeline, mounts `VisualizerLayout`, code-splits the heavy canvas/panels.

Both routes use validated search params for transport + comparison state, both define `errorComponent` + `notFoundComponent`, and the heavy panel surface (R3F + Recharts + KaTeX) is split into a `.lazy.tsx` chunk so the index route stays light.

## Files to create

### 1. `src/routes/visualizer.tsx` (layout route, critical bundle)

Layout/parent route. Owns:
- `head()` with title/description/og tags for `/visualizer`.
- `validateSearch` (zod) — shared search params inherited by `$runId`:
  - `runB?: string` (optional partner run id, validated against `listVisualizationRunIds()` via `fallback`).
  - `mode: "single" | "ab_overlay" | "split_screen"` (default `"single"`).
  - `phase: boolean` (default `false`) — sync-by-phase toggle.
  - `frame: number` (default `0`) — initial scrubber frame, clamped ≥ 0.
- `loader`: returns `{ runIds: string[] }` from `listVisualizationRunIds()` (sync-friendly, no network in fixture mode).
- `component`: thin shell that renders header chrome (back to Configurator, app shell links) + `<Outlet />`.
- `errorComponent` + `notFoundComponent` (per-route).

### 2. `src/routes/visualizer.index.tsx` (critical, no lazy needed)

Index for `/visualizer`. No timeline is loaded here — keep the bundle small.
- Uses `getRouteApi("/visualizer").useLoaderData()` to read the `runIds` list.
- Renders a card grid: each card links to `/visualizer/$runId` with `params={{ runId }}`.
- Empty-state if `runIds.length === 0` using `EmptyPanel`.

### 3. `src/routes/visualizer.$runId.tsx` (critical route config)

Splits cleanly into critical (loader + config) and lazy (component).
- `loader: async ({ params }) => getVisualization(params.runId)` (returns `BakedVisualizationTimeline`).
- `loaderDeps: ({ search }) => ({ runB: search.runB })` so the loader re-runs only when `runB` changes (not on every scrub).
- Inside loader: if `search.runB` present and ≠ `runId`, call `getVisualization(search.runB)` in parallel via `Promise.all`; return `{ a, b: b ?? null }`.
- `head()` derives title from `params.runId`.
- Catches `ServiceError("NOT_FOUND")` from the service and rethrows `notFound()` so the per-route `notFoundComponent` (not the error boundary) handles missing fixtures.
- No `component` field here — provided by the lazy file below.

### 4. `src/routes/visualizer.$runId.lazy.tsx` (split chunk — heavy panels)

- `createLazyFileRoute("/visualizer/$runId")`.
- Uses `getRouteApi("/visualizer/$runId")` for `useLoaderData` / `useParams` / `useSearch` (NOT `import { Route }` — that defeats splitting).
- Reads `mode` / `phase` / `frame` from search and pushes into `useVisualizerStore` on mount (and on change). Initial transport seeds from `frame`.
- Subscribes to store via `subscribeWithSelector` to push `currentFrameIndex`, `comparisonMode`, `syncByPhase` back to the URL via `useNavigate({ from: "/visualizer/$runId" })` with `replace: true` and a small debounce (~150ms) so scrubbing doesn't spam history.
- Renders `<VisualizerLayout timelineA={a} timelineB={b} toolbarLead={…breadcrumb + run-picker chip} />`.
- `errorComponent` + `notFoundComponent` (notFound shows "No visualization for this run" with a link back to `/visualizer`). Both safe to put on the lazy file alongside the component.

### 5. `src/lib/visualizerSearch.ts` (small)

Single zod schema reused by both routes (export `visualizerSearchSchema` + `VisualizerSearch` type). Keeps the inheritance chain DRY — `/visualizer` validates the schema, `$runId` automatically inherits it.

## Files to edit

### `src/routes/__root.tsx`

No structural changes required — root already provides `Outlet` and a global `notFoundComponent`. No edit unless we want a top-nav `<Link to="/visualizer">` (out of scope for this step; nav lives inside route shells).

### `src/routes/index.tsx` (Configurator nav)

Add a `/visualizer` link next to the existing `/qa` chip in the header so the route is reachable. One-line edit; no behaviour change.

### `src/config/features.ts`

No edit; `FEATURES.liveVisualization` already exists and is consumed by the service.

## Search-param contract (full schema)

```ts
// src/lib/visualizerSearch.ts
import { z } from "zod";
import { fallback } from "@tanstack/zod-adapter";

export const visualizerSearchSchema = z.object({
  runB: fallback(z.string(), undefined as unknown as string).optional(),
  mode: fallback(
    z.enum(["single", "ab_overlay", "split_screen"]),
    "single",
  ).default("single"),
  phase: fallback(z.boolean(), false).default(false),
  frame: fallback(z.number().int().min(0), 0).default(0),
});
export type VisualizerSearch = z.infer<typeof visualizerSearchSchema>;
```

URL examples:
- `/visualizer` — landing.
- `/visualizer/kawai-kim-natural` — single-mode, frame 0.
- `/visualizer/kawai-kim-natural?runB=starobinsky-standard&mode=ab_overlay&phase=true&frame=42` — full state restorable from URL.

## Error / not-found behaviour

| Surface | Trigger | Renders |
|---|---|---|
| `/visualizer` errorComponent | loader throws | inline error card with Retry (calls `router.invalidate(); reset()`) |
| `/visualizer` notFoundComponent | unreachable (no children mismatch) | small "Not found" card |
| `/visualizer/$runId` errorComponent | unexpected service error | error card with Retry |
| `/visualizer/$runId` notFoundComponent | `getVisualization` throws `NOT_FOUND` → loader rethrows `notFound()` | "No visualization for run X" + link to `/visualizer` |
| Root `notFoundComponent` | typo in URL (e.g. `/visualizers`) | existing 404 page (already in place) |

## Code-splitting plan

```text
visualizer.tsx              critical (small: layout + search schema + loader for runIds)
visualizer.index.tsx        critical (small: card list)
visualizer.$runId.tsx       critical (loader + config only — no component)
visualizer.$runId.lazy.tsx  SPLIT chunk (R3F canvas, Recharts, KaTeX, all 6 panels,
                            VisualizerLayout, TransportBar, KeymapOverlay)
```

Effect: visiting `/visualizer` (the index) does **not** download the WebGL/Recharts/KaTeX bundle. Only `/visualizer/$runId` triggers the lazy chunk. Loader stays in the critical chunk per TanStack guidance (avoids double-async cost of fetching then loading).

## Acceptance checks

- `bun run typecheck` passes; `routeTree.gen.ts` regenerates with the four new routes.
- `/visualizer` shows the run grid and is interactive without loading R3F.
- `/visualizer/kawai-kim-natural` loads the baked timeline and renders all six panels at 60fps.
- Scrubbing updates `?frame=…` (debounced); refreshing the page restores the same frame, mode, and partner run.
- `/visualizer/does-not-exist` renders the per-route `notFoundComponent`, not a generic crash.
- Toggling A↔B overlay (`O`) and split-screen (`S`) updates `?mode=…`; toggling sync-phase (`P`) updates `?phase=…`.
- No edits to existing services, panels, or store APIs — purely additive routing.
