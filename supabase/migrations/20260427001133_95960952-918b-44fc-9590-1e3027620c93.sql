-- =========================================================================
-- TIER 5: tenants, jobs, billing fields, GPU compute_class
-- =========================================================================

-- 1. Enums ----------------------------------------------------------------
do $$ begin
  create type public.tenant_role as enum ('owner', 'admin', 'member', 'viewer');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.subscription_tier as enum ('free', 'pro', 'team', 'enterprise');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.job_status as enum ('queued', 'running', 'succeeded', 'failed', 'cancelled');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.compute_class as enum ('cpu', 'gpu_small', 'gpu_large');
exception when duplicate_object then null; end $$;

-- 2. Tenants --------------------------------------------------------------
create table if not exists public.tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  subscription_tier public.subscription_tier not null default 'free',
  billing_email text,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.tenant_members (
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role public.tenant_role not null default 'member',
  joined_at timestamptz not null default now(),
  primary key (tenant_id, user_id)
);

create index if not exists tenant_members_user_idx on public.tenant_members(user_id);

-- 3. Helper: is_tenant_member ---------------------------------------------
create or replace function public.is_tenant_member(_tenant uuid, _user uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.tenant_members
    where tenant_id = _tenant and user_id = _user
  )
$$;

create or replace function public.tenant_role(_tenant uuid, _user uuid)
returns public.tenant_role
language sql
stable
security definer
set search_path = public
as $$
  select role from public.tenant_members
  where tenant_id = _tenant and user_id = _user
  limit 1
$$;

-- 4. Default per-user "Personal" tenant + backfill ------------------------
create or replace function public.ensure_personal_tenant(_user uuid)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  t_id uuid;
  base_slug text;
begin
  select tm.tenant_id into t_id
    from public.tenant_members tm
    join public.tenants t on t.id = tm.tenant_id
   where tm.user_id = _user
     and t.created_by = _user
   order by tm.joined_at asc
   limit 1;

  if t_id is not null then return t_id; end if;

  base_slug := 'personal-' || substr(replace(_user::text, '-', ''), 1, 12);

  insert into public.tenants (name, slug, created_by)
  values ('Personal', base_slug, _user)
  returning id into t_id;

  insert into public.tenant_members (tenant_id, user_id, role)
  values (t_id, _user, 'owner')
  on conflict do nothing;

  return t_id;
end;
$$;

-- Backfill: one personal tenant per existing run author
do $$
declare
  rec record;
  t_id uuid;
begin
  for rec in
    select distinct author_user_id from public.runs where author_user_id is not null
  loop
    t_id := public.ensure_personal_tenant(rec.author_user_id);
  end loop;
end $$;

-- 5. Add tenant_id to existing tables -------------------------------------
alter table public.runs add column if not exists tenant_id uuid references public.tenants(id) on delete cascade;
alter table public.tool_call_audit add column if not exists tenant_id uuid references public.tenants(id) on delete set null;

-- Backfill tenant_id on runs from author's personal tenant
update public.runs r
   set tenant_id = (
     select tm.tenant_id
       from public.tenant_members tm
       join public.tenants t on t.id = tm.tenant_id
      where tm.user_id = r.author_user_id
        and t.created_by = r.author_user_id
      order by tm.joined_at asc
      limit 1
   )
 where tenant_id is null and author_user_id is not null;

create index if not exists runs_tenant_idx on public.runs(tenant_id);
create index if not exists audit_tenant_idx on public.tool_call_audit(tenant_id);

-- 6. Jobs queue -----------------------------------------------------------
create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  run_id text references public.runs(id) on delete cascade,
  kind text not null,
  payload jsonb not null default '{}'::jsonb,
  status public.job_status not null default 'queued',
  priority int not null default 100,
  compute_class public.compute_class not null default 'cpu',
  attempts int not null default 0,
  max_attempts int not null default 3,
  locked_by text,
  locked_until timestamptz,
  scheduled_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  error text,
  result jsonb,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists jobs_status_idx on public.jobs(status, priority desc, scheduled_at);
create index if not exists jobs_tenant_idx on public.jobs(tenant_id);

create trigger jobs_touch_updated
  before update on public.jobs
  for each row execute function public.touch_updated_at();

