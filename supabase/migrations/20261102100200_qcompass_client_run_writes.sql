-- Gate 1 round 2 (security lane DB): client writes of runs and everything
-- hung off a run need a writer role in the run's tenant. Additive and
-- idempotent (R13); the inverse is
-- down/20261102100200_qcompass_client_run_writes.down.sql, which restores
-- the previous policies (20261031200200 for the three it changed, main's
-- 20260424153958 for the rest) and drops the two functions added here.
--
-- 20261031200200 (SEC-M1) checked tenant membership only in the WITH CHECK
-- of runs insert/update and "authors write results", and accepted any
-- member, viewer included. So (round-2 c2):
--   * an author kept updating, deleting and writing results for a run that
--     sits in a tenant they no longer (or never) belonged to: the USING
--     clauses and "authors delete own runs" tested only author_user_id;
--   * audit_reports, viz_timelines and the storage write/update/delete
--     policies on the run-artifacts and viz-timelines buckets had no tenant
--     test at all;
--   * a read-only viewer could insert tenant runs and their results.
--
-- Every client write policy on these objects now also requires
-- public.qcompass_can_write_run(run tenant, auth.uid()): the run has no
-- tenant (a personal run, which is what src/lib/persistence.ts writes), or
-- the user's role in it is owner, admin or member. Reads are unchanged.
--
-- Legitimate client writes, found by grepping src/ (supabase/functions/
-- does not exist): src/lib/persistence.ts upserts runs (never sets
-- tenant_id), run_results, audit_reports, viz_timelines and uploads
-- viz-timelines/<runId>/timeline.json; src/services/simulator.ts calls
-- those helpers. All of them write personal runs (tenant_id null) or, for
-- runs main's 20260427001133 backfilled into the author's personal tenant,
-- runs in a tenant the author owns; both stay allowed. Tenant runs are
-- written by the API and the worker (table owner / service_role), which
-- RLS does not restrict; the API also ignores client-authored rows
-- (author_user_id is not null) when it serves a tenant's runs.
--
-- public.qcompass_forged_row_report() lists rows that the policies before
-- this file let a client forge, so James can review them: jobs whose tenant
-- differs from their run's (forged before 20261031200100), runs whose
-- author is not a writer of the run's tenant, and storage objects filed
-- under such runs. It reports and never deletes; it is service-only. This
-- migration prints the count with a NOTICE.

create or replace function public.qcompass_can_write_run(_tenant uuid, _user uuid)
returns boolean
language sql
stable
set search_path = public
as $$
  select _tenant is null
      or coalesce(public.tenant_role(_tenant, _user) in ('owner', 'admin', 'member'), false)
$$;

-- runs -------------------------------------------------------------------
drop policy if exists "authenticated users create runs" on public.runs;
create policy "authenticated users create runs" on public.runs
  for insert to authenticated
  with check (author_user_id = auth.uid() and public.qcompass_can_write_run(tenant_id, auth.uid()));

drop policy if exists "authors update own runs" on public.runs;
create policy "authors update own runs" on public.runs
  for update to authenticated
  using (author_user_id = auth.uid() and public.qcompass_can_write_run(tenant_id, auth.uid()))
  with check (author_user_id = auth.uid() and public.qcompass_can_write_run(tenant_id, auth.uid()));

drop policy if exists "authors delete own runs" on public.runs;
create policy "authors delete own runs" on public.runs
  for delete to authenticated
  using (author_user_id = auth.uid() and public.qcompass_can_write_run(tenant_id, auth.uid()));

-- rows hung off a run -----------------------------------------------------
drop policy if exists "authors write results" on public.run_results;
create policy "authors write results" on public.run_results
  for all to authenticated
  using (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
      and public.qcompass_can_write_run(r.tenant_id, auth.uid())
  ))
  with check (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
      and public.qcompass_can_write_run(r.tenant_id, auth.uid())
  ));

drop policy if exists "authors write audits" on public.audit_reports;
create policy "authors write audits" on public.audit_reports
  for all to authenticated
  using (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
      and public.qcompass_can_write_run(r.tenant_id, auth.uid())
  ))
  with check (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
      and public.qcompass_can_write_run(r.tenant_id, auth.uid())
  ));

