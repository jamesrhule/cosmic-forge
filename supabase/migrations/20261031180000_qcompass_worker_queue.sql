-- P3-02: the worker service runs on main's queue (public.jobs,
-- claim_next_job, complete_job). This migration adds what a leased worker
-- loop needs. Additive and idempotent (R13); the inverse is
-- down/20261031180000_qcompass_worker_queue.down.sql.
--
--   * compute classes 'qpu' and 'edge' (Part 4: cpu, gpu_small, gpu_large,
--     qpu, edge);
--   * public.job_events: per-run progress events written by workers as
--     modules finish, read by the API's SSE/WebSocket streams;
--   * heartbeat_job: lease renewal; returns false when the job was
--     cancelled or the lease was lost, so the worker stops;
--   * reap_expired_jobs: the janitor; requeues expired leases and
--     dead-letters a job after max_attempts with a system_incidents row;
--   * complete_job only completes a job that is still running (a cancelled
--     or requeued job is never overwritten by a stale worker).
-- All functions are service-role only, like claim_next_job.

alter type public.compute_class add value if not exists 'qpu';
alter type public.compute_class add value if not exists 'edge';

create table if not exists public.job_events (
  id          bigserial primary key,
  job_id      uuid references public.jobs(id) on delete cascade,
  run_id      text not null,
  tenant_id   uuid not null references public.tenants(id) on delete cascade,
  type        text not null,
  payload     jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists job_events_run_idx on public.job_events(run_id, id);
alter table public.job_events enable row level security;
drop policy if exists "tenant members read job events" on public.job_events;
create policy "tenant members read job events" on public.job_events
  for select to authenticated
  using (public.is_tenant_member(tenant_id, auth.uid()));

create index if not exists jobs_lease_idx on public.jobs(locked_until) where status = 'running';

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

revoke all on function public.heartbeat_job(uuid, text, int) from public, anon, authenticated;
revoke all on function public.reap_expired_jobs() from public, anon, authenticated;
