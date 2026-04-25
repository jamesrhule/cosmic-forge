# UCGLE-F1 Workbench — Production Readiness Review

A ranked list of every improvement needed to take this app from "polished demo" to "ship class." Items are ordered **simplest first → most complex last** so we can land them in increments. Nothing in this plan is implemented yet — this is the audit.

The codebase is already in good shape (TanStack Start + RLS-protected Cloud, Vitest harness, error boundaries, telemetry, lazy chunks). What follows is what's missing or weak relative to a production bar.

---

## Tier 1 — Quick wins (each ≤30 min)

1. **Replace `v1.0` placeholder in footer** (`src/routes/index.tsx:130`) with a build-time injected commit SHA + build date (`__APP_VERSION__` via Vite `define`).
2. **Move `katex` extension out of `public` schema** — Supabase linter `0014_extension_in_public` warning (only finding, low severity).
3. **Tighten `runs` INSERT policy** — current policy has `WITH CHECK` blank (`authenticated users create runs`). Add `WITH CHECK (author_user_id = auth.uid())` so a signed-in user cannot insert a run owned by someone else.
4. **Tighten `tool_call_audit` INSERT policy** the same way (`WITH CHECK (user_id = auth.uid())`).
5. **Tighten `profiles` INSERT policy** (`WITH CHECK (id = auth.uid())`).
6. **`profiles are publicly readable` is `USING (true)`** — review whether email/full-name should be exposed to anonymous visitors. Likely should be limited to `authenticated` role or strip sensitive columns via a view.
7. **404 route SEO** — root `notFoundComponent` should set `<title>404 — Not Found</title>` and a `noindex` meta.
8. **Per-route social images** — `__root.tsx` has no `og:image`. Add a `/og/default.png` and per-route overrides for `/`, `/visualizer`, `/visualizer/$runId`.
9. **Robots/sitemap audit** — `public/sitemap.xml` exists; verify it lists every public route and omits `/qa`, `/auth/callback`, `/reset-password`.
10. **Strip `dev build` chip and `/qa` nav from production** — already gated by `IS_DEV`, but confirm no QA-only routes are reachable in prod (`/qa`).

## Tier 2 — Polish & correctness (≤2 h each)

11. **Loading skeletons for the configurator** — currently the `/` loader awaits `getBenchmarks()` with no Suspense fallback; first paint blocks on fixture fetch.
12. **Form validation UX** — `flattenErrors` panel at the bottom is a debug list; promote inline errors to each card and aria-live announce them.
13. **Keyboard shortcuts overlay** — `keymap-overlay.tsx` exists for the visualizer; surface a "?" trigger globally and document space/arrow keys for the transport bar.
14. **Reduced-motion audit** — `usePrefersReducedMotion` is wired; confirm every CSS animation (formula glow, R3F pulse, sonner) respects it.
15. **Color-contrast pass** — run axe on `/` and `/visualizer/:runId`; the muted `text-[11px] text-muted-foreground` lines on `bg-muted/30` likely fail AA.
16. **Focus rings everywhere** — Tailwind v4 ring tokens are configured; spot-check buttons, slider thumbs, R3F canvas overlay, dropdowns.
17. **Mobile layout for `/visualizer/:runId`** — six-panel grid is desktop-only. Either ship a mobile message or stack panels with a tab strip.
18. **Error toasts vs inline errors** — `notifyServiceError` uses sonner; on SSR it no-ops silently. Add a server-aware fallback so SSR errors still surface in the route's `errorComponent`.
19. **`console.warn`/`console.error` review** — 8 sites (`src/lib/audit.ts`, `visualizer-layout.tsx`, `katex-*`, `panel-context-menu.tsx`, `RootErrorBoundary`, `MathErrorBoundary`). Route them through `trackError` so prod bugs surface in PostHog/Plausible.
20. **`<head>` description i18n** — copy is hard-coded English; if non-English support is roadmapped, externalise to a `messages.ts`.

## Tier 3 — Test coverage & CI gates (≤1 day)

21. **Expand Vitest suite** — only 2 files exist (`katex-block.test.tsx`, `panel-formula.annotate.test.ts`). Add tests for:
    - `lib/configSchema.ts` — every defaults profile parses, invalid configs throw with field paths.
    - `lib/visualizerBake.ts` — array-length invariants and `MAX_INSTANCES` cap.
    - `lib/validity.ts` — every `level: "error"` branch.
    - `lib/equationFormatter.ts` — F1/F2 LaTeX rendering with edge values (NaN, ∞, 0).
    - `services/visualizer.ts` — `guardSize` rejects > 200 MB, `safeBake` wraps errors.
22. **Component tests** for `ActionsRail` (run flow), `RunPicker` (filtering), `TransportBar` (play/pause/scrub).
23. **Playwright smoke test** — login → configure → run → open visualizer → screenshot the six panels. Run in CI on every PR.
24. **Lighthouse CI budget** — performance ≥ 90 on `/`, accessibility = 100, SEO = 100. Fail the build on regression.
25. **TypeScript strict audit** — `rg "any\b"` returns hits in 19 files; cast to specific shapes or use `unknown` + zod.
26. **ESLint rule `no-console`** with a `warn` allowlist for the boundary classes.
27. **Dependency audit** — `bun audit` on every PR; pin major versions (currently `^` which lets minor SemVer drift in).

