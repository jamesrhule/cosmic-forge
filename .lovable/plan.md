## Bug found

Session replay shows the home page (`/`) crashing with:

> Failed to parse URL from /fixtures/benchmarks.json

Dev-server log confirms the same telemetry error firing repeatedly. Root cause:

- `src/routes/index.tsx` runs `getBenchmarks()` inside its route `loader`, which executes during **SSR**.
- `getBenchmarks()` calls `loadFixture("benchmarks.json")` which does `fetch("/fixtures/benchmarks.json")`.
- Node's `fetch` (and the Worker SSR runtime) reject **relative URLs** — they require absolute. On the client this works fine; on the server it always throws.

This wasn't introduced by the recent QCompass work — it's a latent SSR bug in the fixture loader that surfaces whenever a route loader hits a fixture during SSR. `/visualizer` happens to dodge it because its loader only calls `listVisualizationRunIds()` (synchronous), but `/` and any other SSR-loader fixture call would crash.

## Fix

Single change to `src/lib/fixtures.ts`: resolve `/fixtures/...` to an absolute URL during SSR using `getRequest()` from `@tanstack/react-start/server` (the same helper already used in `src/integrations/supabase/auth-middleware.ts`). On the client, keep the relative path.

```ts
function resolveFixtureUrl(path: string): string {
  const rel = `/fixtures/${path}`;
  if (typeof window !== "undefined") return rel;
  try {
    const { getRequest } = await import("@tanstack/react-start/server");
    const req = getRequest();
    if (req?.url) return new URL(rel, req.url).toString();
  } catch { /* fall through */ }
  return new URL(rel, "http://localhost:8080").toString();
}
```

Both `loadFixture` and `loadJsonlFixture` use this helper.

### Why this is safe
- The dynamic import of `@tanstack/react-start/server` is wrapped in a `typeof window !== "undefined"` guard, so the browser bundle never resolves the server-only module.
- Behaviour on the client is byte-identical (still a relative `/fixtures/...` fetch).
- All seven existing call sites (`getBenchmarks`, `getRun`, `getScan`, visualizer fixtures, models.json, formulas) flow through the same helper — fixed once.

### Verification
1. `bunx tsc --noEmit`
2. `bun run build`
3. Reload `/` — Configurator renders without the error overlay; benchmarks load.
4. Confirm `/visualizer` and `/visualizer/$runId` still work (they already did).
5. Tail dev-server log: no more `Failed to parse URL from /fixtures/...` lines.

No other files change. No migrations. No new dependencies.