drop policy if exists "authors write timelines" on public.viz_timelines;
create policy "authors write timelines" on public.viz_timelines
  for all to authenticated
  using (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
      and public.qcompass_can_write_run(r.tenant_id, auth.uid())
  ))
  with check (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
      and public.qcompass_can_write_run(r.tenant_id, auth.uid())
  ));

-- storage (object name '<run_id>/<file>', main's convention) ---------------
drop policy if exists "authors write viz-timelines" on storage.objects;
create policy "authors write viz-timelines" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'viz-timelines'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1) and r.author_user_id = auth.uid()
        and public.qcompass_can_write_run(r.tenant_id, auth.uid())
    )
  );

drop policy if exists "authors update viz-timelines" on storage.objects;
create policy "authors update viz-timelines" on storage.objects
  for update to authenticated
  using (
    bucket_id = 'viz-timelines'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1) and r.author_user_id = auth.uid()
        and public.qcompass_can_write_run(r.tenant_id, auth.uid())
    )
  );

drop policy if exists "authors delete viz-timelines" on storage.objects;
create policy "authors delete viz-timelines" on storage.objects
  for delete to authenticated
  using (
    bucket_id = 'viz-timelines'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1) and r.author_user_id = auth.uid()
        and public.qcompass_can_write_run(r.tenant_id, auth.uid())
    )
  );

drop policy if exists "authors write run-artifacts" on storage.objects;
create policy "authors write run-artifacts" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'run-artifacts'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1) and r.author_user_id = auth.uid()
        and public.qcompass_can_write_run(r.tenant_id, auth.uid())
    )
  );

drop policy if exists "authors delete run-artifacts" on storage.objects;
create policy "authors delete run-artifacts" on storage.objects
  for delete to authenticated
  using (
    bucket_id = 'run-artifacts'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1) and r.author_user_id = auth.uid()
        and public.qcompass_can_write_run(r.tenant_id, auth.uid())
    )
  );

-- Report of rows forged before the fixes (never deletes) ------------------
create or replace function public.qcompass_forged_row_report()
returns table (kind text, ref text, tenant_id uuid, detail text)
language sql
stable
set search_path = public
as $$
  select 'job_tenant_differs_from_run', j.id::text, j.tenant_id,
         format('job %s of tenant %s points at run %s of tenant %s',
                j.id, j.tenant_id, j.run_id, coalesce(r.tenant_id::text, 'none'))
    from public.jobs j
    join public.runs r on r.id = j.run_id
   where j.tenant_id is distinct from r.tenant_id
  union all
  select 'run_author_not_a_writer', r.id, r.tenant_id,
         format('run %s by user %s, whose role in tenant %s is %s',
                r.id, r.author_user_id, r.tenant_id,
                coalesce(public.tenant_role(r.tenant_id, r.author_user_id)::text, 'none'))
    from public.runs r
   where r.author_user_id is not null and r.tenant_id is not null
     and not public.qcompass_can_write_run(r.tenant_id, r.author_user_id)
  union all
  select 'storage_object_of_such_run', o.bucket_id || '/' || o.name, r.tenant_id,
         format('object %s/%s under run %s by user %s, not a writer of tenant %s',
                o.bucket_id, o.name, r.id, r.author_user_id, r.tenant_id)
    from storage.objects o
    join public.runs r on r.id = split_part(o.name, '/', 1)
   where o.bucket_id in ('run-artifacts', 'viz-timelines')
     and r.author_user_id is not null and r.tenant_id is not null
     and not public.qcompass_can_write_run(r.tenant_id, r.author_user_id)
$$;

revoke all on function public.qcompass_forged_row_report() from public;
revoke all on function public.qcompass_forged_row_report() from anon, authenticated;
grant execute on function public.qcompass_forged_row_report() to service_role;

do $$
declare
  n bigint;
begin
  select count(*) into n from public.qcompass_forged_row_report();
  if n > 0 then
    raise notice 'qcompass_forged_row_report: % row(s) to review (select * from public.qcompass_forged_row_report())', n;
  end if;
end $$;
