## Goal

Get the frontend into ship-ready state. The build is green and types are clean — what remains is a list of correctness, polish, accessibility, and SEO/perf fixes I caught while sweeping the codebase. I've grouped them by priority so we can ship after Tier 1 if needed and treat Tier 2/3 as fast-follows.

---

## Tier 1 — ship blockers (must land before publish)

1. **Auth-redirect render bug on `/login`** (`src/routes/login.tsx`)
   The current code calls `void navigate(...)` directly inside the function body when `user` is set. That's a side-effect during render and causes a React warning + double-navigate on fast refresh. Move into `useEffect` and return `null` while the redirect is in flight.

2. **`liveBackend` cutover toggle is fixture-only and silent** (`src/components/visualizer/visualizer-layout.tsx` → `LiveStreamControl`)
   The Live toggle is wired but the per-route hook is mounted unconditionally even when no `runIdA` exists (it just disables the button). Hide the entire control when there's no master timeline, and gate the whole control behind `FEATURES.liveVisualization === true || import.meta.env.DEV` so production users don't see a "Live" affordance pointing at bundled JSONL fixtures. Update the indicator's `aria-label` to reflect "Demo stream" vs "Live stream".

3. **Stale visualizer card metadata** (`src/routes/visualizer.index.tsx:78`)
   Every card hardcodes `"240 frames · 24 k-modes · baked GPU buffers"` regardless of the underlying fixture. Either compute real metadata at loader time (frame count + k-mode count from the timeline JSON) or remove the misleading line. Quickest fix: move the per-run summary into `listVisualizationRunIds()` so the loader returns `{ runId, frameCount, kModes }`.

4. **Narrow-screen gate is too aggressive** (`src/routes/index.tsx`)
   Today: under 1024px the Configurator is replaced with "Designed for wide screens". The current preview is 596px wide → users on tablets/landscape phones get only the marketing card. Either (a) ship a stacked single-column variant of the configurator for ≥640px, or (b) reduce the breakpoint to 768px and let the resizable panels collapse. Pick (a); (b) is brittle.

5. **`/qa` 404 in production renders a duplicate of root 404 inline** (`src/routes/qa.tsx`)
   The "not in dev → render 404 markup" branch hand-rolls a 404 page that drifts from `error-page.tsx`. Either `throw notFound()` so the root `notFoundComponent` runs, or import `<ErrorPage />`.

6. **Plausible script loads even when `PLAUSIBLE` env var is unset on prod** — verify
   Confirm `PLAUSIBLE` resolves correctly in the deployed bundle (`src/lib/telemetry.ts`). If it's intended only for prod, gate the `<script>` injection in `__root.tsx` on `import.meta.env.PROD` as a belt-and-braces.

7. **Title casing/inconsistency**
   `head().meta` uses both "UCGLE-F1 Workbench" and "UCGLE-F1 — Workbench" across routes. Standardize the suffix (pick one).

---

## Tier 2 — should land before publish

8. **Bundle size: `phase-space-r3f` ≈ 1.98 MB and `router` ≈ 1.74 MB**
   - Confirm `phase-space-r3f` chunk is only loaded by the `/visualizer/$runId` lazy route (it appears to be — verify after build).
   - The `router` chunk includes vendor code that should be split. Add `manualChunks` for `react-katex` (635 kB) and `recharts` (`CartesianChart` 791 kB) so they don't get pulled into the initial route's chunk graph when not used.

9. **`getStreamFrameCount` does a full GET of the JSONL just to count lines** (`src/services/visualizer.ts`)
   Cheap fix: cache the count per `runId` in a module-level `Map` so subsequent toggles don't refetch the whole file. Acceptable for a fixture; bake the counts into a static map next to `VISUALIZATION_FIXTURES` and skip the network entirely.

10. **Stream control is invisible when scrolled past in narrow viewports** (`src/components/visualizer/visualizer-layout.tsx` header)
    Header is sticky-ish but `LiveStreamControl` plus the three toggles + Export overflow at <900px wide and wrap into a second row that pushes the panel grid down. Add `flex-wrap` + `min-w-0` truncation on `toolbarLead`, or move toggles into a `…` overflow menu under a breakpoint.