## Tier 4 — Observability, ops, security (≤1 week)

28. **Error reporting** — telemetry has `chunk_load_error` + `slow_frames` but no Sentry-style stack traces. Wire Sentry (or PostHog error tracking) with sourcemap upload from the Vite build.
29. **Performance budget enforcement** — `useAnimationFrame` reports slow frames; add a server-side aggregator (edge function) and a dashboard.
30. **Auth UX hardening** — sign-up flow needs:
    - Email-verification gate (don't auto-sign-in until confirmed).
    - Rate-limit `requestPasswordReset` (currently unbounded; Supabase has built-in but verify).
    - Show "session expired" toast and redirect on 401, instead of silently retrying.
31. **`claim_admin` RPC** — review server-side that it's idempotent, atomic, and only callable once. First-user bootstrap is a classic privilege-escalation vector.
32. **Storage bucket `viz-timelines`** — confirm bucket policy matches table RLS (private; signed URLs only). Add a TTL policy that purges blobs after 30 days to match `TIMELINE_TTL_DAYS`.
33. **Server-side input limits** — `MAX_TIMELINE_BYTES = 200 MB` is enforced client-side only. The RLS-protected INSERT path should reject oversized JSON server-side.
34. **CSP headers** — set strict `Content-Security-Policy` (script-src, style-src, connect-src for Supabase + Plausible + PostHog) via the SSR response. Today there is none.
35. **Security headers** — `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Strict-Transport-Security`. None are set.
36. **CORS audit** — confirm `apiClient.ts` uses correct credentials mode and the backend returns `Access-Control-Allow-Origin` only for the workbench origins.
37. **Rate limiting** — there's no app-level throttle. If `/api/*` is exposed, add edge-function quotas (per IP and per user) on `start_run` and assistant tool calls.
38. **Audit log retention** — `tool_call_audit` grows unbounded. Add a `pg_cron` job to archive rows older than 90 days and a dashboard query for admins.
39. **Health check + status page** — add `/api/public/health` returning DB ping + `cloud_status` interpretation; surface on a public `/status` route.

## Tier 5 — Deep / structural (≥1 week each)

40. **Production backend integration** — `FEATURES.liveBackend` is gated by `VITE_API_URL`. Currently empty in most builds. Land:
    - Real FastAPI endpoints for `start_run`, `getRun`, `streamVisualization` (WS).
    - Migration plan from JSON fixtures to live data.
    - Backwards-compat adapter so demo runs still work without the backend.
41. **Streaming visualization over WebSocket** — `streamVisualization` currently iterates a JSONL fixture with `setTimeout(50)`. Replace with reconnecting WS, backpressure, and graceful degradation when the connection drops.
42. **Multi-tenancy / workspaces** — current model is per-user runs. If teams are on the roadmap, add `workspace_id` to `runs` and an invite flow.
43. **Background job queue** — long-running simulations need a worker (not edge function — too short-lived). Consider Cloudflare Queues or a dedicated Python worker behind the FastAPI.
44. **Internationalisation** — i18n framework (e.g. `react-intl`) and translation pipeline if non-English audiences matter. Touches every route.
45. **Onboarding & empty states** — first-time users see no guided tour. Add a "Run your first simulation" flow with sample configs and inline tooltips.
46. **Billing / quotas** — if this becomes a SaaS, integrate Stripe (compute-minute metering) and quota enforcement upstream of `start_run`.
47. **GPU scaling for `/visualizer`** — `MAX_INSTANCES = 4096` is a soft cap. For larger timelines, swap `InstancedMesh` for `BufferGeometry` with vertex shaders, or implement frame decimation.
48. **Accessibility WCAG 2.2 AA full audit** by a third party — keyboard navigation through every six-panel layout, screen-reader narration of formula panel, motion-safe across all R3F panels.
49. **Disaster recovery** — documented runbook for: Cloud DB restore, Storage bucket re-population, secret rotation, rolling back a bad deploy.
50. **Pen test + SOC 2 readiness** — only relevant if enterprise customers are in scope. Includes audit-log immutability, data-residency controls, SSO/SAML.

---

## What's already production-grade (skip)

- TanStack Start router shell, error boundaries, lazy chunking.
- KaTeX hardening (post-recent fixes).
- RLS enabled on every `public` table with sensible owner-scoped policies.
- Vitest + RTL harness configured, FPS overlay, telemetry shim, chunk-load listener.
- `getRouter` factory creates a fresh QueryClient per request (no SSR cache leaks).
- Dev-overlay opt-in pattern.

---

## Recommended sequencing

Land **Tier 1** in one PR (low-risk hardening). **Tier 2** in two PRs (UX vs a11y). Make **Tier 3** the gate for the next deploy (no merging without green tests + Lighthouse). **Tier 4** is the "before public launch" milestone. **Tier 5** is the next quarter's roadmap.

Out of scope for this plan: implementing any of the above. This is the audit; pick which tiers you want to execute and I'll plan each one in detail.
