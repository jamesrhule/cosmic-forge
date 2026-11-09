-- Gate 1 code review SF1 + SF2. Additive and idempotent (R13); the inverse
-- is down/20261031200300_qcompass_queue_lease_guard.down.sql, which restores
-- the 20261031180000 bodies.
--
-- SF1: the janitor's dead-letter branch failed the job but left its run
--      'running' with no terminal event, so every stream of it polled
--      forever. It now fails the run (unless it already ended) and writes a
--      'status: failed' job_events row.
-- SF2: completion is for the lease holder only. complete_job(job, worker,
--      result, error) completes a job only while that worker holds its lease
--      (status 'running' and locked_by = worker), so worker A, whose lease
--      expired and whose job worker B reclaimed, can no longer mark it
--      succeeded or failed. The 3-argument form, which had no lease check,
--      now refuses: every caller must say which worker it is.
--      heartbeat_job already checked locked_by.

create or replace function public.reap_expired_jobs()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  j public.jobs;
  n integer := 0;
begin
  if auth.role() not in ('service_role') then
    raise exception 'reap_expired_jobs requires service role';
  end if;
  for j in
    select * from public.jobs
     where status = 'running' and locked_until < now()
     for update skip locked
  loop
    if j.attempts >= j.max_attempts then
      update public.jobs
         set status = 'failed', finished_at = now(), locked_by = null, locked_until = null,
             error = format('dead-letter: lease expired after %s attempt(s)', j.attempts)
       where id = j.id;
      insert into public.system_incidents (title, severity, status, body)
      values (
        format('Job %s dead-lettered', j.id),
        'minor', 'investigating',
        format('Job %s (kind %s, run %s, class %s) lost its lease %s time(s) and reached max_attempts=%s.',
               j.id, j.kind, coalesce(j.run_id, '-'), j.compute_class, j.attempts, j.max_attempts)
      );
      if j.run_id is not null then
        -- SF1: the run ends too, and its streams see a terminal event.
        update public.runs
           set status = 'failed', completed_at = now(), updated_at = now()
         where id = j.run_id and tenant_id = j.tenant_id
           and status not in ('completed', 'failed', 'canceled');
        if found then
          insert into public.job_events (job_id, run_id, tenant_id, type, payload)
          values (j.id, j.run_id, j.tenant_id, 'status',
                  jsonb_build_object('type', 'status', 'status', 'failed', 'at', now()));
        end if;
      end if;
    else
      update public.jobs
         set status = 'queued', locked_by = null, locked_until = null, scheduled_at = now()
       where id = j.id;
    end if;
    n := n + 1;
  end loop;
  return n;
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

create or replace function public.complete_job(_job_id uuid, _result jsonb default null, _error text default null)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  raise exception 'complete_job(job, result, error) has no lease check; call complete_job(job, worker, result, error)';
end;
$$;

revoke all on function public.complete_job(uuid, text, jsonb, text) from public, anon, authenticated;
revoke all on function public.reap_expired_jobs() from public, anon, authenticated;