11. **Per-route OG images missing**
    Per the TanStack Start guide in context, leaf routes with hero visuals should set `og:image`. The visualizer index/run pages have nothing. For `/visualizer/$runId`, generate a deterministic preview URL (or use a single static `/og/visualizer.png`) and wire it into both `og:image` and `twitter:image`.

12. **`startRun` always falls back to the demo run id `"kawai-kim-natural"` for anonymous users** (`src/services/simulator.ts:263`)
    User-visible: an anonymous user clicks "Run simulation" and is silently routed back to the same canned run with no toast explaining why. Either disable the run button when `!user && !FEATURES.liveBackend`, or surface a `toast.message("Sign in to author your own runs — showing the demo run instead")`.

13. **`exportFirstCanvas` only exports the phase-space WebGL canvas** (`visualizer-layout.tsx:279`)
    Either rename the button "Export phase space" to be honest, or add a small popover with three options (current panel / phase space / all panels as ZIP). Renaming is the quick ship.

14. **`visualizer-context.tsx` exposes the master timeline but no `runId` for partner panels** — verify the partner panel phase-mapping doesn't read stale state on rapid runB swaps; currently the loader is keyed only on `runB` but the URL-driven `seek` effect uses `seededRef` which never resets when `a.runId` changes between visits. Reset `seededRef.current = false` in the cleanup.

---

## Tier 3 — polish (post-ship is fine)

15. **Empty states across the visualizer**
    - `EmptyPanel` only shows on the index page when `runIds.length === 0`; the workbench panels render a blank canvas if `timelineA?.frames.length === 0` instead of an empty state. Wrap each panel's "no data" branch in `<EmptyPanel />` for consistency.

16. **A11y sweep**
    - `<Toggle>` "Sync phase" / "Overlay" / "Split" / "Live" have `title` attributes but no visible focus ring on the dark theme — add `focus-visible:ring-2 focus-visible:ring-ring`.
    - `TransportBar` keyboard shortcuts (Space/←/→/L/1-5) are documented in `KeymapOverlay` but not announced; add a `aria-keyshortcuts` to each control.
    - `streaming-progress-indicator` has `aria-live="polite"` which will fire on every frame update during a 60-frame stream — debounce the announcement (e.g. announce only on status transitions and on completion).

17. **Error toasts deduplication**
    `notifyServiceError` is called from both the visualizer route loader and the `useVisualizationStream` hook on the same error class. Dedupe by toast id (`toast.error(..., { id: 'visualization' })`) so a network blip doesn't fire two stacked toasts.

18. **`reset-password.tsx` and `auth.callback.tsx` head() blocks**
    Both have `noindex` missing — they shouldn't appear in search results.

19. **Minor copy / consistency**
    - "Restore V2 defaults" button copy in `ActionsRail.tsx` — consider "Restore Kawai-Kim defaults" since "V2" is internal jargon.
    - Footer in `index.tsx` says `"v1.0"` for prod builds; this is hardcoded. Either drive from `import.meta.env.VITE_APP_VERSION` or drop the version string.

20. **Telemetry / chunk-error listener**
    `installChunkErrorListener` is installed in `__root.tsx` but never displays a UI affordance when triggered. Wire it to a one-time `toast.error("App update available — refresh to load the new version", { duration: Infinity, action: { label: 'Refresh', onClick: () => location.reload() } })`.

---

## Out of scope

- Live backend cutover (the FastAPI side and the WS path) — separate milestone.
- Splicing streamed frames into baked panel buffers (deferred per the prior plan).
- New domains beyond UCGLE-F1 (the QCompass Phase 2 placeholders stay disabled).

---

## Suggested execution order

1. Land Tier 1 #1, #4, #5 (route correctness) in one pass.
2. Tier 1 #2, #3, #6, #7 (visualizer + meta consistency) in a second pass.
3. Tier 2 #8–#14 grouped into one pass.
4. Tier 3 polish in a final pass.

This keeps each diff small enough to review in isolation and lets us publish after Tier 1+2.
