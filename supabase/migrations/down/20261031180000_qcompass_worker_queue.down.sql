-- Inverse of 20261031180000_qcompass_worker_queue.sql.
-- R13: public.job_events is renamed (deprecated), never dropped. The two
-- new functions are dropped (they hold no data); complete_job is restored
-- to its 20260427001133 definition. Enum values cannot be removed from a
-- Postgres enum without rewriting every column that uses it, so 'qpu' and
-- 'edge' stay (unused values are harmless).
do $$
declare
  i record;
  suffix constant text := '_20261031180000';
begin
  if to_regclass('public.job_events') is not null then
    for i in select indexname from pg_indexes where schemaname = 'public' and tablename = 'job_events' loop
      execute format('alter index public.%I rename to %I', i.indexname, left('_dep_' || i.indexname || suffix, 63));
    end loop;
    alter table public.job_events rename to _deprecated_job_events_20261031180000;
  end if;
end $$;

drop index if exists public.jobs_lease_idx;
drop function if exists public.heartbeat_job(uuid, text, int);
drop function if exists public.reap_expired_jobs();

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
