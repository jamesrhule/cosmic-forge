# Plan — ResizeObserver-driven Recharts containers

Recharts' built-in `ResponsiveContainer` listens to `window.resize`, not to the parent element. When a user drags a `react-resizable-panels` handle, the panel resizes but the window does not, so charts inside the Configurator (and later Research) keep their stale width until the window itself is resized. We'll replace `ResponsiveContainer` with a small in-house wrapper backed by `ResizeObserver` and use it everywhere a Recharts chart is mounted.

## New file

**`src/components/charts/responsive-chart.tsx`** — generic `<ResponsiveChart>` wrapper.

Behavior:
- Renders a `div` with `width: 100%` and the configured `height` (number or string), measured via `ResizeObserver` on the div itself.
- Uses a `useLayoutEffect` to attach the observer and seed initial dimensions from `getBoundingClientRect()` so the first paint is correct (no 0×0 flicker).
- Calls children as a render-prop: `children({ width, height })` so we can pass concrete numbers to Recharts' `LineChart` / `BarChart` etc.
- Skips render until `width > 0` to avoid Recharts' "width(0) and height(0) of chart should be greater than 0" warning.
- Throttles updates with `requestAnimationFrame` to coalesce rapid drag events into one render per frame.
- SSR-safe: guards `typeof ResizeObserver !== "undefined"`; falls back to a one-shot `getBoundingClientRect` measurement on mount.
- Cleans up the observer and any pending RAF on unmount.

API:
```ts
interface ResponsiveChartProps {
  height: number | string;          // px number or CSS string (e.g. "100%")
  minWidth?: number;                 // default 0
  className?: string;
  children: (size: { width: number; height: number }) => React.ReactNode;
}
```

## Edits

**`src/components/potential-preview-chart.tsx`**
- Drop the `ResponsiveContainer` import.
- Replace the `<div><ResponsiveContainer><LineChart …/></ResponsiveContainer></div>` block with `<ResponsiveChart height={height}>{({ width, height }) => <LineChart width={width} height={height} …/>}</ResponsiveChart>`.
- Keep all axis/tooltip/line config unchanged.

**`src/components/sgwb-plot.tsx`**
- Same swap: drop `ResponsiveContainer`, render `LineChart` with explicit width/height from the wrapper.
- Keep log scales, reference areas, legend, and color array unchanged.

**`src/components/parameter-heatmap.tsx`**
- This component is custom SVG with a fixed `viewBox` and `className="block w-full"`, so it already scales. No change needed — call this out so we don't accidentally rewrite it.

## Why ResizeObserver and not just window resize

`react-resizable-panels` mutates panel widths through inline styles in response to pointer events; the window `resize` event never fires. `ResizeObserver` fires on every box-size change of the observed element, which is exactly what we need for both:
- Drag of the `<ResizableHandle>` between Configurator panels.
- Future Research view comparison columns and any Sheet/Drawer that animates open.

## Verification (after switch to default mode)

1. Build still passes (`bun run build`).
2. Drag the left handle on `/`; the V(ψ) preview chart's plotting area resizes live with the panel.
3. Resize the window; chart still tracks viewport (sanity check the wrapper doesn't regress the window-resize case).
4. Console shows no Recharts width/height warnings on initial load or during drags.

## Out of scope

- Replacing `ResponsiveContainer` in any non-Recharts library.
- Touching the `ParameterHeatmap` SVG (already responsive via `viewBox`).
- Debounce tuning beyond the single-RAF coalescing — drag perf is already fine at the chart sizes we render.
