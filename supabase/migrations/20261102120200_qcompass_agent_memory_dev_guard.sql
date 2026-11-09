-- Gate 1 round 3B (lane DB3): no agent row is ever filed under a user-owned
-- 'dev' tenant. Additive and idempotent (R13); the inverse is
-- down/20261102120200_qcompass_agent_memory_dev_guard.down.sql, which drops
-- only what this file adds (no data is touched in either direction).
--
-- 20261102100100 undid 20261031200400's backfill into a user-owned 'dev'
-- tenant once. 20261031200400's unconditional
--   update ... set tenant_id = <the tenant with slug 'dev'> where tenant_id is null
-- is still live, so any single-version down/up of 20261031200400
-- (ucgle_f1.db.migrate allows one; test_sf4_agent_tenancy_migration_is_reversible
-- does exactly that) hands every tenant-less agent row, including the rows
-- 20261102100100 set back to null, to a user-owned 'dev' again, and
-- 20261102100100 never runs again (round-2 DB verifier, LOW).
--
-- A BEFORE INSERT OR UPDATE trigger on the six agent_* tables now keeps a
-- row off a user-owned 'dev' tenant, whoever writes (the migrations run as
-- the owner): when tenant_id would become such a tenant, the row keeps its
-- previous tenant (null for an INSERT), so a re-run backfill leaves those
-- rows tenant-less, which is what 20261102100100 decided. A 'dev' tenant
-- is user-owned when it has a creator or any member; the service's own 'dev'
-- (AuthStore.ensure_tenant: no creator, no members) is unaffected. This is
-- the rule of auth._USER_OWNED_DEV and 20261102100100.
--
-- The trigger reads tenant_id through to_jsonb(new), so it also works while
-- a rollback of 20261031200400 has the column renamed.

create or replace function public.qcompass_user_owned_dev(_tenant uuid)
returns boolean
language sql
stable
set search_path = public
as $$
  select exists (
    select 1 from public.tenants d
     where d.id = _tenant and d.slug = 'dev'
       and (d.created_by is not null
            or exists (select 1 from public.tenant_members m where m.tenant_id = d.id))
  )
$$;

create or replace function public.qcompass_agent_memory_dev_guard()
returns trigger
language plpgsql
set search_path = public
as $$
declare
  wanted uuid := (to_jsonb(new) ->> 'tenant_id')::uuid;
  previous uuid;
begin
  if wanted is null then
    return new;
  end if;
  if tg_op = 'UPDATE' then
    previous := (to_jsonb(old) ->> 'tenant_id')::uuid;
    if wanted is not distinct from previous then
      return new;
    end if;
  end if;
  if public.qcompass_user_owned_dev(wanted) then
    new := jsonb_populate_record(new, jsonb_build_object('tenant_id', previous));
  end if;
  return new;
end;
$$;

do $$
declare
  t text;
begin
  foreach t in array array['agent_hypotheses', 'agent_plans', 'agent_approval_tokens',
                           'agent_run_links', 'agent_tool_calls', 'agent_patches'] loop
    execute format('drop trigger if exists %I on public.%I', t || '_dev_guard', t);
    execute format(
      'create trigger %I before insert or update on public.%I '
      'for each row execute function public.qcompass_agent_memory_dev_guard()', t || '_dev_guard', t);
  end loop;
end $$;
