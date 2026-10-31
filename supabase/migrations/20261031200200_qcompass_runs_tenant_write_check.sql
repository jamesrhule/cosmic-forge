-- SEC-M1 (Gate 1 security review): run and result writes must stay inside
-- the writer's tenants. Additive and idempotent (R13); the inverse is
-- down/20261031200200_qcompass_runs_tenant_write_check.down.sql, which
-- restores main's policies (20260424153958, tightened in 20260425015026).
--
-- Main's INSERT/UPDATE policies on public.runs checked only author_user_id,
-- so a user could write a run into (or move their run to) a tenant they do
-- not belong to; "authors write results" likewise. Each with-check now also
-- requires tenant_id to be null (a personal run, as src/lib/persistence.ts
-- writes) or a tenant the user is a member of.

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
