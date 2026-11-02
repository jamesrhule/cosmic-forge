-- Gate 1 round 3B (lane DB3): a positive marker for the runs the API created.
-- Additive and idempotent (R13); the inverse is
-- down/20261102120000_qcompass_run_api_origin.down.sql, which restores
-- 20261102100300's alias index and keeps this column's data (renamed).
--
-- Round 2 took "author_user_id is null" as proof that the API created a run:
-- JobQueue served and listed only such rows of a tenant, the monthly quota
-- (plans.enforce_at_enqueue) counted only them, and the per-tenant alias
-- index (20261102100300) covered only them. But runs.author_user_id
-- references auth.users ON DELETE SET NULL (20260424153958). When a member's
-- account is deleted (offboarding, GDPR), every tenant run that member wrote
-- through PostgREST loses its author and became a platform run: the API
-- served a planted 'completed' run and its result, the quota counted the
-- member's rows dated 2099, and a client row that reused an API run's alias
-- made the account undeletable (unique violation from the SET NULL). The
-- tenant's owner cannot delete those author-less rows through the client
-- (round-2 DB verifier: R2-VIEWER-PLANT, R2-QUOTA, R2-RUN-ID regression).
--
-- public.runs.origin is 'api' for a run the API created, 'client' for
-- anything else. Only privileged writers choose it: the table's owner (the
-- API and the worker connect as the owner) and service_role, judged by
-- public.qcompass_privileged_writer (20261102100000), i.e. by the database
-- role, never by a JWT claim. For any other writer (PostgREST's
-- authenticated and anon) the trigger runs_origin_guard
--   * on INSERT forces origin = 'client' and client_run_id = null (the alias
--     is the API's per-tenant name for its own runs; a client row never
--     carries one, so it can never collide with an API alias);
--   * on UPDATE refuses any change of origin or client_run_id
--     (insufficient_privilege, as tenants_write_guard does for its columns).
-- The column defaults to 'client', so a privileged writer that does not say
-- otherwise also writes a client row; JobQueue.enqueue_run sets 'api'. The
-- SET NULL of a deleted author runs as the table's owner and changes neither
-- column, so a deleted account turns nothing into an API run.
--
-- Backfill: an existing run is 'api' when it has no author, has a tenant and
-- has a public.jobs row of that same tenant. enqueue_run writes the run and
-- its job in one transaction, and clients cannot insert jobs since
-- 20261031200100. Runs whose author was already deleted have no job and stay
-- 'client'; qcompass_forged_row_report (20261102120100) lists them.
--
-- The alias index keeps its name and now covers origin = 'api' rows only.

do $$
begin
  -- A rollback renames the column; bring it (and its data) back.
  if exists (select 1 from information_schema.columns where table_schema = 'public'
              and table_name = 'runs' and column_name = '_deprecated_origin_20261102120000')
     and not exists (select 1 from information_schema.columns where table_schema = 'public'
              and table_name = 'runs' and column_name = 'origin') then
    alter table public.runs rename column _deprecated_origin_20261102120000 to origin;
  end if;
end $$;

alter table public.runs add column if not exists origin text not null default 'client';
alter table public.runs alter column origin set default 'client';

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'runs_origin_check' and conrelid = 'public.runs'::regclass
  ) then
    alter table public.runs add constraint runs_origin_check check (origin in ('api', 'client'));
  end if;
end $$;

create or replace function public.qcompass_runs_origin_guard()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if public.qcompass_privileged_writer(tg_relid::regclass) then
    return new;
  end if;
  if tg_op = 'INSERT' then
    new.origin := 'client';
    new.client_run_id := null;
    return new;
  end if;
  if new.origin is distinct from old.origin then
    raise exception 'runs.origin is set by the API only'
      using errcode = 'insufficient_privilege';
  end if;
  if new.client_run_id is distinct from old.client_run_id then
    raise exception 'runs.client_run_id is set by the API only'
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end;
$$;

drop trigger if exists runs_origin_guard on public.runs;
create trigger runs_origin_guard
  before insert or update on public.runs
  for each row execute function public.qcompass_runs_origin_guard();

-- Backfill (runs as the owner, so the guard lets it through).
update public.runs r
   set origin = 'api'
 where r.origin = 'client'
   and r.author_user_id is null
   and r.tenant_id is not null
   and exists (select 1 from public.jobs j where j.run_id = r.id and j.tenant_id = r.tenant_id);

-- The per-tenant alias, unique among the API's runs (20261102100300 keyed it
-- on author_user_id is null).
drop index if exists public.runs_tenant_client_run_id_key;
create unique index runs_tenant_client_run_id_key
  on public.runs (tenant_id, client_run_id)
  where client_run_id is not null and origin = 'api';
