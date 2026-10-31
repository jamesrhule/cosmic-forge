-- Inverse of 20261031200100_qcompass_jobs_service_enqueue.sql: main's
-- policy as created in 20260427001133. Policies hold no data (R13).
drop policy if exists "service role enqueues jobs" on public.jobs;

drop policy if exists "tenant members enqueue jobs" on public.jobs;
create policy "tenant members enqueue jobs" on public.jobs
  for insert to authenticated
  with check (
    public.is_tenant_member(tenant_id, auth.uid())
    and created_by = auth.uid()
    and status = 'queued'
    and locked_by is null
  );
