-- Inverse of 20261102120100_qcompass_forged_row_report_tiers.sql: the
-- function as 20261102100200 defined it (three kinds). A function holds no
-- data (R13).
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
