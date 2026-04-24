# Robust KaTeX rendering — drop the `react-katex` dependency

## Root cause

The blank screen is caused by `react-katex`, not by our import shape:

1. The dist file (`react-katex.js`) is a UMD bundle. When Vite's SSR module runner sees `Object.defineProperty(exports, "__esModule", true)` it refuses default-as-namespace interop, so `pkg.BlockMath` ends up `undefined`.
2. As a workaround we set `ssr.noExternal: ["react-katex"]`. That made Vite resolve the package's **`src/index.jsx`** (its source field), which then crashed at `PropTypes.string` because `prop-types` doesn't resolve cleanly through the module runner. That is the current `Cannot read properties of undefined (reading 'string')` runtime error visible in the preview.
3. Any "more clever" import wrapper (default + namespace + destructure with fallbacks) still has to evaluate the broken module — so it can't actually save us.

The cleanest, smallest, and most durable fix is to render KaTeX ourselves using `katex.renderToString` (already a transitive dependency we ship) and remove `react-katex` from the import graph entirely. KaTeX's own package is plain ESM/CJS that bundles correctly in both client and SSR, so this also unblocks SSR rendering of the formula panel.

## Changes

1. **`src/components/lazy/katex-block.tsx`** — replace `react-katex` import with a tiny component that calls `katex.renderToString(math, { displayMode: true, throwOnError: false, trust: true, strict: "ignore" })` and renders the HTML via `dangerouslySetInnerHTML`. On render failure (try/catch around `renderToString`) fall back to `<code>{math}</code>` so the panel never blanks.

2. **`src/components/lazy/katex-inline.tsx`** — same pattern with `displayMode: false`, rendered into a `<span>`.

3. **`src/components/math.tsx`** — no API change; still lazy-loads the two chunks above. Update the JSDoc comment to drop the "react-katex" reference.

4. **`vite.config.ts`** — remove `optimizeDeps.include: ["react-katex"]` and `ssr.noExternal: ["react-katex"]` (no longer needed). Keep the `vendor-katex` manualChunks rule (now matches just `/katex/`).

5. **`package.json`** — remove `react-katex` and `@types/react-katex` from `dependencies` / `devDependencies` via `bun remove`. Keep `katex` (we use it directly) and `rehype-katex` (untouched, used by markdown pipeline).

## Technical detail

The replacement component is ~15 lines and uses KaTeX's documented public API:

```tsx
import katex from "katex";
import "katex/dist/katex.min.css";

export default function LazyBlockMath({ math }: { math: string }) {
  let html = "";
  try {
    html = katex.renderToString(math, {
      displayMode: true,
      throwOnError: false,
      trust: true,
      strict: "ignore",
    });
  } catch {
    return <code className="font-mono text-[11px]">{math}</code>;
  }
  return <div data-testid="react-katex" dangerouslySetInnerHTML={{ __html: html }} />;
}
```

`throwOnError: false` makes KaTeX render the offending source in red instead of throwing, and the surrounding `try/catch` is the belt-and-braces guard that prevents *any* runtime in this module from blanking the screen. The `data-testid="react-katex"` attribute is preserved so existing selectors keep working. The `\htmlId{...}` annotation flow used by `panel-formula.tsx` continues to work because `trust: true` enables it (same setting `react-katex` used internally).

## Validation

- Reload `/` and `/visualizer/...` — the formula panel must render the LaTeX, no white screen, no console error from `react-katex/src/index.jsx`.
- Active-term glow (`[id^='vfx-']` selector in `panel-formula.tsx`) still highlights terms as the frame index changes.
- Production build (`bun run build`) still emits a `vendor-katex` chunk and the route bundle stays small.
