# Plan — profiles, password reset, liveBackend cutover, Storage timelines

Four parallel landings on top of the auth + persistence layer that just shipped.

## 1. Profiles table + author attribution

**Migration** (`supabase/migrations/<ts>_profiles.sql`):
- `public.profiles` with `id uuid pk references auth.users on delete cascade`, `display_name text`, `handle citext unique`, `avatar_url text`, `bio text`, `affiliation text`, `created_at`, `updated_at`. Enable `citext` extension if not already.
- Trigger `on_auth_user_created_profile` (AFTER INSERT on auth.users): inserts a row with `display_name` defaulting to email local-part. Extends the existing `handle_new_user` flow — second trigger, not a rewrite.
- `touch_updated_at` reused for the `updated_at` column.
- RLS: anyone reads (`for select using (true)`); only the owner inserts/updates their own row.

**Code**:
- `src/lib/profiles.ts` — `getProfile(userId)`, `updateProfile(patch)`, `getProfilesByIds(ids[])` (batched for run cards).
- `src/components/author-badge.tsx` — avatar + display name + `@handle` chip; uses a small in-memory cache keyed on user id.
- Wire badge into the run cards on `/` and the visualizer transport bar header.
- Extend `useAuth()` with a lightweight `profile` field hydrated after sign-in (single fetch, cached).

**No /profile route this turn** — edit lives in a `<UserMenu>` dropdown "Edit profile" sheet to keep scope tight.

## 2. Password reset / `/reset-password`

Default Lovable Cloud auth emails (no domain setup).

- Add `signInWithPassword`-adjacent helper `requestPasswordReset(email)` to `src/lib/auth.tsx`:
  ```ts
  supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/reset-password`,
  });
  ```
- New route `src/routes/login.tsx` gets a "Forgot password?" link below the password field that opens an inline form (no extra route — keeps the catalog flat).
- New route `src/routes/reset-password.tsx`:
  - Public route (NOT under `_authenticated`).
  - Detects `type=recovery` in URL hash; AuthProvider's `onAuthStateChange` already swaps the session.
  - Form calls `supabase.auth.updateUser({ password })`, then redirects to `/`.
  - Empty-state if no recovery session: "This link has expired — request a new one" with link back to `/login`.

## 3. liveBackend cutover (full)

Drop the `void FEATURES.liveBackend;` no-ops and route every service through `API_BASE_URL` when set, with fixture fallback when unset (so local dev without a backend keeps working).

Shared infra (`src/lib/apiClient.ts`):
- `apiFetch(path, init)` wrapper that prefixes `API_BASE_URL`, attaches the Supabase access token (`Authorization: Bearer …`), threads `AbortSignal`, and translates non-2xx into `ServiceError` with the existing `INVALID_INPUT` / `NOT_FOUND` / etc. codes.
- `apiSse(path, signal)` async generator for SSE streams; falls back to `EventSource`-style line parsing.

Per service:
- **`src/services/simulator.ts`** — when `API_BASE_URL` is set:
  - `getBenchmarks` → `GET /api/benchmarks`
  - `getRun` → `GET /api/runs/{id}` (still goes to Postgres first via existing logic, then `apiFetch`, then fixture)
  - `listRuns` → `GET /api/runs`
  - `startRun` → `POST /api/runs` (server returns the canonical id; we still mirror to Postgres via `persistRunRow`)
  - `streamRun` → `apiSse('/api/runs/{id}/stream')`
  - `getScan` → `GET /api/scans/{id}`
- **`src/services/assistant.ts`** — `sendMessage` → `POST /v1/chat` SSE; `listModels` / `installModel` / `uninstallModel` / `getModelStatus` → REST equivalents under `/api/models`. Tool-dispatch path stays gated by `toolRegistry.ts` tier checks.
- **`src/services/artifacts.ts`** — backend artifact endpoints with the existing fixture fallback.
- **`src/services/visualizer.ts`** — see §4.

Feature flag flip in `src/config/features.ts`: `liveBackend`, `liveAssistantToolDispatch`, `liveModelManagement`, `liveVisualization` all default to `Boolean(API_BASE_URL)` (env-driven), not hard-coded `true`. This means: if `VITE_API_URL` is set, the app talks to the backend; otherwise fixtures. No more dead `void FEATURES.x;` lines.

## 4. Visualizer timelines → Storage signed URLs

`src/services/visualizer.ts` rewrite of `getVisualization`:

```text
1. Try Storage (persistence.ts already has getTimelineSignedUrl).
   - If signed URL resolves → fetch JSON → guardSize → bake → return.
2. On miss, fall back to bundled fixture under VISUALIZATION_FIXTURES.
3. Fire-and-forget backfill: if user is signed in, call
   persistVisualizationTimeline({ runId, timeline, expiresAt: now + 30d })
   so the next read is hot from Storage.
4. NOT_FOUND only when both paths miss.
```

Helpers added:
- `loadTimelineFromStorage(runId)` in `persistence.ts` — wraps `getTimelineSignedUrl` + `fetch`, parses JSON, returns `VisualizationTimeline | null`. Keeps RLS handling out of the service.
- `streamVisualization` stays fixture-driven for now (live WS path is a separate workstream).

The 200 MB `MAX_TIMELINE_BYTES` ceiling stays — it now also guards the Storage path. Manifest in `viz_timelines` (`bytes_size`, `frame_count`) lets us short-circuit oversize timelines *before* downloading, in a follow-up; not in scope this turn.

## Files

**New**
- `src/lib/profiles.ts`
- `src/components/author-badge.tsx`
- `src/lib/apiClient.ts`
- `src/routes/reset-password.tsx`
- `supabase/migrations/<ts>_profiles.sql`

**Edited**
- `src/lib/auth.tsx` (profile hydration, `requestPasswordReset`)
- `src/lib/persistence.ts` (`loadTimelineFromStorage`)
- `src/services/simulator.ts` (apiFetch wiring)
- `src/services/assistant.ts` (apiFetch + SSE)
- `src/services/artifacts.ts` (apiFetch wiring)
- `src/services/visualizer.ts` (Storage-first)
- `src/config/features.ts` (env-driven flags)
- `src/routes/login.tsx` (forgot-password link)
- `src/routes/index.tsx`, `src/components/visualizer/transport-bar.tsx` (author badges)
- `src/components/user-menu.tsx` (Edit profile sheet)

## Out of scope (called out for clarity)

- Branded auth email templates (default emails for now per your call).
- Public `/u/:handle` author pages.
- Live WS visualization streaming (`streamVisualization` stays fixture-driven).
- Manifest-driven timeline pre-flight (frame_count/bytes_size already populated; will land with the next quota work).