create trigger tenants_touch_updated
  before update on public.tenants
  for each row execute function public.touch_updated_at();

-- 7. Job claim / complete RPCs -------------------------------------------
create or replace function public.claim_next_job(_worker_id text, _classes public.compute_class[], _lease_seconds int default 60)
returns public.jobs
language plpgsql
security definer
set search_path = public
as $$
declare
  picked public.jobs;
begin
  -- Service-role only: anon/authenticated should never call this directly.
  if auth.role() not in ('service_role') then
    raise exception 'claim_next_job requires service role';
  end if;

  update public.jobs j
     set status = 'running',
         locked_by = _worker_id,
         locked_until = now() + make_interval(secs => _lease_seconds),
         attempts = attempts + 1,
         started_at = coalesce(started_at, now())
   where j.id = (
     select id from public.jobs
      where status = 'queued'
        and scheduled_at <= now()
        and compute_class = any(_classes)
      order by priority desc, scheduled_at asc
      for update skip locked
      limit 1
   )
  returning * into picked;

  return picked;
end;
$$;

create or replace function public.complete_job(_job_id uuid, _result jsonb default null, _error text default null)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.role() not in ('service_role') then
    raise exception 'complete_job requires service role';
  end if;

  update public.jobs
     set status = case when _error is null then 'succeeded'::public.job_status else 'failed'::public.job_status end,
         finished_at = now(),
         result = coalesce(_result, result),
         error = _error
   where id = _job_id;
end;
$$;

-- 8. RLS ------------------------------------------------------------------
alter table public.tenants enable row level security;
alter table public.tenant_members enable row level security;
alter table public.jobs enable row level security;

-- tenants
create policy "members read own tenants" on public.tenants
  for select to authenticated
  using (public.is_tenant_member(id, auth.uid()));

create policy "owners update tenants" on public.tenants
  for update to authenticated
  using (public.tenant_role(id, auth.uid()) in ('owner','admin'))
  with check (public.tenant_role(id, auth.uid()) in ('owner','admin'));

create policy "verified users create tenants" on public.tenants
  for insert to authenticated
  with check (
    created_by = auth.uid()
    and coalesce(((auth.jwt() ->> 'email_verified')::boolean), false) = true
  );

-- tenant_members
create policy "members read own memberships" on public.tenant_members
  for select to authenticated
  using (user_id = auth.uid() or public.is_tenant_member(tenant_id, auth.uid()));

create policy "admins manage members" on public.tenant_members
  for all to authenticated
  using (public.tenant_role(tenant_id, auth.uid()) in ('owner','admin'))
  with check (public.tenant_role(tenant_id, auth.uid()) in ('owner','admin'));

-- jobs (read-only to tenant members; mutation via service role only)
create policy "tenant members read jobs" on public.jobs
  for select to authenticated
  using (public.is_tenant_member(tenant_id, auth.uid()));

create policy "tenant members enqueue jobs" on public.jobs
  for insert to authenticated
  with check (
    public.is_tenant_member(tenant_id, auth.uid())
    and created_by = auth.uid()
    and status = 'queued'
    and locked_by is null
  );

-- 9. Update existing run policies to include tenant membership -----------
drop policy if exists "anyone reads public runs" on public.runs;
create policy "anyone reads public runs" on public.runs
  for select to public
  using (
    visibility = 'public'
    or author_user_id = auth.uid()
    or (tenant_id is not null and public.is_tenant_member(tenant_id, auth.uid()))
  );

-- 10. Tool call audit: enforce tenant membership when tenant_id is set ---
drop policy if exists "verified users insert own audit rows" on public.tool_call_audit;
create policy "verified users insert own audit rows" on public.tool_call_audit
  for insert to authenticated
  with check (
    user_id = auth.uid()
    and coalesce(((auth.jwt() ->> 'email_verified')::boolean), false) = true
    and (tenant_id is null or public.is_tenant_member(tenant_id, auth.uid()))
  );

-- 11. Auto-create personal tenant on signup ------------------------------
create or replace function public.handle_new_user_tenant()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.ensure_personal_tenant(new.id);
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_tenant on auth.users;
create trigger on_auth_user_created_tenant
  after insert on auth.users
  for each row execute function public.handle_new_user_tenant();
