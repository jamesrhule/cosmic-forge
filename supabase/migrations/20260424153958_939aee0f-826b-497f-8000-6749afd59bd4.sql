-- ============================================================
-- App roles (separate table — never on profiles)
-- ============================================================
create type public.app_role as enum ('viewer', 'researcher', 'admin');

create table public.user_roles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  role public.app_role not null,
  granted_at timestamptz not null default now(),
  granted_by uuid references auth.users(id),
  unique (user_id, role)
);

alter table public.user_roles enable row level security;

create or replace function public.has_role(_user_id uuid, _role public.app_role)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.user_roles
    where user_id = _user_id and role = _role
  )
$$;

create policy "users read own roles"
  on public.user_roles for select
  to authenticated
  using (user_id = auth.uid() or public.has_role(auth.uid(), 'admin'));

create policy "admins manage roles"
  on public.user_roles for all
  to authenticated
  using (public.has_role(auth.uid(), 'admin'))
  with check (public.has_role(auth.uid(), 'admin'));

-- ============================================================
-- Runs (public catalog, author-attributed)
-- ============================================================
create type public.run_visibility as enum ('public', 'unlisted', 'private');
create type public.run_status as enum ('queued', 'running', 'completed', 'failed', 'canceled');

create table public.runs (
  id text primary key,
  author_user_id uuid references auth.users(id) on delete set null,
  visibility public.run_visibility not null default 'public',
  status public.run_status not null default 'queued',
  label text,
  notes text,
  config jsonb not null,
  potential_kind text,
  precision text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index runs_author_idx on public.runs(author_user_id);
create index runs_status_idx on public.runs(status);
create index runs_visibility_created_idx on public.runs(visibility, created_at desc);

alter table public.runs enable row level security;

create policy "anyone reads public runs"
  on public.runs for select
  using (visibility = 'public' or author_user_id = auth.uid());

create policy "authenticated users create runs"
  on public.runs for insert
  to authenticated
  with check (author_user_id = auth.uid());

create policy "authors update own runs"
  on public.runs for update
  to authenticated
  using (author_user_id = auth.uid())
  with check (author_user_id = auth.uid());

create policy "authors delete own runs"
  on public.runs for delete
  to authenticated
  using (author_user_id = auth.uid());

-- ============================================================
-- Run results (full payload)
-- ============================================================
create table public.run_results (
  run_id text primary key references public.runs(id) on delete cascade,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.run_results enable row level security;

create policy "results follow run visibility"
  on public.run_results for select
  using (exists (
    select 1 from public.runs r
    where r.id = run_id
      and (r.visibility = 'public' or r.author_user_id = auth.uid())
  ));

create policy "authors write results"
  on public.run_results for all
  to authenticated
  using (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ))
  with check (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ));

-- ============================================================
-- Audit reports (denormalized for queryability)
-- ============================================================
create table public.audit_reports (
  run_id text primary key references public.runs(id) on delete cascade,
  verdicts jsonb not null,
  pass_count integer,
  fail_count integer,
  created_at timestamptz not null default now()
);

alter table public.audit_reports enable row level security;

create policy "audits follow run visibility"
  on public.audit_reports for select
  using (exists (
    select 1 from public.runs r
    where r.id = run_id
      and (r.visibility = 'public' or r.author_user_id = auth.uid())
  ));

create policy "authors write audits"
  on public.audit_reports for all
  to authenticated
  using (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ))
  with check (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ));

-- ============================================================
-- Visualization timelines (metadata only; large buffers in storage)
-- ============================================================
create table public.viz_timelines (
  run_id text primary key references public.runs(id) on delete cascade,
  frame_count integer,
  duration_seconds double precision,
  bytes_size bigint,
  storage_path text not null,
  manifest jsonb,
  expires_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.viz_timelines enable row level security;

create policy "timelines follow run visibility"
  on public.viz_timelines for select
  using (exists (
    select 1 from public.runs r
    where r.id = run_id
      and (r.visibility = 'public' or r.author_user_id = auth.uid())
  ));

create policy "authors write timelines"
  on public.viz_timelines for all
  to authenticated
  using (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ))
  with check (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ));

-- ============================================================
-- Tool-call audit (every assistant tool invocation)
-- ============================================================
create type public.tool_tier as enum ('read', 'write', 'destructive');
create type public.tool_status as enum ('ok', 'error', 'denied', 'pending_approval');

create table public.tool_call_audit (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  conversation_id text,
  tool_name text not null,
  tier public.tool_tier not null,
  args_redacted jsonb,
  status public.tool_status not null,
  result_summary text,
  latency_ms integer,
  approval_token_id text,
  created_at timestamptz not null default now()
);

create index tool_call_audit_user_idx on public.tool_call_audit(user_id, created_at desc);
create index tool_call_audit_tool_idx on public.tool_call_audit(tool_name, created_at desc);
create index tool_call_audit_status_idx on public.tool_call_audit(status, created_at desc);

alter table public.tool_call_audit enable row level security;

create policy "users read own audit rows"
  on public.tool_call_audit for select
  using (user_id = auth.uid() or public.has_role(auth.uid(), 'admin'));

create policy "authenticated users insert own audit rows"
  on public.tool_call_audit for insert
  to authenticated
  with check (user_id = auth.uid());

-- ============================================================
-- updated_at trigger
-- ============================================================
create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger runs_touch before update on public.runs
  for each row execute function public.touch_updated_at();

create trigger run_results_touch before update on public.run_results
  for each row execute function public.touch_updated_at();

-- ============================================================
-- Storage buckets (private; access via signed URLs)
-- ============================================================
insert into storage.buckets (id, name, public)
values
  ('viz-timelines', 'viz-timelines', false),
  ('run-artifacts', 'run-artifacts', false)
on conflict (id) do nothing;

-- Storage RLS: read follows the run visibility (path = "<run_id>/...")
create policy "read viz-timelines for visible runs"
  on storage.objects for select
  using (
    bucket_id = 'viz-timelines'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and (r.visibility = 'public' or r.author_user_id = auth.uid())
    )
  );

create policy "authors write viz-timelines"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'viz-timelines'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and r.author_user_id = auth.uid()
    )
  );

create policy "authors update viz-timelines"
  on storage.objects for update
  to authenticated
  using (
    bucket_id = 'viz-timelines'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and r.author_user_id = auth.uid()
    )
  );

create policy "authors delete viz-timelines"
  on storage.objects for delete
  to authenticated
  using (
    bucket_id = 'viz-timelines'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and r.author_user_id = auth.uid()
    )
  );

create policy "read run-artifacts for visible runs"
  on storage.objects for select
  using (
    bucket_id = 'run-artifacts'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and (r.visibility = 'public' or r.author_user_id = auth.uid())
    )
  );

create policy "authors write run-artifacts"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'run-artifacts'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and r.author_user_id = auth.uid()
    )
  );

create policy "authors delete run-artifacts"
  on storage.objects for delete
  to authenticated
  using (
    bucket_id = 'run-artifacts'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and r.author_user_id = auth.uid()
    )
  );