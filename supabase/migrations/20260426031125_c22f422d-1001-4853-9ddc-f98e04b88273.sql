-- ========== 1. Rate limiting ============================================

create table if not exists public.api_rate_limit (
  actor_id text not null,
  scope text not null,
  tokens double precision not null default 0,
  refilled_at timestamptz not null default now(),
  primary key (actor_id, scope)
);

alter table public.api_rate_limit enable row level security;

-- No direct client access; everything goes through the SECURITY DEFINER fn.
create policy "rate_limit_no_direct_select"
  on public.api_rate_limit for select
  to authenticated
  using (false);

create or replace function public.check_rate_limit(
  _scope text,
  _capacity double precision,
  _refill_per_sec double precision
) returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  caller uuid := auth.uid();
  actor text;
  row_tokens double precision;
  row_refilled timestamptz;
  now_ts timestamptz := now();
  elapsed double precision;
  new_tokens double precision;
begin
  if caller is null then
    -- anonymous: bucket per (scope, "anon") — the caller is responsible for
    -- including request IP in the scope when finer granularity is needed.
    actor := 'anon';
  else
    actor := caller::text;
  end if;

  insert into public.api_rate_limit (actor_id, scope, tokens, refilled_at)
  values (actor, _scope, _capacity, now_ts)
  on conflict (actor_id, scope) do nothing;

  select tokens, refilled_at
    into row_tokens, row_refilled
    from public.api_rate_limit
   where actor_id = actor and scope = _scope
   for update;

  elapsed := greatest(0, extract(epoch from (now_ts - row_refilled)));
  new_tokens := least(_capacity, row_tokens + elapsed * _refill_per_sec);

  if new_tokens >= 1 then
    update public.api_rate_limit
       set tokens = new_tokens - 1,
           refilled_at = now_ts
     where actor_id = actor and scope = _scope;
    return true;
  else
    update public.api_rate_limit
       set tokens = new_tokens,
           refilled_at = now_ts
     where actor_id = actor and scope = _scope;
    return false;
  end if;
end;
$$;

revoke all on function public.check_rate_limit(text, double precision, double precision) from public;
grant execute on function public.check_rate_limit(text, double precision, double precision) to anon, authenticated;

-- ========== 2. System incidents (powers /status) ========================

create table if not exists public.system_incidents (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  status text not null default 'investigating'
    check (status in ('investigating','identified','monitoring','resolved')),
  severity text not null default 'minor'
    check (severity in ('minor','major','critical')),
  body text,
  started_at timestamptz not null default now(),
  resolved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.system_incidents enable row level security;

create policy "incidents are publicly readable"
  on public.system_incidents for select
  to anon, authenticated
  using (true);

create policy "admins manage incidents"
  on public.system_incidents for all
  to authenticated
  using (public.has_role(auth.uid(), 'admin'::app_role))
  with check (public.has_role(auth.uid(), 'admin'::app_role));

create trigger touch_system_incidents
  before update on public.system_incidents
  for each row execute function public.touch_updated_at();

-- ========== 3. Audit-log retention ======================================

create or replace function public.prune_old_audit_rows()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  deleted integer;
begin
  delete from public.tool_call_audit
   where created_at < now() - interval '90 days';
  get diagnostics deleted = row_count;
  return deleted;
end;
$$;

revoke all on function public.prune_old_audit_rows() from public;
-- only admins / the cron job (which runs as the postgres role) execute it
grant execute on function public.prune_old_audit_rows() to postgres;

create extension if not exists pg_cron with schema extensions;

-- Idempotent reschedule: drop any prior incarnation, then create.
do $$
declare
  job_id bigint;
begin
  select jobid into job_id from cron.job where jobname = 'prune_tool_call_audit_nightly';
  if job_id is not null then
    perform cron.unschedule(job_id);
  end if;
end $$;

select cron.schedule(
  'prune_tool_call_audit_nightly',
  '17 3 * * *',
  $$select public.prune_old_audit_rows();$$
);

-- ========== 4. Harden claim_admin ======================================
-- Original behaviour: any signed-in user matching the email argument could
-- self-promote. After this change the call only succeeds when no admin
-- exists yet (true bootstrap), which removes a remote takeover vector.

create or replace function public.claim_admin(_email text)
 returns boolean
 language plpgsql
 security definer
 set search_path to 'public'
as $$
declare
  caller_email text;
  caller_id uuid;
  existing_admins int;
begin
  caller_id := auth.uid();
  if caller_id is null then
    return false;
  end if;

  caller_email := lower(coalesce(auth.jwt() ->> 'email', ''));
  if caller_email = '' or caller_email <> lower(_email) then
    return false;
  end if;

  -- Require email-verified callers only.
  if coalesce((auth.jwt() ->> 'email_verified')::boolean, false) is not true then
    return false;
  end if;

  select count(*) into existing_admins
    from public.user_roles
   where role = 'admin'::app_role;

  if existing_admins > 0 then
    -- Bootstrap window closed; route the user to ask an existing admin.
    return false;
  end if;

  insert into public.user_roles (user_id, role, granted_by)
  values (caller_id, 'admin'::app_role, caller_id)
  on conflict (user_id, role) do nothing;

  return true;
end;
$$;

-- ========== 5. Tighten tool_call_audit insert policy ====================
-- Require email-verified callers for audit writes (defence-in-depth on top
-- of the soft client-side gate the UI applies).

drop policy if exists "authenticated users insert own audit rows" on public.tool_call_audit;

create policy "verified users insert own audit rows"
  on public.tool_call_audit for insert
  to authenticated
  with check (
    user_id = auth.uid()
    and coalesce((auth.jwt() ->> 'email_verified')::boolean, false) = true
  );