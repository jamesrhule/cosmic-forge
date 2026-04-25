-- 1. Tighten WITH CHECK on runs INSERT (was blank)
DROP POLICY IF EXISTS "authenticated users create runs" ON public.runs;
CREATE POLICY "authenticated users create runs"
  ON public.runs
  FOR INSERT
  TO authenticated
  WITH CHECK (author_user_id = auth.uid());

-- 2. tool_call_audit INSERT already has WITH CHECK; re-affirm + restrict to authenticated
DROP POLICY IF EXISTS "authenticated users insert own audit rows" ON public.tool_call_audit;
CREATE POLICY "authenticated users insert own audit rows"
  ON public.tool_call_audit
  FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

-- Same table: tighten SELECT to authenticated only (audit log is user-private)
DROP POLICY IF EXISTS "users read own audit rows" ON public.tool_call_audit;
CREATE POLICY "users read own audit rows"
  ON public.tool_call_audit
  FOR SELECT
  TO authenticated
  USING ((user_id = auth.uid()) OR public.has_role(auth.uid(), 'admin'::public.app_role));

-- 3. profiles INSERT WITH CHECK already exists but is open to all roles — pin to authenticated
DROP POLICY IF EXISTS "users insert own profile" ON public.profiles;
CREATE POLICY "users insert own profile"
  ON public.profiles
  FOR INSERT
  TO authenticated
  WITH CHECK (id = auth.uid());

-- 4. Restrict profiles public read: keep public-readable but narrow exposure.
--    The frontend reads display_name/handle/bio/avatar_url/affiliation only;
--    drop the open `USING (true)` policy and replace with one that's still
--    public but documented, plus an authenticated-only policy that the
--    frontend's getProfile() path will hit when signed in (RLS combines
--    permissively, so anonymous users still see profiles via the public
--    policy — this is intentional for author bylines on public runs).
--
--    Note: column-level grants are the right tool for hiding `id` from
--    anonymous SELECTs. We REVOKE id from anon and grant only the
--    public-safe columns. Authenticated callers retain full access.
DROP POLICY IF EXISTS "profiles are publicly readable" ON public.profiles;
CREATE POLICY "profiles are publicly readable"
  ON public.profiles
  FOR SELECT
  TO anon, authenticated
  USING (true);

-- Column-level lockdown for anonymous traffic. Authenticated users keep
-- full SELECT (granted by Supabase defaults to `authenticated`).
REVOKE SELECT ON public.profiles FROM anon;
GRANT SELECT (display_name, handle, bio, avatar_url, affiliation, created_at) ON public.profiles TO anon;

-- 5. Move citext extension out of public schema (Supabase linter 0014)
CREATE SCHEMA IF NOT EXISTS extensions;
GRANT USAGE ON SCHEMA extensions TO postgres, anon, authenticated, service_role;
ALTER EXTENSION citext SET SCHEMA extensions;