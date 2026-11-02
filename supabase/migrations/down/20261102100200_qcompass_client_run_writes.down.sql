-- Inverse of 20261102100200_qcompass_client_run_writes.sql: the previous
-- policies, i.e. 20261031200200 for runs insert/update and "authors write
-- results", and main's 20260424153958 for the rest. Then the two functions
-- are dropped. Policies and functions hold no data (R13).

-- runs (20261031200200) ----------------------------------------------------
drop policy if exists "authenticated users create runs" on public.runs;
create policy "authenticated users create runs" on public.runs
  for insert to authenticated
  with check (
    author_user_id = auth.uid()
    and (tenant_id is null or public.is_tenant_member(tenant_id, auth.uid()))
  );

drop policy if exists "authors update own runs" on public.runs;
create policy "authors update own runs" on public.runs
  for update to authenticated
  using (author_user_id = auth.uid())
  with check (
    author_user_id = auth.uid()
    and (tenant_id is null or public.is_tenant_member(tenant_id, auth.uid()))
  );

drop policy if exists "authors write results" on public.run_results;
create policy "authors write results" on public.run_results
  for all to authenticated
  using (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ))
  with check (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
      and (r.tenant_id is null or public.is_tenant_member(r.tenant_id, auth.uid()))
  ));

-- main (20260424153958) ----------------------------------------------------
drop policy if exists "authors delete own runs" on public.runs;
create policy "authors delete own runs"
  on public.runs for delete
  to authenticated
  using (author_user_id = auth.uid());

drop policy if exists "authors write audits" on public.audit_reports;
create policy "authors write audits"
  on public.audit_reports for all
  to authenticated
  using (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ))
  with check (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ));

drop policy if exists "authors write timelines" on public.viz_timelines;
create policy "authors write timelines"
  on public.viz_timelines for all
  to authenticated
  using (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ))
  with check (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ));

drop policy if exists "authors write viz-timelines" on storage.objects;
create policy "authors write viz-timelines"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'viz-timelines'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and r.author_user_id = auth.uid()
    )
  );

drop policy if exists "authors update viz-timelines" on storage.objects;
create policy "authors update viz-timelines"
  on storage.objects for update
  to authenticated
  using (
    bucket_id = 'viz-timelines'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and r.author_user_id = auth.uid()
    )
  );

drop policy if exists "authors delete viz-timelines" on storage.objects;
create policy "authors delete viz-timelines"
  on storage.objects for delete
  to authenticated
  using (
    bucket_id = 'viz-timelines'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and r.author_user_id = auth.uid()
    )
  );

drop policy if exists "authors write run-artifacts" on storage.objects;
create policy "authors write run-artifacts"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'run-artifacts'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and r.author_user_id = auth.uid()
    )
  );

drop policy if exists "authors delete run-artifacts" on storage.objects;
create policy "authors delete run-artifacts"
  on storage.objects for delete
  to authenticated
  using (
    bucket_id = 'run-artifacts'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and r.author_user_id = auth.uid()
    )
  );

drop function if exists public.qcompass_forged_row_report();
drop function if exists public.qcompass_can_write_run(uuid, uuid);
