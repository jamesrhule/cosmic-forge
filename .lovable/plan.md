# Tier 4 — Visualizer Bundle Splitting

The `/visualizer/$runId` lazy chunk is 2.2 MB because three heavy libraries (KaTeX, Recharts, @react-three/fiber + three) are statically imported by the panels. They all load eagerly the moment a run is opened, even before the user looks at a given panel. This pass lazy-loads each library at the panel boundary and verifies SSR doesn't pull them in.

## Goals

- Reduce the visualizer entry chunk by splitting the three heavy libs into their own dynamically-imported chunks.
- Keep SSR clean: R3F (`Canvas`) must stay browser-only; KaTeX CSS must still load; Recharts must not crash during server render.
- No visible UX regression: panels show a small skeleton while their library chunk streams in.

## Scope (files touched)

```text
src/components/visualizer/panel-phase-space.tsx     — R3F Canvas → React.lazy + ClientOnly fallback
src/components/visualizer/panel-gb-window.tsx       — Recharts → React.lazy inner chart
src/components/visualizer/panel-sgwb.tsx            — Recharts → React.lazy inner chart
src/components/visualizer/panel-anomaly.tsx         — Recharts → React.lazy inner chart
src/components/visualizer/panel-formula.tsx         — KaTeX → React.lazy MathBlock
src/components/equation-block.tsx                   — KaTeX → React.lazy BlockMath
src/components/math.tsx                             — keep as-is, becomes the lazy target
src/components/sgwb-plot.tsx                        — Recharts → React.lazy
src/components/potential-preview-chart.tsx          — Recharts → React.lazy
```

Two new tiny wrapper files:

```text
src/components/visualizer/lazy/phase-space-canvas.tsx   — default export wrapping current PhaseSpaceCanvas inner
src/components/visualizer/lazy/recharts-bundle.ts       — single dynamic chunk that re-exports {LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceArea, Legend}
src/components/lazy/katex-block.tsx                     — default export of `BlockMath` + side-effect CSS import
src/components/lazy/katex-inline.tsx                    — default export of `InlineMath` + CSS
```

Co-locating the dynamic re-exports in their own files is what allows Rollup to emit a separate chunk per library.

## Approach per library

### 1. R3F + three (largest win, ~900 KB)

`panel-phase-space.tsx` already wraps `Canvas` in `<ClientOnly>`. Move the **entire `Canvas` subtree + every `useFrame` / `useThree` consumer** into a new file `src/components/visualizer/lazy/phase-space-canvas.tsx` with a default export. Then in `panel-phase-space.tsx`:

```tsx
const PhaseSpaceCanvasInner = React.lazy(
  () => import("./lazy/phase-space-canvas")
);
// ...
<ClientOnly fallback={<PanelSkeleton label="Loading 3D…" />}>
  <Suspense fallback={<PanelSkeleton label="Loading 3D…" />}>
    <PhaseSpaceCanvasInner {...props} />
  </Suspense>
</ClientOnly>
```

`ClientOnly` guarantees the `import()` only fires after hydration → three.js never enters the SSR bundle.

### 2. Recharts (~400 KB)

Recharts is SSR-safe but heavy. Three visualizer panels + two non-visualizer components import it.

Create one shared lazy module so all consumers share a single chunk:

```ts
// src/components/visualizer/lazy/recharts-bundle.ts
export { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceArea, Legend } from "recharts";
```

Each chart panel becomes:

```tsx
const RechartsChart = React.lazy(async () => {
  const r = await import("./lazy/recharts-bundle");
  return { default: (props) => <RealChart {...props} r={r} /> };
});
```

Wrap with `<Suspense fallback={<ChartSkeleton />}>` inside `<ResponsiveChart>`. No `ClientOnly` needed — Recharts works during SSR, but we still defer the chunk download.

### 3. KaTeX (~280 KB)

`react-katex` + `katex/dist/katex.min.css` are the third offender. Two surface points:

- `panel-formula.tsx` (`Math as MathBlock`)
- `equation-block.tsx` (`BlockMath` + CSS import on line 1)
- `routes/index.tsx` uses `EquationBlock`

Create `src/components/lazy/katex-block.tsx`:

```tsx
import "katex/dist/katex.min.css";
import { BlockMath } from "react-katex";
export default BlockMath;
```

Then `equation-block.tsx`:

```tsx
const BlockMath = React.lazy(() => import("@/components/lazy/katex-block"));
// <Suspense fallback={<code>{latex}</code>}><BlockMath math={latex} /></Suspense>
```

The `latex` text is a perfectly readable fallback while the chunk loads.

`panel-formula.tsx` does the same, with the wrapper-ref behavior preserved (the `data-active` walk already runs in an effect — that effect just needs to wait for the `Suspense` boundary to resolve, which is the natural React behavior).

## SSR safety checklist

- R3F: gated behind `<ClientOnly>` → no SSR import. ✅
- KaTeX: works in SSR (already does today via `react-katex`). The `import()` will execute on the server too — safe. ✅
- Recharts: works in SSR; lazy `import()` executes server-side, ResponsiveContainer already uses `ResponsiveChart` wrapper. ✅
- `vite.config.ts` is `defineConfig()` from `@lovable.dev/vite-tanstack-config` — do **not** add `ssr.external` or `resolve.external` (forbidden per platform rules). ✅

## Skeletons

Add one shared `<PanelSkeleton label="..."/>` (12 lines, animate-pulse) reused across panels and chart fallbacks. Lives in `src/components/visualizer/panel-skeleton.tsx`.

## Verification

After the edits I will:

1. Run `npm run build` and report the new visualizer chunk size + the new emitted chunks (expect: `katex.<hash>.js`, `recharts.<hash>.js`, `phase-space.<hash>.js`).
2. Run `npm run typecheck`.
3. Spot-check `/visualizer`, `/visualizer/<runId>`, `/qa?tab=control` (uses SGWBPlot), and `/` (uses EquationBlock) by reading the rendered output to confirm no regression.

## Out of scope (intentional)

- Pruning unused Radix primitives — that's Tier 4 step 2; keeping this turn focused.
- Activating live backend / SSE wiring — Tier 6.
- Any visual redesign.

## Expected outcome

Visualizer entry chunk ~2.2 MB → ~600–800 KB. KaTeX/Recharts/R3F land as parallel chunks fetched only when the consuming panel mounts. The `/visualizer` index route stays unchanged (already excluded these libs).