
# UCGLE-F1 Workbench — Frontend Shell

A typed, fixture-backed research UI for a gravitational-leptogenesis simulator. Three integrated views, an AI assistant drawer, and a model manager — all wired through a service layer that's ready for a real backend to drop in.

## Stack adjustments
- **Routing**: TanStack Start file-based routes under `src/routes/`. Loaders call the service layer; components consume `useLoaderData`. Routes: `index.tsx` (Configurator), `runs.tsx` (list layout), `runs.index.tsx`, `runs.$id.tsx`, `research.tsx`.
- **Editor**: CodeMirror 6 (`@uiw/react-codemirror`, `@codemirror/lang-python`) inside a `<ClientOnly>` boundary. Read-only lint decorations driven by `src/lib/potentialValidator.ts` stub.
- Everything else per spec: Tailwind + shadcn, TanStack Query, Zustand, RHF+Zod, KaTeX, Recharts, react-markdown+remark-gfm, lucide.

## Service layer (the contract)
`src/services/{simulator,assistant,artifacts}.ts` — every function async, fully typed, JSDoc'd with the intended backend endpoint (e.g. `POST /api/runs`, `WebSocket /ws/assistant`). Streams implemented as async generators reading `.jsonl` fixtures with ~200ms delays. `ServiceError` with `.code`. Feature flag `FEATURES.liveBackend = false` in `src/config/features.ts`; `VITE_API_URL` read but unused.

`src/types/domain.ts` — every type from the spec verbatim.

## App shell
- Sticky top nav (h-14): wordmark, mode pill, center tabs (Configurator/Control/Research), chat toggle with unread dot, "static mode" backend status, theme toggle, GitHub link.
- ⌘K command palette (jump to run, switch tab, open benchmark, ask assistant, install model).
- Right-side resizable chat drawer (450px, 360–720px range), persists across routes via Zustand.
- Footer (h-8): build SHA · fixture badge · loaded-run count · citation.

## View 1 — Configurator (`/`)
Three-column resizable. **Left** (360px): four collapsible RHF+Zod cards — Potential V(Ψ) (radio + Custom→CodeMirror + KaTeX preview), GB/CS Couplings (sci-notation + log slider for ξ + 0–2π for θ_grav), Seesaw Sector (with hint text), Reheating & Precision. "Restore V2 defaults" loads Kawai-Kim fixture. **Center**: KaTeX boxed F1 equation with substituted values, V(Ψ) line chart, cost badge, validity traffic-light from `src/lib/validity.ts`. **Right** (sticky): Run simulation, Load from benchmark (Sheet), Export config (YAML download), Ask assistant (opens drawer with config pre-attached).

## View 2 — Control (`/runs`, `/runs/$id`)
**Left** (400px): virtualized run list with status chips (queued/running/completed/failed/canceled), multi-select for compare. **Right tabs**: Overview (η_B hero, S1–S15 verdict strip, V1–V8 recovery matrix, config readout, Ask assistant), Modules (M1–M7 timing waterfall + convergence panels), Live (SSE-style log viewport from `streamRun` generator, per-module progress, k-mode + Bogoliubov-drift gauges, Cancel toast), Artifacts (table + Download triggers browser save). **Compare mode** (≥2 selected): config diff with delta highlighting, η_B/F_GB/audit-pass diff badges, overlaid SGWB spectra, "Ask assistant to compare".

## View 3 — Research (`/research`)
Four secondary tabs: **Equation Gallery** (F1–F7 cards with cleanness score, KaTeX boxed eqs, expand→Sheet with S-checks; F1 has "Primary" ribbon), **Parameter Scan Explorer** (custom-SVG ξ×θ_grav heatmap, perceptually-uniform scale centered on 6.1×10⁻¹⁰, Planck contour, axis-swap/log toggles, click-to-load), **Benchmark Recovery Matrix** (V1–V8 × loaded runs, click→comparison Sheet), **Citations & Export** (papers list with Copy BibTeX, Cite this app, Export ZIP stub).

## AI assistant drawer
Header: model picker (installed-ready models + "Manage models…"), New conversation, overflow menu. Context strip with attached chips (RunConfig, runs, benchmark) driven by Zustand. Virtualized message list, role-distinguished avatars, streaming token render from `AssistantEvent`, markdown + KaTeX + code highlight. Tool-call cards (collapsible args/result, Apply button no-op toast) for all 9 tool names — one fixture transcript per tool. Input: multiline textarea, shift+enter newline, shortcut chips (Explain run / Compare selected / Suggest parameters / Cite). Status line: model, streaming indicator, token count, stop button.

## Model manager (modal from chat header)
Two tabs. **Catalog**: filterable grid (provider, format, size, tags, search) of `ModelDescriptor` cards with Recommended ribbons and Install→async generator progress (concurrent installs in stacked toasts). **Installed**: table with Set as default + Uninstall (confirm dialog). Catalog fixture: Llama-3.1-8B-Instruct-Q4, Qwen2.5-14B-Instruct-Q4, Mistral-7B-Instruct-Q5, BYO API, plus code- and math-specialty models — plausible sizes/licenses/tags.

## Shared components (`src/components/`)
`<Sci>`, `<EquationBlock>`, `<VerdictChip>`, `<UncertaintyBar>`, `<SGWBPlot>`, `<BogoliubovGauge>`, `<ParameterHeatmap>`, `<ArxivLink>`, `<ContextChip>`, `<ModelBadge>`, `<ToolCallCard>`.

## Fixtures (`/public/fixtures/`)
`benchmarks.json`, `runs/{kawai-kim-natural,starobinsky-standard,gb-off-control,failing-run}.json`, `scans/xi-theta-64x64.json`, `formulas/F1-F7.json`, `events/run-kawai-kim.jsonl`, `events/install-llama-8b.jsonl`, `chat/transcripts/*.jsonl` (one per tool), `models.json`, sample `artifacts/`. All numbers internally consistent.

## Quality bars
Strict TS, zero `any`, JSDoc endpoints on every service fn, Skeleton loaders, arXiv links new-tab, keyboard accessible, self-hosted Inter + JetBrains Mono in `/public/fonts`, light/dark via Tailwind class strategy with single indigo #4338ca accent, works to 1024px (narrower → "Designed for wide screens" card with phone summary).

## README
**Running the shell** + **Handoff to Claude Code** checklist: every service function with its target endpoint, every tool name, every fixture file, every feature flag, intended real backend behavior for each.

## Explicitly out of scope
No real HTTP/SSE/WS, no LLM, no model downloads, no Python execution, no auth, no mobile-first layouts, no perf optimization.
