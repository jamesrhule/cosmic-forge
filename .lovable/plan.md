# Plan — Chart-resize QA checklist + dev overlay

Two deliverables: a written checklist for handoff and an opt-in dev overlay so the checklist is fast to actually run.

## 1. New file: `docs/qa/chart-resizing.md`

Plain-text QA script. Sections:

- **Setup** — `npm run dev`, open `http://localhost:5173`, open DevTools console (must stay free of Recharts `width(0)/height(0)` and React `findDOMNode` warnings).
- **Enabling the dev overlay** — set `localStorage.setItem("ucgle.devOverlay", "1")` and reload, or append `?devOverlay=1` to the URL once.
- **Checklist per view**, each a numbered list of pass/fail steps:
  - **Configurator (`/`)**
    1. On load, V(ψ) preview chart fills its card with no flicker; overlay badge reads non-zero `w × h`.
    2. Drag the left handle right → left → right; overlay `w` updates within one frame; SVG `<svg>` width attribute matches.
    3. Drag the right handle similarly.
    4. Collapse and reopen the **Potential** accordion — chart remounts at correct size, no warnings.
    5. Resize the browser window; chart still tracks viewport.
  - **Control** (placeholder until the route lands; checklist already lists the SGWB plot + heatmap steps).
  - **Research** (placeholder; lists the comparison-grid SGWB plots).
- **Edge cases** — narrow-screen gate (<1024px shows the wide-screens card and unmounts charts entirely; verify zero chart warnings); SSR (view page source, confirm no chart markup in initial HTML — charts are client-mounted).
- **Sign-off table** — date / tester / view / pass.

The Control and Research entries are stubs marked `TBD when route lands` so we don't pretend coverage we don't have, but the steps are pre-written so future passes don't have to design QA from scratch.

## 2. New file: `src/components/dev/chart-size-overlay.tsx`

A tiny opt-in HUD attached to the `ResponsiveChart` wrapper. Behavior:

- Reads a flag from `src/config/dev-overlay.ts` (`isDevOverlayEnabled()` → checks `localStorage["ucgle.devOverlay"] === "1"` OR `window.location.search` contains `devOverlay=1`; SSR-safe, returns `false` on the server).
- Component `<ChartSizeBadge width height label?>` renders an absolutely-positioned chip in the top-right of its parent: monospace text like `vψ · 612×200`. Uses `bg-black/70 text-white` (raw colors are acceptable here because this is a debug-only chrome that must contrast against any chart background) — wrapped in a comment explaining the design-token exception.
- Counts updates: keeps a `useRef` increment and shows `· n=37` so you can visually confirm `ResizeObserver` is firing (counter ticks during a drag; stays still when idle).
- Returns `null` when the flag is off — zero runtime cost in normal use.

## 3. New file: `src/config/dev-overlay.ts`

```ts
export function isDevOverlayEnabled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    if (window.localStorage.getItem("ucgle.devOverlay") === "1") return true;
  } catch { /* private mode */ }
  return new URLSearchParams(window.location.search).has("devOverlay");
}
```

Also exports a one-liner `persistDevOverlayFromUrl()` that, on first load, copies `?devOverlay=1` into `localStorage` so the flag survives navigation. Called from `__root.tsx` inside a mount effect.

## 4. Edit `src/components/charts/responsive-chart.tsx`

- Add an optional `label?: string` prop (used as the badge's tag, e.g. `"vψ"`, `"sgwb"`).
- Inside the wrapper div, after `children({...})`, conditionally render `<ChartSizeBadge label={label} width={size.width} height={size.height} />` when `isDevOverlayEnabled()` returns true.
- Keep the wrapper's public API otherwise unchanged.

## 5. Edit chart consumers

- `src/components/potential-preview-chart.tsx` → pass `label="vψ"`.
- `src/components/sgwb-plot.tsx` → pass `label="sgwb"`.
- `src/components/parameter-heatmap.tsx` → custom SVG, no `ResponsiveChart` wrapper. Add the same badge directly via a small absolutely-positioned `<div>` sibling so the heatmap is also covered. Wrap the SVG in a `relative` container.

## 6. Tiny README pointer

Append a one-line bullet under `## 3. Implementation status` (or a new `## 5. QA`) pointing at `docs/qa/chart-resizing.md` and the `localStorage["ucgle.devOverlay"]` toggle. No architectural change.

## Out of scope

- Automated visual-regression tests / Playwright runs (separate pass).
- Telemetry beyond width/height/update count.
- Touching `Configurator` form behavior or any non-chart components.
- Building the Control or Research routes — only the QA steps for them are pre-written.
