## Two issues found while sweeping the project

### Issue 1 (blocking): SSR error on `/visualizer/:runId`

Hitting `/visualizer/kawai-kim-natural` returns 200 to the browser but the SSR pipeline throws:

> Error: No QueryClient set, use QueryClientProvider to set one
> at useQueryClient (panel-formula.tsx:44)

`src/components/visualizer/panel-formula.tsx` calls `useQuery(...)` to fetch `formulas/F1-F7.json`, but **no `QueryClientProvider` exists anywhere in the tree** — `src/router.tsx` doesn't construct a `QueryClient` and `src/routes/__root.tsx` doesn't render the provider. React swallows the SSR throw and falls back to client-side render, so the URL "works" but the formula panel silently fails on every visualizer load.

### Issue 2 (cosmetic): `timeline_sign_failed` telemetry on anonymous visualizer reads

`src/services/visualizer.ts → loadTimelineFromStorage()` always tries to sign a URL from the `viz-timelines` bucket before falling back to fixtures. For signed-out users, RLS rightly rejects the sign, which is logged as `service_error / timeline_sign_failed`. Functionality is correct (fixture fallback runs), but the noise is misleading. Demote to debug-level / suppress the log when the cause is "no row exists yet".

## Fix

### `src/router.tsx`
- Construct a fresh `QueryClient` inside `getRouter()` (never at module level — that would leak SSR cache between requests).
- Pass it through router `context: { queryClient }` and update the root route to be `createRootRouteWithContext<{ queryClient: QueryClient }>()`.

### `src/routes/__root.tsx`
- Switch `createRootRoute` → `createRootRouteWithContext<{ queryClient: QueryClient }>()`.
- Wrap `<Outlet />` (and the rest of the app shell) with `<QueryClientProvider client={queryClient}>` reading `queryClient` from `Route.useRouteContext()`.

### `src/lib/persistence.ts`
- In `getTimelineSignedUrl`: stop calling `trackError` when the storage error is a benign "object not found" / RLS rejection. Keep the telemetry for genuine failures (network, auth misconfiguration). Concretely: only `trackError` when `error.message` does not match `/not found|object not found|404/i`.

## Verification
1. `bunx tsc --noEmit` — clean
2. `bun run build` — clean
3. `curl /visualizer/kawai-kim-natural` — no `No QueryClient set` in dev-server log
4. Curl every route (`/`, `/visualizer`, `/visualizer/$runId`, `/login`, `/reset-password`, `/qa`, `/auth/callback`) — all 200 after redirect, no new SSR errors in logs
5. Open the visualizer in the browser — formula panel renders KaTeX (was silently empty before)

No new dependencies. No migrations. No public API changes — only one router-context type changes, and the only file reading that context is the root route.
