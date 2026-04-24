# Frontend Ship-Readiness — KaTeX, Tests, Formula UX, Perf Guard, Type Audit

Five small, independent improvements that complete the frontend polish pass before ship.

---

## 1. KaTeX error fallback hardening

Today `katex-block.tsx` and `katex-inline.tsx` already wrap `renderToString` in `try/catch` and fall back to a `<code>` block. Two gaps remain:

- The fallback gives no signal that something failed — users see raw LaTeX with no hint why.
- The lazy-import itself isn't guarded. If the dynamic chunk ever 404s (deploy race, network blip), the `<Suspense>` fallback in `math.tsx` keeps showing the raw LaTeX forever with no recovery.

Changes:

1. **`src/components/lazy/katex-block.tsx` / `katex-inline.tsx`** — when `renderToString` throws or KaTeX emits its red error span, render the raw LaTeX inside a styled `<code>` with `title="Failed to render LaTeX"` and `data-katex-fallback="true"`. Detect the KaTeX error sentinel (`html.includes('class="katex-error"')`) and treat it as a render failure for the fallback path too. Log once per session via `console.warn` (guarded by a module-level `Set` of seen sources) so we don't flood logs in dev.
2. **`src/components/math.tsx`** — wrap the `<Suspense>` in a small `MathErrorBoundary` (new file: `src/components/lazy/math-error-boundary.tsx`) that catches chunk-load errors from `lazy()` and renders the same fallback `<code>`. This is the missing safety net for the "vendor-katex chunk failed to load" case.
3. Keep the `data-testid="react-katex"` attribute (existing selectors still pass).

---

## 2. Math rendering tests

No test runner is installed. Add Vitest with the minimal config needed to cover the math pipeline.

Changes:

