# Production-Readiness Audit — UCGLE-F1 Workbench

Tiers 1–5 of the prior plan are landed (formatting, dev-only chips, telemetry stub, error boundary, theme toggle, ChatDrawer, lazy KaTeX/Recharts/R3F). Below is a fresh audit of what's still needed to ship at production quality, ordered by complexity.

---

## Tier A — Trivial polish (under 30 min each)

1. **Surface a Chat trigger button.** `ChatDrawer` is mounted in `__root.tsx` but the only way to open it today is via `ActionsRail` ("Ask assistant") on `/`, the phase-space panel, and the visualizer context menu. There is no global affordance — add a floating bottom-right `MessageSquare` button (or header icon) wired to `useChat.setOpen(true)` so users on `/qa`, `/visualizer`, and the 404 page can reach it.
2. **Fill in remaining OG metadata.** Root layout has `og:type`/`og:title`/`og:description` but no `og:image`. Skip a root `og:image` per platform rules; add per-route `og:image` only on `/` (configurator screenshot) and `/visualizer` (panel screenshot) when assets exist. For now, add `og:url` and `twitter:title`/`twitter:description` to each route head.
3. **Hide `/qa` from production navigation.** It's already `noindex,nofollow`, but it's still reachable. Either gate the route behind `import.meta.env.DEV` in `router.tsx` or render a 404 in production. (QA harnesses don't belong on a customer build.)
4. **Replace `Math.random()` id generator** in `chat-drawer.tsx` with a single `crypto.randomUUID()` call (with a short polyfill for SSR) — already half-done; tighten it.
5. **Empty-state for `/visualizer` with no fixtures.** If `runIds` is empty, the index renders nothing. Add a small empty card pointing to `/`.

## Tier B — Small focused improvements (30–90 min each)

6. **404 + error boundary visual polish.** `NotFoundComponent` is text-only. Add the brand mark, secondary actions ("Open assistant"), and align typography with the rest of the shell. Same for `RootErrorBoundary` and the per-route error components in `visualizer.tsx`.
7. **Chat persistence.** `useChat` is in-memory only; refresh wipes the conversation. Persist `messages` + `conversationId` to `localStorage` via `zustand/middleware/persist` (skip during SSR). Add a "Clear conversation" affordance.
8. **Telemetry: wire a real provider.** `src/lib/telemetry.ts` is a console stub. Pick one (Plausible script in `__root.tsx` head, or PostHog via `posthog-js` lazy-init) gated by `VITE_TELEMETRY_KEY`. Without this you have no production visibility.
9. **Robots / sitemap.** No `public/robots.txt` or sitemap. Add `robots.txt` (allow `/`, `/visualizer`, disallow `/qa`) and a static `sitemap.xml` listing the public routes.
10. **Favicon + PWA manifest.** Confirm `public/favicon.ico` exists at proper sizes (16/32/180) and add a minimal `manifest.webmanifest` referenced from root head. Production browsers warn loudly when these are missing.
11. **Link checker pass.** Several footers/headers point to anchors or `to="/"` placeholders. Walk every `<Link>` and external `<a>` and make sure each resolves and external links have `rel="noopener noreferrer"` + `target="_blank"` where intended.
12. **Reduced-motion + prefers-color-scheme audit.** `usePrefersReducedMotion` exists; verify the phase-space `useFrame` loop, transport animations, and panel-skeleton pulse all respect it. Theme toggle exists but check `prefers-color-scheme` is the initial source of truth.

## Tier C — Medium quality bars (half-day each)

13. **Accessibility pass.** Only ~18 `aria-label`/`role` attributes across the visualizer + routes. Audit:
    - Keyboard focus rings on all custom components (sliders, chips, panels).
    - `aria-live` regions for streaming chat tokens and run progress.
    - Color contrast for `text-muted-foreground` on dark theme (currently borderline).
    - Tab order through the resizable panel groups on `/`.
    Add a one-page accessibility checklist to `docs/qa/`.
14. **Loading + error states across service calls.** Loaders throw `ServiceError`, but only some routes render `errorComponent`. Add toast.error fallbacks for `getRun`, `getVisualization`, and `getBenchmarks` failures consistently. Audit every `await loadFixture` for network-failure UX (offline mode shows blank panels today).
15. **Rate-limit / cancel for chat streaming.** `chat-drawer.tsx` has no abort controller — if the user closes the drawer mid-stream the generator keeps running. Wire `AbortController` through `sendMessage` and call it in cleanup. Also disable Send while `isStreaming`.
16. **Bundle audit pass 2.** With Tier 4 done, the visualizer entry is 85 KB but the route still pulls in `@uiw/react-codemirror` (Python language pack) eagerly via `PotentialCard`. Lazy-load CodeMirror the same way KaTeX was split. Re-run `vite build` and inventory remaining chunks > 100 KB.
17. **Image / asset optimization.** Verify `public/fixtures/**/*.json` are gzipped at the edge (they should be — Cloudflare Workers default). Inspect `wrangler.jsonc` cache headers; add long `Cache-Control: immutable` for `/_build/assets/*` and short for fixtures.
18. **Analytics for failure paths.** Currently telemetry only tracks success ("run_started", "visualization_opened"). Add `run_failed`, `visualization_error`, `chat_error`, `chunk_load_error` events so you can monitor regressions post-deploy.

## Tier D — Large / multi-touch (1–2 days each)

19. **CI + automated checks.** No `.github/workflows`, no test runner. Add:
    - `bun run typecheck` (`tsc --noEmit`)
    - `bun run lint` (already configured)
    - `bun run build`
    - Vitest with smoke tests for each route loader and service function.
    - Playwright smoke for `/`, `/visualizer`, `/visualizer/$runId` (one fixture).
    Block PRs on these.
20. **Backend wiring (Tier 6 of original plan).** The Python FastAPI orchestrator at `backend/src/ucgle_f1/m8_agent/server.py` is fully built (`/v1/chat`, `/api/runs`, `/api/benchmarks`, `/api/runs/{id}/stream`, `/api/models`). The frontend services all `void FEATURES.liveBackend` and return fixtures. Concretely:
    - Implement `httpClient.ts` wrapper with `API_BASE_URL`, retry, timeout, `ServiceError` mapping.
    - Replace each fixture branch in `services/{simulator,assistant,visualizer,artifacts}.ts` with real `fetch` / `EventSource` / `WebSocket` behind the flag.
    - Standardize SSE parsing helper for `streamRun` and `sendMessage`.
    - Document the deploy topology (frontend on Cloudflare Workers, backend wherever; CORS already `*` in dev).
21. **Authentication.** Today there is no user model. Decide: (a) keep it open for the research consortium (add IP allowlist or Cloudflare Access in front of the Worker), or (b) add Lovable Cloud auth + `user_roles` table for the assistant tool-call audit trail. Approval tokens already exist in the backend (`/api/approvals`) — the frontend never asks for them.
22. **Observability.** Beyond client telemetry: add backend request logs forwarded to a sink (Cloudflare Logpush or external), error tracking (Sentry SDK both sides), and a `/api/health` ping the frontend can show in a status chip. The `RootErrorBoundary` should `Sentry.captureException` once Sentry is wired.

## Tier E — Strategic / requires product decisions

23. **Multi-tenancy & persistence.** Runs are read-only fixtures. Production-grade means: a real run database (Postgres via Lovable Cloud), per-user run history, sharable run URLs, and lifecycle policies on visualization timelines (the 200 MB ceiling in `visualizer.ts` hints at this). Significant schema + migration work.
24. **Security review of the assistant tool-call surface.** The backend exposes `start_run`, `patch_config`, `research`, etc. via `/v1/chat` with an approval-token model. Before going public:
    - Threat-model the tool registry (can a prompt-injected LLM call `start_run` with a malicious config?).
    - Enforce per-user rate limits on `/v1/chat`.
    - Sandbox `patch.py` execution (the `dry_run` module exists; verify it's the only path).
    - Add structured audit-log review tooling.

---

## Recommended sequence

1. Tier A items 1–5 (1 hour total) — lands today.
2. Tier B 7, 8, 11 + Tier C 13, 15, 16 — visible quality wins for end users.
3. Tier D 19 (CI) before Tier D 20 (backend) so you can iterate safely.
4. Tier D 20 + 21 + 22 in one focused sprint — turns the app from "demo" into "product".
5. Tier E last, only after real usage informs the data model.

## Out of scope (already done)

- Prettier/format pass — landed.
- Dev-only chip gating, real metadata, author tag — landed.
- Toaster, theme toggle, TanStack `<Link>` migration — landed.
- ChatDrawer UI + store + fixture streaming — landed.
- RootErrorBoundary, telemetry stub, export toasts — landed.
- Visualizer bundle splitting (KaTeX / Recharts / R3F) — landed (2.2 MB → 85 KB).
