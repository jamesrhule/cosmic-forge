# Visualizer panels + chrome — eleven new components

Goal: ship the rendering surface that consumes the 7 fixtures + JSONL stream from the previous turn. No routes, no service changes — just the panels and shell that the upcoming `/visualizer` routes will compose.

## File map (all new, under `src/components/visualizer/`)

### Shell / chrome (5)
1. `transport-bar.tsx` — `TransportBar`
2. `keymap-overlay.tsx` — `KeymapOverlay`
3. `empty-panel.tsx` — `EmptyPanel`
4. `visualizer-layout.tsx` — `VisualizerLayout`
5. `panel-context-menu.tsx` — `PanelContextMenu`

### Panels (6)
6. `panel-phase-space.tsx` — `PhaseSpaceCanvas` (R3F + 2D fallback inline)
7. `panel-gb-window.tsx` — `GBWindowTimeline`
8. `panel-sgwb.tsx` — `SGWBSnapshotPlot`
9. `panel-anomaly.tsx` — `AnomalyIntegrandPlot`
10. `panel-lepton-flow.tsx` — `LeptonFlowSankey` (custom SVG, no extra dep)
11. `panel-formula.tsx` — `FormulaOverlay` (KaTeX with `\htmlId` glow)

All consume `BakedVisualizationTimeline` via `useFrameAt`; all subscribe to `useVisualizerStore` for `currentFrameIndex`. Charts wrap in `ResponsiveChart` so they cooperate with `react-resizable-panels` and the existing chart-size badge.

## Component contracts

```text
EmptyPanel        { title, reason, action?, dense? }
KeymapOverlay     ()                       — listens for "?", renders a Dialog
TransportBar      { label?, className? }   — owns rAF loop + transport hotkeys
PanelContextMenu  { children, items }      — wrap any panel; right-click → actions
VisualizerLayout  { header, transport, children, comparison }
                  — CSS-grid shell: header / 2×3 panels / transport
                  — `comparison: "single" | "ab_overlay" | "split_screen"` flips
                    the grid template (single column for split-screen with two
                    column groups, etc.)

PhaseSpaceCanvas  { timelineA, timelineB?, height? }
GBWindowTimeline  { timelineA, timelineB? }     — also acts as scrubber
SGWBSnapshotPlot  { timelineA, timelineB? }     — uses `sgwb_snapshot` at the
                                                  nearest frame ≤ current
AnomalyIntegrandPlot { timelineA, timelineB? }  — last `anomaly_integrand`
                                                  ≤ current frame
LeptonFlowSankey  { timelineA, timelineB? }
FormulaOverlay    { variant, activeTerms }       — read directly from frame
```

Comparison overlay rule (uniform across all panels): when `comparisonMode === "ab_overlay"` and `timelineB` is provided, render A in indigo (`var(--color-accent-indigo)`) and B in amber (`var(--color-chart-4)`); legend in panel header. Split-screen passes the same panels twice with one timeline each — the layout component handles the split, panels stay single-source.

## Per-panel notes

**PhaseSpaceCanvas** (Panel 1)
- `<Canvas>` with `<InstancedMesh>` of `MAX_MODES` instances; per-frame `useFrame` updates matrices from `timeline.baked.positions[currentFrameIndex]` and instanceColor from `.colors[...]`. Camera: orthographic, axis labels for `log10(k)`, `Re h_+`, `Im h_+`.
- Fallback: when `WebGLRenderingContext` probe returns null, render a Canvas-2D scatter of the same buffers (no instancing — just `ctx.fillRect` per mode). Same axes, same color rules. Behind `<ClientOnly fallback={<EmptyPanel ... dense />}>`.
- Dispatches `visualizer_frame` chip on right-click → "Pin to assistant".

**GBWindowTimeline** (Panel 2)
- Recharts `LineChart`: `B_plus`, `B_minus`, `xi_dot_H` over τ across the full timeline (not just current frame).
- Vertical reference line at the current frame; clicking the chart calls `seek` — this *is* the global scrubber.
- Phase-band shading from `meta.phaseBoundaries`.

**SGWBSnapshotPlot** (Panel 3)
- Log-log `LineChart` of the `sgwb_snapshot` attached to the nearest snapshot frame ≤ current. Three snapshots per timeline → label switches automatically ("source" / "post-reheat" / "today"). Reuses the same axis tokens as the existing `SGWBPlot`.
- Chirality encoded via stroke dash pattern in addition to color (color-blind safe).

