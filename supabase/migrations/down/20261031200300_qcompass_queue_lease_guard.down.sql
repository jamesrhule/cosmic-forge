-- Inverse of 20261031200300_qcompass_queue_lease_guard.sql: the
-- 20261031180000 bodies of reap_expired_jobs and complete_job(uuid, jsonb,
-- text); the lease-checked overload is dropped. Functions hold no data (R13).
drop function if exists public.complete_job(uuid, text, jsonb, text);

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
         locked_until = null,
         result = coalesce(_result, result),
         error = _error
   where id = _job_id and status = 'running';
end;
$$;
