## Goal

Eliminate every navigational dead end and visual lie in the app's header bars. After this change, every page reaches every other page in one click, and no clickable-looking element does nothing.

## Findings (current navigation graph)

```text
                   header link?
   ┌───────────┬───┬───────────┬─────┐
   │ from \ to │ / │ /visualizer│ /qa │
   ├───────────┼───┼───────────┼─────┤
   │ /         │ — │  yes      │ yes │
   │ /visualizer (any) │ yes │  yes  │ yes │
   │ /qa       │ yes │  NO     │  —  │   ← orphaned
   └───────────┴───┴───────────┴─────┘
```

Plus three "looks clickable but isn't" traps:
- `/` header `Configurator | Control | Research` tabs are inert `<span>`s.
- `/` header brand "UCGLE-F1 Workbench" is plain text (the same brand is a link elsewhere — inconsistent affordance).
- `/visualizer` header's `Configurator` link has no active styling, only `Visualizer` does.

## Fixes (no functionality removed)

### 1. Make the QA header carry the same workbench nav as the Visualizer header

In `src/components/qa/qa-shell.tsx`, add a small inline `<nav>` after the brand with `Link`s to `/` (Configurator) and `/visualizer`, mirroring the styling on the visualizer header (`text-sm` muted with `bg-accent` for active). This removes QA's orphaned status — one click reaches every other top-level surface.

### 2. Wire up the fake NavTabs on `/`

In `src/routes/index.tsx`, replace the `<NavTab>` `<span>`s with real `<Link>`s:
- `Configurator` → `to="/"` with `activeOptions={{ exact: true }}`, `activeProps` = the existing "active" styling.
- `Control` → `to="/qa"` with `search={{ tab: "control" }}`.
- `Research` → `to="/qa"` with `search={{ tab: "research" }}`.

The QA harness already accepts `?tab=control` / `?tab=research` and renders the matching frame, so this points the existing mock tabs at the only places that surface those views today. Keeps the visual exactly the same, but they finally do something.

The `NavTab` helper becomes a styled `<Link>` wrapper; the `active` prop disappears and `activeProps` takes over (TanStack Router sets it automatically based on the current route).

### 3. Make the Configurator header brand a Link

In `src/routes/index.tsx`, change `<span>UCGLE-F1 Workbench</span>` to `<Link to="/" activeOptions={{ exact: true }}>UCGLE-F1 Workbench</Link>`. Identical visual; matches the affordance users already learn on `/qa` and `/visualizer`. On `/` the click is a no-op refresh — same behavior as those other headers.

### 4. Add active styling to the Configurator link in the visualizer header

In `src/routes/visualizer.tsx`, give the `to="/"` (Configurator) link the same `activeOptions={{ exact: true }}` + `activeProps` treatment the `to="/visualizer"` link already has. Symmetry, and accurate visual feedback when the user is on `/` (only relevant when the parent header is reused — currently not the case, but cheap and prevents future confusion).

### 5. Improve the global 404

In `src/routes/__root.tsx` `NotFoundComponent`, add a secondary outline `Link to="/visualizer"` next to "Go home". Users who landed on a typo'd `/visualizer/$runId` get bounced through here and currently can only return to `/`.

## Files touched

- **edit** `src/components/qa/qa-shell.tsx` — add workbench nav links in the header.
- **edit** `src/routes/index.tsx` — convert `NavTab`s to real `Link`s; convert brand to `Link`.
- **edit** `src/routes/visualizer.tsx` — add active-state styling to the Configurator link.
- **edit** `src/routes/__root.tsx` — add `/visualizer` link to the 404 page.

## Out of scope

- Footer redesign on `/qa` (the doc reference is informational, not a dead end since the header has full nav).
- Adding hash-anchored sections — every route stays as it is.
- Visualizer empty-state copy — already escapable via the parent header.
- Changes to any service, store, fixture, or panel.
