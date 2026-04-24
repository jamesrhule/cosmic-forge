# UCGLE-F1 Workbench — Production-Readiness Audit

The app is a fixture-backed scientific workbench (Configurator → Visualizer → QA harness) on TanStack Start. Build is **green**, typecheck is **clean**, no runtime errors, no console noise. Below is every gap to ship-ready, ordered low-to-high complexity.

---

## Tier 1 — Trivial polish (minutes, low risk)

1. **Run `prettier --write .`** — lint reports ~80 Prettier-only errors across routes/services. No logic, just formatting; one command.
2. **Fix author/branding meta in `__root.tsx`** — title/description still say "Lovable App" / "Lovable Generated Project". Replace with "UCGLE-F1 Workbench" + real description; `name="author"` should be the project owner, not "Lovable".
3. **Remove `"static-shell"` / `"fixture mode"` chips and footer build string** before production OR gate them behind `import.meta.env.DEV`. Ship-shaming chips on the live header look unfinished.
4. **`/qa` discoverability** — `<meta name="robots" content="noindex,nofollow">` is correct; also remove the visible `/qa` link from the Configurator header in production builds (keep it dev-only).
5. **Restore-defaults toast typo** — copy says "Restored V2 (Kawai-Kim) defaults" but the button label says "Restore V2 defaults"; align wording.

## Tier 2 — Small UX cleanups

6. **Active-state symmetry on QA header** — the `/qa` Visualizer link is missing `activeOptions={{ exact: true }}` (line 81 of `qa-shell.tsx`); the QA pill is a `<span>` rather than a `Link` with active style — make it consistent with the other two headers.
7. **Sonner toaster mounted only on `/`** — `<Toaster />` lives in `index.tsx` only. Toasts fired from the visualizer (export PNG, copy formula) or QA never appear. Move to `__root.tsx` so it renders on every route.
8. **Theme toggle is dead** — `useTheme` store exists with persist + `applyTheme`, but no UI control toggles it. Either add a header button or remove the store.
9. **`NarrowScreenGate` traps mobile users on `/`** — copy says Control/Research "ship in later releases" but they exist at `/qa`. Update copy to point users at `/visualizer` (which renders on mobile) and `/qa` for inspection.
10. **Replace raw `<a href="/">` in the global error boundary** (`router.tsx` line 47) with TanStack `<Link>` for client-side navigation; otherwise a recoverable error forces a full page reload.

## Tier 3 — Connect the assistant UI (medium)

11. **No chat surface is mounted anywhere.** `useChat` store is fully built; `ActionsRail` ("Ask assistant"), `panel-context-menu` ("Pin frame to assistant"), and `panel-phase-space` all push context chips into the store, but **nothing reads `chat.open`** to render a drawer/panel. Either:
    - build a minimal `<ChatDrawer />` component (Sheet + message list + input + chip strip + model picker) and mount it in `__root.tsx`, wiring it to `services/assistant.sendMessage`, OR
    - hide the "Ask assistant" / "Pin to assistant" affordances until that surface ships.
    Today every "Ask assistant" click silently no-ops past a toast — the single biggest UX trap.
12. **Model manager is similarly orphaned** — `chat.modelManagerOpen` + `services/assistant.installModel/listModels/etc.` exist with no UI. Same choice: build it or hide the entry point.

## Tier 4 — Bundle and performance

13. **`visualizer.$runId.lazy` chunk is 2.22 MB** and the eager `slider`/`validity`/`worker-entry` chunks are 1.6 / 1.1 / 0.7 MB. Vite is warning. Concrete wins:
    - lazy-load `react-katex`/`katex` only inside `panel-formula.tsx` and `equation-block.tsx` via `React.lazy` (currently eager in the visualizer chunk).
    - lazy-load `recharts` panels (`panel-sgwb`, `panel-anomaly`, `panel-gb-window`, `panel-lepton-flow`) — each is independent.
    - lazy-load `@react-three/fiber` + `three` + `drei` only when `PhaseSpaceCanvas` actually mounts.
    - confirm `@codemirror/*` (currently in deps but unused in the audit) is tree-shaken; remove if unused.
