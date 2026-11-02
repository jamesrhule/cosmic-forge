-- Gate 1 security round 2, worker lane (c3). Additive and idempotent (R13);
-- the inverse is down/20261102105000_qcompass_queue_attempt_lease.down.sql,
-- which restores the 20261031180000 body of heartbeat_job(job, worker,
-- lease) and the 20261031200300 body of complete_job(job, worker, result,
-- error), and drops what this migration adds.
--
-- Per-attempt leases (SF2 residual). A lease was (job, worker id): an
-- attempt the worker had abandoned, or a stale worker reusing the same id,
-- still matched it after the job was requeued and claimed again. A lease is
-- now (job, worker id, attempt), where attempt is jobs.attempts as
-- claim_next_job returned it; the next claim increments attempts, so no
-- earlier attempt matches again.
--   * heartbeat_job(job, worker, attempt, lease_seconds) and
--     complete_job(job, worker, attempt, result, error) check all three.
--   * The forms without an attempt now refuse, as 20261031200300 did for
--     complete_job(job, result, error): every caller says which attempt.
--   (Run, result, provenance and event writes carry the same check in the
--   service's SQL, ucgle_f1/jobs.py.)
--
-- Sticky run states. A run moves only queued -> running -> terminal
-- (queued -> failed/canceled for a run that ends before it starts). A
-- terminal run (completed, failed, canceled) never changes status again,
-- whoever writes: the service, a worker, the janitor or a client.

create or replace function public.heartbeat_job(_job_id uuid, _worker_id text, _attempt int, _lease_seconds int)
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
   where id = _job_id and locked_by = _worker_id and attempts = _attempt and status = 'running'
  returning true into renewed;
  return coalesce(renewed, false);
end;
$$;

create or replace function public.complete_job(
  _job_id uuid, _worker_id text, _attempt int, _result jsonb, _error text
)
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
   where id = _job_id and status = 'running' and locked_by = _worker_id and attempts = _attempt
  returning true into done;
  return coalesce(done, false);
end;
$$;

create or replace function public.heartbeat_job(_job_id uuid, _worker_id text, _lease_seconds int default 60)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  raise exception 'heartbeat_job(job, worker, lease) has no attempt check; call heartbeat_job(job, worker, attempt, lease)';
end;
$$;

create or replace function public.complete_job(_job_id uuid, _worker_id text, _result jsonb, _error text)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  raise exception 'complete_job(job, worker, result, error) has no attempt check; call complete_job(job, worker, attempt, result, error)';
end;
$$;

revoke all on function public.heartbeat_job(uuid, text, int, int) from public, anon, authenticated;
revoke all on function public.complete_job(uuid, text, int, jsonb, text) from public, anon, authenticated;

create or replace function public.runs_status_transition_guard()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.status is distinct from old.status and not (
       (old.status = 'queued' and new.status in ('running', 'failed', 'canceled'))
    or (old.status = 'running' and new.status in ('completed', 'failed', 'canceled'))
  ) then
    raise exception 'run % cannot go from % to %', old.id, old.status, new.status
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

drop trigger if exists runs_status_transition on public.runs;
create trigger runs_status_transition
  before update of status on public.runs
  for each row execute function public.runs_status_transition_guard();
