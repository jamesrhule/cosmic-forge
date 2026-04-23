
# Configurator View — Implementation Plan

Replace the demo content on `src/routes/index.tsx` with the spec'd three-column resizable Configurator. Service layer, types, and shared components are already in place; this pass adds the form, computed previews, action panel, and the supporting building blocks they need.

## File changes

### New files
- **`src/lib/configDefaults.ts`** — `defaultsForPotential(kind)` returns sensible param + coupling defaults; `kawaiKimDefaults()` returns the V2 baseline `RunConfig`; helper to build a starting `RunConfig`.
- **`src/lib/configSchema.ts`** — Zod schema mirroring `RunConfig` (potential discriminated by `kind`, sci-notation numerics, θ_grav ∈ [0, 2π], precision enum). Used by RHF resolver.
- **`src/lib/configYaml.ts`** — Minimal hand-rolled YAML serializer for `RunConfig` (no new dep) used by Export config.
- **`src/lib/equationFormatter.ts`** — `renderF1WithValues(config)` returns a LaTeX string for the F1 boxed equation with substituted ξ, θ_grav, S_E2, M₁, f_a, M⋆ rendered via `formatSci`.
- **`src/lib/potentialEvaluator.ts`** — Pure JS evaluators for the three built-in potentials (Starobinsky, natural, hilltop) sampling V(Ψ) over a Ψ range. For `custom`, returns `null` (chart shows "preview unavailable for custom potential — backend will compute").
- **`src/components/client-only.tsx`** — `<ClientOnly>` wrapper using `useIsMounted` to gate SSR-incompatible children (CodeMirror).
- **`src/components/sci-input.tsx`** — Controlled numeric input that accepts `8.5e-3`, `1e16`, etc., shows formatted scientific value below, validates against min/max, integrates with RHF via Controller.
- **`src/components/log-slider.tsx`** — Log-scale slider built on `@/components/ui/slider` for ξ (10⁻⁵ to 10⁰); displays current value via `<Sci>`.
- **`src/components/angle-slider.tsx`** — 0..2π slider for θ_grav with degree readout and π-fraction labels.
- **`src/components/potential-editor.tsx`** — `<ClientOnly>`-wrapped CodeMirror 6 (`@uiw/react-codemirror` + `@codemirror/lang-python` + `@codemirror/theme-one-dark` in dark mode). Read-only lint markers from `lintPotentialSnippet`. Min height 220px, monospace, line numbers.
- **`src/components/potential-preview-chart.tsx`** — Recharts line chart of V(Ψ) using `potentialEvaluator`; "preview unavailable" placeholder for custom.
- **`src/components/validity-light.tsx`** — Traffic-light pill (green/amber/red) plus popover listing per-field issues from `checkConfigValidity`.
- **`src/components/cost-badge.tsx`** — Estimated CPU-minute badge derived from precision + couplings (deterministic mock).
- **`src/components/configurator/PotentialCard.tsx`** — Card 1: radio for `PotentialKind`, conditional param fields (Starobinsky M; Natural f, Λ⁴; Hilltop μ, p; Custom → `<PotentialEditor>` + KaTeX preview of declared `V(ψ)`).
- **`src/components/configurator/CouplingsCard.tsx`** — Card 2: ξ via log-slider + sci input, θ_grav via angle-slider, f_a / M⋆ / M₁ / S_E2 via `<SciInput>`.
- **`src/components/configurator/SeesawCard.tsx`** — Card 3: M₁, S_E2 (mirrored — single source of truth on form), with hint text about M₁ scale and S_E2 ranges.
- **`src/components/configurator/ReheatingCard.tsx`** — Card 4: Γ_φ, T_reh (sci inputs) + precision radio (`fast | standard | high`).
- **`src/components/configurator/ActionsRail.tsx`** — Right rail: Run simulation (calls `startRun` → toast with runId), Load from benchmark (opens Sheet listing `BenchmarkIndex`, click loads), Export config YAML (download via Blob), Ask assistant (adds config context chip via `useChat.addContext` + opens drawer).

### Replaced files
- **`src/routes/index.tsx`** — Becomes the Configurator. Loader fetches `getBenchmarks()` and exposes via `useLoaderData`; component renders the slim header (existing wordmark + static-mode pill), then a `ResizablePanelGroup` with three panels: Left (`360px`, four collapsible cards), Center (F1 equation with substituted values, V(Ψ) chart, cost badge, validity light), Right (sticky `ActionsRail`). RHF `useForm<RunConfig>` with Zod resolver, default values from `kawaiKimDefaults()`. Form state piped to center previews via `watch()`. Below 1024px: shows "Designed for wide screens" card.

### Touched files
- **`src/store/ui.ts`** — Add `lastSubmittedConfig` slice (optional convenience for ActionsRail → assistant chip). No breaking changes.

## Technical details

- **No new deps.** Recharts, KaTeX, RHF+Zod, CodeMirror packages, react-resizable-panels, sonner are already installed.
- **SSR safety:** CodeMirror loads only inside `<ClientOnly>`; route loader pure-fetches a JSON fixture; no `window` access in module scope.
- **Form architecture:** Single `useForm<RunConfig>`; cards are presentational, consume `control` via prop. Validation surfaces via `<ValidityLight>` (semantic check) AND Zod field errors (input-level). Run button disabled when Zod invalid OR validity is `error`.
- **F1 substitution:** `renderF1WithValues` swaps numeric placeholders into `\boxed{η_B = N · ξ · θ_grav · ⟨RR̃⟩ · (S_E2 · M₁)/(f_a · M⋆²)}`, scientific notation via `\times 10^{n}`. Re-rendered on form change (debounced via `useDeferredValue`).
- **Export YAML:** Serializes the current `RunConfig` (including `customPython` when kind=custom) to a deterministic YAML, downloads as `ucgle-config-{timestamp}.yaml`.
- **Benchmark sheet:** `<Sheet>` from `ui/sheet`, lists each `BenchmarkEntry` with arxiv link + expected η_B; click calls `form.reset(entry.config)` and toasts.
- **Ask assistant:** Pushes `{ kind: "config", label, config }` chip to `useChat`, calls `setOpen(true)`. Drawer itself isn't built yet — the chip persists; opening currently surfaces the existing minimal placeholder (drawer build is a later pass).

## Layout sketch

```text
┌─ header ─────────────────────────────────────────────────────────────┐
├──────────────┬──────────────────────────────────┬──────────────────┤
│ Potential V  │  F1 (with substituted values)    │  ▶ Run sim       │
│ Couplings    │  V(Ψ) chart                      │  ☰ Benchmarks    │
│ Seesaw       │  cost badge · validity light     │  ⤓ Export YAML   │
│ Reheating    │                                  │  ✦ Ask assistant │
└──────────────┴──────────────────────────────────┴──────────────────┘
```

## Out of scope (this pass)
- Chat drawer UI, Control view, Research view — separate passes per the original plan.
- Real Python execution / true potential AST validation (still stubbed).
- Mobile layout beyond the "wide screens" card.
