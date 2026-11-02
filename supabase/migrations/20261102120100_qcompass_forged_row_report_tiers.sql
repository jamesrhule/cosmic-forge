-- Gate 1 round 3B (lane DB3): two more kinds in qcompass_forged_row_report.
-- Additive and idempotent (R13); the inverse is
-- down/20261102120100_qcompass_forged_row_report_tiers.down.sql, which
-- restores 20261102100200's version of the function.
--
-- The report (service-only, it lists and never deletes) gains:
--   * tenant_tier_not_free: every tenant whose subscription_tier is not
--     'free'. Main's "owners update tenants" policy let any owner or admin
--     raise their own tier until tenants_write_guard (20261102100000), and
--     no billing integration sets tiers yet (src/lib/billing.ts:
--     startCheckout is a stub), so no paid tier can be told apart from a
--     self-raised one; James reviews each (round-2 DB verifier,
--     R2-FORGED-REPORT residual).
--   * client_run_without_author: tenant runs a client wrote (origin
--     'client', 20261102120000) whose author's account was deleted. The API
--     never serves or counts them, but the tenant's owner cannot delete them
--     through the client either (the delete policy needs the author).
-- The three kinds of 20261102100200 are unchanged. EXECUTE stays with
-- service_role only.

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
  union all
  select 'tenant_tier_not_free', t.id::text, t.id,
         format('tenant %s (slug %s) is on tier %s; no billing integration sets tiers yet, '
                'and owners could raise their own tier before 20261102100000',
                t.id, t.slug, t.subscription_tier)
    from public.tenants t
   where t.subscription_tier::text <> 'free'
  union all
  select 'client_run_without_author', r.id, r.tenant_id,
         format('run %s of tenant %s was written by a client whose account was deleted; '
                'the API neither serves nor counts it, and no client can delete it',
                r.id, r.tenant_id)
    from public.runs r
   where r.origin = 'client' and r.author_user_id is null and r.tenant_id is not null
$$;

revoke all on function public.qcompass_forged_row_report() from public;
revoke all on function public.qcompass_forged_row_report() from anon, authenticated;
grant execute on function public.qcompass_forged_row_report() to service_role;

do $$
declare
  n bigint;
begin
  select count(*) into n from public.qcompass_forged_row_report()
   where kind in ('tenant_tier_not_free', 'client_run_without_author');
  if n > 0 then
    raise notice 'qcompass_forged_row_report: % paid-tier tenant(s) or author-less client run(s) to review', n;
  end if;
end $$;
