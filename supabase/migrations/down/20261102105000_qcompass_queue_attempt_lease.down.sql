-- Inverse of 20261102105000_qcompass_queue_attempt_lease.sql: drops the
-- per-attempt overloads and the run-status trigger, and restores the
-- 20261031180000 body of heartbeat_job(job, worker, lease) and the
-- 20261031200300 body of complete_job(job, worker, result, error).
-- Functions and triggers hold no data (R13).
drop trigger if exists runs_status_transition on public.runs;
drop function if exists public.runs_status_transition_guard();
drop function if exists public.heartbeat_job(uuid, text, int, int);
drop function if exists public.complete_job(uuid, text, int, jsonb, text);

create or replace function public.heartbeat_job(_job_id uuid, _worker_id text, _lease_seconds int default 60)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  renewed boolean;
begin
  if auth.role() not in ('service_role') then
    raise exception 'heartbeat_job requires service role';
  end if;
  update public.jobs
     set locked_until = now() + make_interval(secs => _lease_seconds)
   where id = _job_id and locked_by = _worker_id and status = 'running'
  returning true into renewed;
  return coalesce(renewed, false);
end;
$$;

create or replace function public.complete_job(_job_id uuid, _worker_id text, _result jsonb, _error text)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  done boolean;
begin
  if auth.role() not in ('service_role') then
    raise exception 'complete_job requires service role';
  end if;

  update public.jobs
     set status = case when _error is null then 'succeeded'::public.job_status else 'failed'::public.job_status end,
         finished_at = now(),
         locked_until = null,
         result = coalesce(_result, result),
         error = _error
   where id = _job_id and status = 'running' and locked_by = _worker_id
  returning true into done;
  return coalesce(done, false);
end;
$$;

revoke all on function public.heartbeat_job(uuid, text, int) from public, anon, authenticated;
revoke all on function public.complete_job(uuid, text, jsonb, text) from public, anon, authenticated;
