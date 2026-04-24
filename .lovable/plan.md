# Auth + persistence cutover

Goal: land a real user identity (email/password + Google), give every authenticated user a default `viewer` role with admin self-grant for the seed user, then flip `FEATURES.persistRuns` on and migrate the three list/get/start hooks in `services/simulator.ts` over to the new Postgres tables. Fixtures stay as a fallback so the existing public catalog still renders for signed-out visitors.

## What you'll see

- A new **Sign in** button in the chrome (header on `/`, transport bar on `/visualizer`). Anonymous browsing of the public catalog still works.
- A new `/login` route with email/password + "Continue with Google".
- A new `/auth/callback` route that consumes the OAuth redirect and bounces back to wherever you came from.
- After signing in: an **author chip** showing your email, a **Sign out** action, and (for the admin) a small "Admin" badge.
- The runs list on `/` and the run picker on `/visualizer` start serving from Postgres. If a row isn't there yet (cold DB), the fixture is returned and quietly upserted in the background so future visits hit the database.
- "Start run" persists a row and flips its status as the (still-fixture) stream completes — visible in the audit log and as a real entry in the runs table.

Everything else (chat, visualizer panels, audit panel) is untouched.

## Steps

### 1. Auth schema + seed (migration)

- Confirm `app_role` enum has `viewer | researcher | admin` (already created in the previous turn — verify before re-defining).
- Add a trigger on `auth.users` insert that grants every new user the `viewer` role in `public.user_roles`. Self-service writes/reads still gate on RLS.
- No `profiles` table this turn — we don't need a display name yet; the chrome shows `auth.user.email`. (Easy to add later.)
- Seed admin: a one-shot SQL helper `public.claim_admin(email text)` (security definer) that, when called by a signed-in user matching that email, inserts an `admin` row for them. We'll call it once from the browser after first login.

### 2. Auth wiring (frontend)

- `src/lib/auth.tsx` — a tiny React context exposing `{ user, session, roles, signInWithPassword, signUp, signInWithGoogle, signOut, hasRole }`. Subscribes to `supabase.auth.onAuthStateChange` (set up before `getSession` per Lovable Cloud rule). Roles are fetched once per session from `user_roles`.
- `src/routes/__root.tsx` — wrap `<Outlet />` in `<AuthProvider>`. No route guard at root: the catalog is public.
- `src/routes/login.tsx` — email/password form + Google button (uses `lovable.auth.signInWithOAuth("google", { redirect_uri: window.location.origin + "/auth/callback" })`). Validates with `validateSearch` for `?redirect=`. If already signed in, `beforeLoad` redirects to the saved location.
- `src/routes/auth.callback.tsx` — minimal route that waits for the session to settle then `navigate({ to: search.redirect ?? "/" })`.
- A small `<UserMenu />` component (avatar/email + Sign out) rendered in the existing chrome on `/` and in `transport-bar.tsx`.

Email confirmation stays on (Lovable Cloud default). No password-reset flow this turn — explicitly out of scope.

### 3. Flip persistence + migrate the three service calls

- `src/config/features.ts` → `persistRuns: true`. `auditToolCalls` already true.
- `src/services/simulator.ts`:
  - `listRuns()` — query `runs` ordered by `created_at desc, limit 50`. Merge with fixture list by id (fixtures fill any slot not yet in Postgres so the public catalog never looks empty during cold start).
  - `getRun(id)` — try `runs` + `run_results` join first (RLS handles visibility). If miss and id is a known fixture key, return the fixture **and** fire-and-forget `persistRunRow` + `persistRunResult` + `persistAuditReport` so the next read is hot. Signed-out users skip the upsert.
  - `startRun(config)` — generate a real id (`crypto.randomUUID()`), `persistRunRow({ id, config, status: "queued", visibility: "public" })`, then return `{ runId: id }`. If unauthenticated, fall back to the current fixture-id behavior (so the demo flow on `/` still works for anonymous visitors).
  - `streamRun(runId)` — unchanged (still fixture-driven), but on the terminal `run.complete` event we also call `setRunStatus(runId, "succeeded", { completedAt })` and `persistRunResult` if signed in.
- `getAuditReport` already derives from `getRun`, so no change needed.

### 4. Author chip + visibility selector (light touch)

- `ActionsRail.tsx` — when signed in, show a single radio: **Public** / **Unlisted** (default Public, matches the catalog model). Stored on `RunConfig.metadata.visibility` and forwarded to `persistRunRow`.
- Run cards on `/` and `/visualizer` show a small "by you" badge when `author_user_id === currentUser.id`.

### 5. Audit + role checks

- `src/lib/audit.ts` already writes rows; once auth lands, `user_id` will be populated automatically by RLS (`with check user_id = auth.uid()`). No code change.
- `src/lib/toolRegistry.ts` `destructive` tier already gates on `hasRole("admin")` — once the admin seed runs, the gating starts working for real instead of always denying.

### 6. Docs

- Update `docs/audit.md` with: how to claim admin (`select public.claim_admin('you@example.com')` from the SQL editor or via the in-app one-shot button we'll add to `/login` for the very first user), and the role hierarchy.

## Out of scope (next turn)

- Password reset / `/reset-password`.
- `profiles` table + display name.
- Cutting the visualizer over to Postgres-backed timelines (still fixture-served; persistence helpers are ready).
- `liveBackend` flip — backend is still the fixture path. Only persistence flips this turn.

## Files

**New**
- `supabase/migrations/<ts>_auth_seed.sql` — `handle_new_user` trigger + `claim_admin` function.
- `src/lib/auth.tsx`
- `src/routes/login.tsx`
- `src/routes/auth.callback.tsx`
- `src/components/user-menu.tsx`

**Edited**
- `src/routes/__root.tsx` (AuthProvider wrap)
- `src/router.tsx` (typed router context if needed)
- `src/services/simulator.ts` (Postgres-first reads/writes with fixture fallback)
- `src/components/configurator/ActionsRail.tsx` (visibility radio + author badge)
- `src/components/visualizer/transport-bar.tsx` (UserMenu)
- `src/config/features.ts` (`persistRuns: true`)
- `docs/audit.md`

## Risk + rollback

- If anything regresses for anonymous users, `FEATURES.persistRuns = false` reverts every service call back to fixtures in one line — the helpers no-op, the routes still render. The new auth UI keeps working but stops persisting.
- RLS already enforces visibility, so a signed-in user can never see another user's private run even if the client query is wrong.
- Google OAuth uses Lovable Cloud's managed credentials by default; no secret request needed.

Ready for approval — say the word and I'll implement.