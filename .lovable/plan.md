## Issues found

### 1. Runtime crash: `Cannot destructure property 'BlockMath' from null or undefined value`

Triggered when navigating to `/visualizer/$runId` (which renders `panel-formula.tsx`), and would also crash any view using `EquationBlock` (`/`, `/qa`).

**Root cause.** `react-katex@3.1.0` ships its built bundle (`dist/react-katex.js`) with **named exports only** — `BlockMath` and `InlineMath`. There is no default export. The current code does:

```ts
import katexPkg from "react-katex";
const { BlockMath, InlineMath } = katexPkg as unknown as { … };
```

When Vite/ESM evaluates this, `katexPkg` resolves to `undefined`, and the top-level destructuring throws at module-init time — which is why the error shows up in `componentDidCatch` the moment the route mounts. The `as unknown as { … }` cast silences TypeScript but doesn't change runtime behavior.

Affected files:
- `src/components/math.tsx`
- `src/components/equation-block.tsx`

### 2. Production build failure: `Rollup failed to resolve import "@tanstack/query-core"`

`bun run build` fails because `@tanstack/react-query` imports `@tanstack/query-core` internally, but `query-core` isn't a direct dependency, so Rollup can't resolve it during the client bundle.

**Root cause.** Bun's hoisted lockfile placed `@tanstack/query-core` only inside `react-query`'s isolated `.bun/...` directory. Vite's resolver (with TanStack's dedupe config) looks for it at the top level of `node_modules/@tanstack/` and doesn't find it.

## Plan

### Fix 1 — repair the `react-katex` imports (no functionality change)

Switch both files to **named imports**, drop the `as unknown as` cast (which was masking the real shape), and lean on `@types/react-katex` (already in devDependencies) for proper types.

`src/components/math.tsx`:
```ts
import "katex/dist/katex.min.css";
import { BlockMath, InlineMath } from "react-katex";

export function Math({ tex, block = false }: { tex: string; block?: boolean }) {
  return block ? <BlockMath math={tex} /> : <InlineMath math={tex} />;
}
```

`src/components/equation-block.tsx`:
```ts
import "katex/dist/katex.min.css";
import { BlockMath } from "react-katex";
// …rest unchanged
```

This restores the visualizer's Formula panel and the configurator/QA equation cards without touching any consumer.

### Fix 2 — add `@tanstack/query-core` as an explicit dependency

Add `"@tanstack/query-core": "^5.100.1"` to `package.json` (matching the `react-query` major). It's already in the dependency graph; making it explicit lets Rollup hoist and resolve it during the production build.

No code changes — `react-query` continues to consume it transparently.

### Verification (post-implementation)

1. `bunx tsc --noEmit` — typecheck stays clean.
2. `bun run build` — production build completes.
3. Manually exercise `/`, `/visualizer`, `/visualizer/$runId`, `/qa` in the preview to confirm KaTeX renders and no boundaries fire.

### Out of scope

- No changes to component APIs, routing, store, or fixtures.
- No version bumps beyond adding the missing peer dep.
- The `@types/react-katex` definitions already cover the named export surface, so the cast is no longer needed.

## Files touched

- **edit** `src/components/math.tsx` — switch to named import, drop cast.
- **edit** `src/components/equation-block.tsx` — switch to named import, drop cast.
- **edit** `package.json` — add `@tanstack/query-core` to `dependencies`.
