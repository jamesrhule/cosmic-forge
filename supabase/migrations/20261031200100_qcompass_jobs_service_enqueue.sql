-- SEC-H2 (Gate 1 security review): only the service role enqueues jobs.
-- Additive and idempotent (R13); the inverse is
-- down/20261031200100_qcompass_jobs_service_enqueue.down.sql, which restores
-- main's policy from 20260427001133.
--
-- Main's "tenant members enqueue jobs" let any member insert a job with any
-- compute_class, priority, max_attempts, kind, payload and run_id, including
-- another tenant's run id; the worker then ran it with the service role,
-- bypassing plan limits (P3-05) and scopes, and overwrote the victim run's
-- status, events, result and provenance. Every enqueue now goes through the
-- API (POST /api/qcompass/domains/{id}/runs, POST /api/runs), which checks
-- the principal, its scopes and its plan before inserting with the service
-- role. The frontend's direct insert (src/lib/jobs.ts, never called) is
-- removed in the same change. No client RPC is added: nothing needs one.
--
-- Members keep reading their tenant's jobs ("tenant members read jobs").

drop policy if exists "tenant members enqueue jobs" on public.jobs;

drop policy if exists "service role enqueues jobs" on public.jobs;
create policy "service role enqueues jobs" on public.jobs
  for insert to service_role
  with check (true);
