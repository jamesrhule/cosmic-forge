## Goal

Add a `/qa` route that bundles the three view layouts (Configurator, Control, Research) onto one page so a tester can drag handles, watch every chart's live size badge, and tick off the resize checklist without hopping between routes.

## What the user will see at `/qa`

```text
┌─ /qa  · Chart resize QA ────────────────────────────────────────┐
│ Header: title · "dev overlay: ON/OFF" pill · [enable] button    │
├─────────────────────────────────────────────────────────────────┤
│ Tabs:  [Configurator]  [Control]  [Research]  [Checklist]      │
├─────────────────────────────────────────────────────────────────┤
│ <Active tab body — height: calc(100vh - header - tabs)>        │
│                                                                 │
│  Configurator tab → 3-panel ResizablePanelGroup that mirrors   │
│    `/`: form column · preview column (V(ψ) chart) · actions    │
│                                                                 │
│  Control tab → 2-panel group: run list · run detail with       │
│    SGWBPlot (kawai-kim + starobinsky overlay)                  │
│                                                                 │
│  Research tab → 2-panel group: ξ×θ ParameterHeatmap ·          │
│    side-by-side SGWBPlot tiles (2 spectra)                     │
│                                                                 │
│  Checklist tab → rendered docs/qa/chart-resizing.md as a       │
│    scrollable column with ✓ checkboxes that persist to         │
│    localStorage so a tester can resume mid-pass                │
└─────────────────────────────────────────────────────────────────┘
```

The dev overlay flag is force-enabled when the tab body mounts (so a tester landing on `/qa` immediately sees every badge without having to type `localStorage.setItem(...)`), and a small status pill shows the live count of mounted badges so it's obvious if a chart failed to render.

## Files

**New**

- `src/routes/qa.tsx` — the route. Loader pulls the three fixtures already used elsewhere (`getBenchmarks`, `getRun("kawai-kim-natural")`, `getRun("starobinsky-standard")`, `getScan(...)`); errorComponent + notFoundComponent included per stack rules. Sets `head()` with `title: "Chart resize QA — UCGLE-F1"` and `noindex` via meta robots.
- `src/components/qa/qa-shell.tsx` — header + tab strip + body switcher (uses existing `Tabs` from `@/components/ui/tabs`).
- `src/components/qa/qa-configurator-frame.tsx` — extracts the 3-panel layout used in `routes/index.tsx` so both `/` and `/qa` render identical structure. The form-card column reuses `PotentialCard` / `CouplingsCard` / `SeesawCard` / `ReheatingCard`; the preview column already contains the `vψ` chart via `PotentialCard`.
- `src/components/qa/qa-control-frame.tsx` — 2-panel ResizablePanelGroup; left lists the four run fixtures, right shows `<SGWBPlot spectra={[selected, baseline]} />`.
- `src/components/qa/qa-research-frame.tsx` — 2-panel; left `<ParameterHeatmap scan={scan} />`, right grid of two `<SGWBPlot>` tiles.
- `src/components/qa/qa-checklist.tsx` — renders the checklist as semantic HTML (one `<section>` per heading from `chart-resizing.md`) with `<input type="checkbox">` per row, persisted to `localStorage` under `ucgle.qa.checklist.v1`.
- `src/lib/qa-checklist-data.ts` — the checklist content as a typed array (sections → rows). Mirrors `docs/qa/chart-resizing.md` so the markdown stays the source of truth and this file is the structured render copy.

**Edited**

- `src/config/dev-overlay.ts` — add `forceEnableForSession()` that sets `localStorage` and a window-scoped flag so `isDevOverlayEnabled()` returns true immediately (today the badge reads the flag in `useEffect`, so a one-shot session enable is enough). Existing API unchanged.
- `src/routes/__root.tsx` — add a `<Link to="/qa">QA</Link>` item to the (currently empty) header nav so the route is discoverable. No other changes.
- `README.md` — under the existing QA section, add a one-line pointer: "Or open `/qa` for an all-in-one dashboard."

`docs/qa/chart-resizing.md` is **not** edited; the structured copy in `qa-checklist-data.ts` references it explicitly so future edits to the markdown trigger an obvious diff in code review.

## Behaviour details

- **Dev overlay auto-on**: `qa.tsx` calls `forceEnableForSession()` in a top-level `useEffect`. A "dev overlay: ON" pill shows in the header; a "disable" button removes the localStorage key and reloads.
- **Badge counter pill**: a small `MountedChartsCounter` reads `document.querySelectorAll('[data-testid="chart-size-badge"]').length` on a `MutationObserver` and shows e.g. `badges: 4`. Confirms at a glance that every expected chart actually mounted.
- **Persistence**: tab choice persisted via TanStack Router search param `?tab=configurator|control|research|checklist`, defaulting to `configurator`. Checklist tick state in `localStorage`.
- **No SSR surprises**: chart frames are wrapped in the existing `ClientOnly` component (already in repo) so Recharts never measures inside server HTML.

## Out of scope

- No changes to the three production routes' behaviour. `/qa` is purely additive.
- No new automated tests — this is a manual QA dashboard.
- No new chart components; we reuse `PotentialPreviewChart`, `SGWBPlot`, `ParameterHeatmap` exactly as they are today.