14. **Drop unused Radix primitives** — `package.json` ships menubar, navigation-menu, hover-card, aspect-ratio, context-menu, etc. Audit which are actually imported (`grep -r "@radix-ui/react-..."`) and prune. Each shaves 5–30 kB.
15. **Visualizer 200 MB timeline ceiling is silent until breach** — show the size on the run-picker card so users know before clicking. Currently `getVisualization` throws only after the fetch.

## Tier 5 — Robustness and observability

16. **No global ErrorBoundary inside `RootComponent`** — TanStack's `defaultErrorComponent` catches loader/render errors, but uncaught errors inside event handlers (e.g. inside a chart resize callback or the rAF loop) will white-screen. Add a React error boundary inside `RootShell`.
17. **`exportFirstCanvas` and `panel-context-menu` PNG export silently warn to console** on failure. Surface a toast instead so users know the click did nothing.
18. **Visualizer transport URL sync sets `replace: true` per 150 ms** — fine — but `currentFrameIndex` flushes happen on every store change including programmatic seeks. Skip the URL flush during the initial seed (`seededRef`) and during rAF play to avoid history churn on tab reload during playback.
19. **No telemetry / analytics hook** — for production you typically want at least pageview + run-started + visualization-opened events. Add a thin `track()` wrapper in `src/lib/` that no-ops by default and is wired at three call sites (`/`, `/visualizer/$runId` mount, `startRun`). Keeps it provider-agnostic.
20. **Per-route SEO is partial** — `/visualizer/$runId` has `og:title`/`og:description` but no `og:image`. Bake a static social card (or render one server-side from the timeline thumbnail) and wire it; without it, shared run links look generic.

## Tier 6 — Backend integration (largest)

21. **Flip `FEATURES.liveBackend` and wire the service layer to a real API.** Every function in `src/services/{simulator,visualizer,assistant,artifacts}.ts` is a fixture stub with the intended endpoint already documented in JSDoc. Work order:
    1. `getBenchmarks`, `listRuns`, `getRun` (read-only) → switch first to validate `VITE_API_URL` plumbing.
    2. `startRun` + `streamRun` (SSE/WebSocket) → introduces real auth + run lifecycle.
    3. `getVisualization` + `streamVisualization` → largest payloads; needs CDN/range-request strategy.
    4. `assistant.sendMessage` + `installModel` → only after the chat UI from Tier 3 ships.
    Each step needs a Zod parser at the boundary so a backend drift fails loudly instead of corrupting state.
22. **Authentication / users / RLS** — currently no auth at all. If runs are user-owned, enable Lovable Cloud, add a `user_roles` table per the role pattern, gate `/visualizer/$runId` and `startRun` behind `auth.uid()`. Without this, the live backend exposes every run to every visitor.
23. **Artifact downloads use `fetch('/fixtures/artifacts/…')`** which only works while fixtures ship in `/public`. Replace with presigned URLs from the backend (`GET /api/runs/{id}/artifacts/{name}`) returning a 302 to S3/R2; update `downloadArtifact` to follow that redirect or stream the body.
24. **CI quality gate** — add a GitHub Action (or equivalent) running `bun run build`, `tsc --noEmit`, `eslint .`, and `prettier --check .` on every PR. The current lint/format drift would have been caught automatically.

---

## Suggested first wave (1–10) is purely frontend, low-risk, ~half a day total.
The chat surface (Tier 3) is the single biggest user-visible gap.
Bundle work (Tier 4) is the biggest perf win.
Backend wiring (Tier 6) is the actual road to "production".

Approve any subset (e.g. "do Tiers 1–2 now") and I'll implement.