**AnomalyIntegrandPlot** (Panel 4)
- Two-axis `ComposedChart`: bar = `integrand`, line = `running_integral`, vertical reference line at `cutoff`. Falls back to the most recent `anomaly_integrand` payload (attached every 10 frames per fixture).

**LeptonFlowSankey** (Panel 5)
- Custom SVG with four nodes (`chiral_gw → anomaly → delta_N_L → eta_B_running`). Stroke widths proportional to magnitudes; cubic-bezier flow paths. No external Sankey lib — keeps the bundle slim.
- Animates flow stroke-dashoffset on each frame change, but skips animation when `usePrefersReducedMotion()` is true.

**FormulaOverlay** (Panel 6)
- Reads `formulaVariant` and `activeTerms` from the current frame. Renders the variant's `latex` from the cached `F1-F7.json` payload (consume via `loadFixture` once on mount, memoised).
- Wraps the LaTeX with `\htmlId{<term>}{...}` annotations. Active terms get `data-active="true"` via a post-render DOM walk; styled with a `.formula-glow` class (indigo box-shadow that fades over 600 ms).
- "Why is this glowing?" tooltip per term, sourced from a small static dictionary in the same file.

## Shell

**VisualizerLayout** uses CSS grid:
```text
+------------------------------------------------+
| header (pickers, comparison toggles, export)   |
+--------------+----------------+----------------+
| PhaseSpace   | GBWindow       | SGWB           |
| (Panel 1)    | (Panel 2)      | (Panel 3)      |
+--------------+----------------+----------------+
| Anomaly      | LeptonFlow     | Formula        |
| (Panel 4)    | (Panel 5)      | (Panel 6)      |
+------------------------------------------------+
| TransportBar (slider, frame counter, speed)    |
+------------------------------------------------+
```
- Single mode: 3-col × 2-row grid as above.
- A/B overlay: same grid, panels render two series each.
- Split screen: 2-col outer × (3-col × 2-row inner). Each inner gets one timeline.

**PanelContextMenu** wraps any panel root and exposes:
- "Pin frame to assistant" — pushes a `visualizer_frame` chip via `useChat.addContext`.
- "Pin comparison" (only when both timelines loaded) — pushes `visualizer_comparison`.
- "Export this panel as PNG" — uses `exportSvgPng` for SVG panels and `exportCanvasPng` for the R3F canvas; reuses `downloadBlob` from `src/lib/exportFrame.ts`.

Implemented with `@radix-ui/react-context-menu` (already installed via `src/components/ui/context-menu.tsx`).

## Hotkey contract

Owned by `TransportBar` (transport + speed) and `KeymapOverlay` (`?`). Comparison hotkeys (`O`, `S`, `P`) and export (`E`) live on `VisualizerLayout` so they're scoped to a mounted visualizer rather than the global app shell. All listeners short-circuit when the active element is an `<input>` / `<textarea>`.

## Design system

Every color is a semantic token: `--color-accent-indigo`, `--color-chart-{2..5}`, `--color-border`, `--color-popover`, `--color-muted`, `--color-foreground`, `--color-muted-foreground`. No raw hex anywhere. Add one new keyframe in `src/styles.css` for `formula-glow` (indigo `box-shadow` pulse). All animations short-circuit when `prefers-reduced-motion: reduce`.

## Out of scope for this turn

- `/visualizer` and `/visualizer/$runId` routes (next turn).
- Run-picker UI / cmd-k integration.
- Live-stream wiring beyond what `streamVisualization` already provides — panels accept a static `BakedVisualizationTimeline`; live mode will swap the timeline reference under their feet without API changes.

## Acceptance

- All 11 component files exist and typecheck (`bun run typecheck`).
- Production build succeeds (`bun run build`); R3F lands in a lazy chunk only when `PhaseSpaceCanvas` is imported (verified by grepping the build output for `three`).
- Wiring sanity: a throwaway storybook-ish smoke route is NOT created — verification happens in the upcoming `/visualizer` route turn. For this turn, components are validated via tsc + a render-only Vitest-style snippet run inline through `code--exec` if needed.
- All transport hotkeys, `?` overlay, and right-click menu work without a route mounted (each component is self-contained and uses the existing stores).
- README "Visualizer" section gets a one-paragraph component map + hotkey table.
