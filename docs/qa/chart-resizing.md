# Chart-resizing QA checklist

This document is the manual QA script for verifying that every Recharts /
SVG chart in the workbench resizes correctly during a panel drag, on
initial load, and after switching tabs / collapsing accordions.

The shell uses a custom `ResizeObserver`-based wrapper
(`src/components/charts/responsive-chart.tsx`) instead of Recharts' own
`ResponsiveContainer`, because `react-resizable-panels` mutates panel
widths via inline styles without firing `window.resize`. Run this
checklist whenever that wrapper, the panel layout, or any chart
component changes.

## Setup

1. `npm install && npm run dev`.
2. Open <http://localhost:5173/>.
3. Open DevTools → Console. The console **must stay free** of:
   - `The width(0) and height(0) of chart should be greater than 0`
   - `findDOMNode is deprecated`
   - any `ResizeObserver loop ...` errors

## Enable the dev overlay

The overlay paints a small black chip on each chart showing
`label · width × height · n=<update count>`. Use the counter to confirm
visually that `ResizeObserver` is firing during a drag.

Either:

```js
localStorage.setItem("ucgle.devOverlay", "1");
location.reload();
```

…or just append `?devOverlay=1` to any URL once — `__root.tsx` copies the
flag into `localStorage` so it survives navigation.

To turn it off:

```js
localStorage.removeItem("ucgle.devOverlay");
location.reload();
```

The badge component is gated behind this flag and renders `null` when
disabled — zero cost in production browsing.

## 1. Configurator (`/`)

Charts under test: **V(ψ) preview** (`label="vψ"`), inside the Potential
card on the left form column (the chart itself renders in the middle
preview column once the form is implemented; today it's also previewed
inline within `PotentialCard`).

| # | Step | Expected |
|---|---|---|
| 1 | Hard reload the page. | Chart paints once at the correct size with no flicker; overlay shows non-zero `w × h`; `n` starts at 1 or 2. |
| 2 | Drag the **left** resizable handle slowly right, then back left. | Overlay `w` updates within one animation frame; the SVG's `width` attribute matches; `n` increments smoothly. |
| 3 | Drag the **right** resizable handle. | Same — middle column shrinks/grows; `w` tracks. |
| 4 | Collapse the **Potential** accordion, then re-open it. | Chart remounts at correct size on re-open; no console warnings. |
| 5 | Resize the browser window between ~1024px and full-width. | Chart still tracks viewport (sanity check: window-resize path is not regressed). |
| 6 | Shrink the window below 1024px. | Wide-screen gate appears, the entire `<Configurator>` subtree unmounts, **no chart warnings** are logged. |
| 7 | Expand back above 1024px. | Configurator re-mounts cleanly; chart paints once, no double-mount or 0×0 frames. |

## 2. Control view *(TBD when route lands)*

Charts under test: **SGWB plot** (`label="sgwb"`), **Parameter heatmap**
(`label="η-scan"`).

Pre-written steps so the checklist is ready when the Control route ships:

| # | Step | Expected |
|---|---|---|
| 1 | Navigate from `/` → Control tab. | First paint shows correct size; no `width(0)` warnings. |
| 2 | Drag the run-list / detail handle. | SGWB plot tracks live; `n` increments. |
| 3 | Switch between two runs in the run list. | Chart remounts at the same size; counter resets. |
| 4 | Switch to Configurator tab and back. | No stale dimensions; chart re-measures on re-mount. |
| 5 | Open the heatmap modal / tab. | Heatmap badge shows current container size; SVG `viewBox` scales without distortion. |

## 3. Research view *(TBD when route lands)*

Charts under test: comparison-grid SGWB plots (multiple `label="sgwb"`
instances side by side).

| # | Step | Expected |
|---|---|---|
| 1 | Open Research with 2+ runs selected. | Each tile renders independently; overlay badges show distinct widths. |
| 2 | Drag the comparison-grid resizer to change column count from 2 → 3 → 1. | Every tile re-measures; no layout overlap; no warnings. |
| 3 | Toggle a run on/off in the picker. | Remaining tiles re-flow and re-measure cleanly. |

## 4. Edge cases

- **SSR**: Right-click → *View Page Source*. The initial HTML must contain
  no `<svg>` chart markup — charts are client-mounted under
  `ClientOnly` / measured-after-mount boundaries.
- **Reduced motion / slow CPU**: Throttle CPU 4× in DevTools, repeat the
  drag tests. Chart should still keep up (one update per frame, not per
  pointer event).
- **Two charts in one panel**: When Research lands, drag a panel that
  contains two SGWB plots and confirm both badges update in lockstep.

## 5. Sign-off

| Date | Tester | View | Result | Notes |
|---|---|---|---|---|
| | | Configurator | | |
| | | Control | | |
| | | Research | | |
