-- Inverse of 20261031200200_qcompass_runs_tenant_write_check.sql: main's
-- policies (20260424153958; INSERT as tightened in 20260425015026).
-- Policies hold no data (R13).
drop policy if exists "authenticated users create runs" on public.runs;
create policy "authenticated users create runs"
  on public.runs
  for insert
  to authenticated
  with check (author_user_id = auth.uid());

drop policy if exists "authors update own runs" on public.runs;
create policy "authors update own runs"
  on public.runs for update
  to authenticated
  using (author_user_id = auth.uid())
  with check (author_user_id = auth.uid());

drop policy if exists "authors write results" on public.run_results;
create policy "authors write results"
  on public.run_results for all
  to authenticated
  using (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ))
  with check (exists (
    select 1 from public.runs r
    where r.id = run_id and r.author_user_id = auth.uid()
  ));