1. **Install dev deps**: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`.
2. **`vitest.config.ts`** — `environment: "jsdom"`, alias `@` → `src`, setup file that imports `@testing-library/jest-dom`.
3. **`package.json`** — add `"test": "vitest run"` and `"test:watch": "vitest"`.
4. **`src/components/lazy/__tests__/katex-block.test.tsx`** — three cases:
   - Renders simple `E = mc^2` to a div containing `.katex` HTML.
   - Renders an `\htmlId{vfx-xi}{\xi}` term and asserts `id="vfx-xi"` is in the output (formula-glow contract).
   - Pathological input (e.g. `\fakecommand{`) does NOT throw and produces either a `katex-error` span or the `data-katex-fallback` `<code>`.
5. **`src/components/visualizer/__tests__/panel-formula.annotate.test.ts`** — extract `annotateLatex` from `panel-formula.tsx` into `src/lib/annotateLatex.ts` (pure function, no React) and unit-test:
   - Longest-first ordering: `M_\star^2` is wrapped before `M_1`.
   - Unknown term IDs are silently skipped.
   - Multiple occurrences: only the first is wrapped (current behavior — assert it so a future change is intentional).
6. Update `panel-formula.tsx` to import from the new module.

These tests pin down the contracts that broke twice already (KaTeX named-exports, formula-glow IDs).

---

## 3. Formula panel UX polish

The formula panel works but feels under-finished compared to the other panels.

Changes (all in `src/components/visualizer/panel-formula.tsx`):

1. **Copy LaTeX button** in the header (mirror `EquationBlock`'s pattern): `Copy` icon → toggles to `Check` for 1.5s, copies the un-annotated `formula.latex`. Hidden until hover, `aria-label="Copy LaTeX"`.
2. **Active-term legend** — when `activeTerms.size > 0`, render a row of small chips below the formula, one per active term ID, styled with the same indigo accent as the glow. Click a chip to scroll its `[id^='vfx-']` node into view (`scrollIntoView({ block: "nearest" })`). Helps users connect timeline events to formula terms.
3. **Reduced-motion respect** — gate the `formula-glow` keyframe behind `prefers-reduced-motion: no-preference` via a Tailwind `motion-safe:` variant on the `[data-active='true']` class chain. Currently the animation runs unconditionally.
4. **Empty-state copy** — when `formula` resolves but `termIds` is empty, show a one-line muted hint: "No annotated terms for this variant." (right now the panel renders the formula with zero glow targets and no explanation).

---

## 4. Render performance guard

`useAnimationFrame` runs the transport loop. We have no in-app signal when the visualizer drops frames — a regression in `panel-phase-space` or `panel-sgwb` would only be caught manually.

Changes:

1. **`src/hooks/useAnimationFrame.ts`** — add an optional `onSlowFrame?: (dtMs: number) => void` callback, fired when `dt > 33` (≈ <30fps) more than 5 times in a 2s window. Implement with a small ring buffer in the effect.
2. **`src/lib/telemetry.ts`** (existing) — add `reportSlowFrames(panel: string, count: number, p95Ms: number)` that POSTs to the existing telemetry sink in production and `console.debug`s in dev.
3. **`src/components/visualizer/visualizer-layout.tsx`** — wire the master transport loop's `onSlowFrame` to `reportSlowFrames("transport", …)`. Aggregate within a 10s window before reporting so we don't spam.
4. **`src/components/dev/chart-size-overlay.tsx`** is the existing dev overlay — add a sibling `src/components/dev/fps-overlay.tsx` (gated by `import.meta.env.DEV` AND `localStorage.getItem("vfx:fps") === "1"`) that shows current FPS and slow-frame counter in the bottom-right. Off by default; opt-in for QA passes.

No production UI change. This gives us a real guard rail before ship.

---

## 5. Visualizer types audit

`src/types/visualizer.ts` is the wire contract with the simulator. A pre-ship audit + light tightening:

1. **`SgwbSnapshot`**, **`AnomalyIntegrandSample`** — assert array-length invariants in a new `src/lib/visualizerSchema.ts` Zod schema (`f_Hz.length === Omega_gw.length === chirality.length`, same for anomaly's `k` / `integrand` / `running_integral`). Run it inside `bakeTimelineBuffers` in dev only (`if (import.meta.env.DEV)`); throw a clear error pointing at the offending frame index. Today a mismatched array silently corrupts the SGWB chart.
2. **`VisualizationFrame.active_terms`** — document and enforce that values are formula term IDs without the `vfx-` prefix (matches what `panel-formula.tsx` strips). Add a unit test in step 2's suite.
3. **`FormulaVariant`** — add a `FORMULA_VARIANTS` const array exported from `types/visualizer.ts` (`["F1","F2",…,"F7"] as const`) so `formulas/F1-F7.json` consumers and the run-picker can iterate without a hand-maintained list. Update `panel-formula.tsx` and `src/lib/fixtureSchemas.ts` to use it.
4. **`BakedTimelineBuffers.maxModes`** — add a JSDoc note that this is the hard cap for the R3F `InstancedMesh` instance count and should be checked against `MAX_INSTANCES` in `panel-phase-space.tsx` (add the assertion; today an oversized timeline would crash the GPU draw call with a cryptic Three.js error).
5. **README touch-up** in `docs/qa/` — one short markdown file `docs/qa/visualizer-contract.md` summarizing the wire shape and the dev-only invariants for the backend team.

---

## Files touched (summary)

- New: `src/components/lazy/math-error-boundary.tsx`, `src/lib/annotateLatex.ts`, `src/lib/visualizerSchema.ts`, `src/components/dev/fps-overlay.tsx`, `vitest.config.ts`, `vitest.setup.ts`, `src/components/lazy/__tests__/katex-block.test.tsx`, `src/components/visualizer/__tests__/panel-formula.annotate.test.ts`, `docs/qa/visualizer-contract.md`.
- Edited: `src/components/lazy/katex-block.tsx`, `src/components/lazy/katex-inline.tsx`, `src/components/math.tsx`, `src/components/visualizer/panel-formula.tsx`, `src/components/visualizer/visualizer-layout.tsx`, `src/components/visualizer/panel-phase-space.tsx`, `src/hooks/useAnimationFrame.ts`, `src/lib/telemetry.ts`, `src/lib/visualizerBake.ts`, `src/lib/fixtureSchemas.ts`, `src/types/visualizer.ts`, `package.json`.

## Out of scope

- No backend / Supabase changes.
- No new routes or auth changes.
- No visual redesign — only the formula panel additions described above.
